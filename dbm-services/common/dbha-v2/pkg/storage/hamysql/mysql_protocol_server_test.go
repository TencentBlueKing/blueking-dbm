/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hamysql_test

import (
	"context"
	"encoding/binary"
	"io"
	"net"
	"strconv"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

// This file simulates a server that speaks the MySQL client/server protocol.
// It is not a database. It only produces the packets NewGormDB and NewSqlxDB
// exchange while establishing a connection, and it can stop responding at a
// chosen step so the connect timeout can be tested without a real MySQL instance.

// protocolStall is the point at which the simulated server stops responding.
type protocolStall int

const (
	// stallBeforeHandshake accepts TCP and never sends the server greeting.
	stallBeforeHandshake protocolStall = iota
	// stallAfterHandshake sends the greeting and then never answers authentication.
	stallAfterHandshake
	// stallOnQuery completes authentication and then never answers the next query.
	// With the default charset that query is SET NAMES. With charset cleared it is SELECT VERSION().
	stallOnQuery
	// stallNone answers the queries issued while the connection is established.
	stallNone
)

// protocolServer is a simulated MySQL-protocol server bound to 127.0.0.1.
type protocolServer struct {
	ln    net.Listener
	stall protocolStall
	done  chan struct{}
}

// startProtocolServer listens on an ephemeral port and serves one connection.
func startProtocolServer(t *testing.T, stall protocolStall) *protocolServer {
	t.Helper()

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %s", err)
	}
	srv := &protocolServer{ln: ln, stall: stall, done: make(chan struct{})}
	go func() {
		defer close(srv.done)
		conn, acceptErr := ln.Accept()
		if acceptErr != nil {
			return
		}
		defer conn.Close()
		serveMySQLProtocol(conn, stall)
	}()
	t.Cleanup(func() {
		ln.Close()
		<-srv.done
	})
	return srv
}

func (s *protocolServer) hostPort(t *testing.T) (string, int) {
	t.Helper()
	host, portText, err := net.SplitHostPort(s.ln.Addr().String())
	if err != nil {
		t.Fatalf("split addr: %s", err)
	}
	port, err := strconv.Atoi(portText)
	if err != nil {
		t.Fatalf("parse port: %s", err)
	}
	return host, port
}

// serveMySQLProtocol speaks the handshake and the few queries NewGormDB sends.
func serveMySQLProtocol(conn net.Conn, stall protocolStall) {
	if stall == stallBeforeHandshake {
		holdUntilClientClose(conn)
		return
	}
	if err := writePacket(conn, 0, mysqlGreeting()); err != nil {
		return
	}
	if stall == stallAfterHandshake {
		holdUntilClientClose(conn)
		return
	}

	seq, _, err := readPacket(conn)
	if err != nil {
		return
	}
	if err = writePacket(conn, seq+1, mysqlOK()); err != nil {
		return
	}
	if stall == stallOnQuery {
		holdUntilClientClose(conn)
		return
	}

	for {
		var payload []byte
		seq, payload, err = readPacket(conn)
		if err != nil || len(payload) == 0 {
			return
		}
		// COM_QUERY is 0x03 followed by the SQL text. Anything else is accepted.
		if payload[0] != 0x03 {
			if err = writePacket(conn, seq+1, mysqlOK()); err != nil {
				return
			}
			continue
		}
		sqlText := string(payload[1:])
		switch {
		case strings.Contains(sqlText, "max_allowed_packet"):
			err = writeResultSet(conn, seq, "max_allowed_packet", "4194304")
		case strings.Contains(strings.ToLower(sqlText), "version"):
			err = writeResultSet(conn, seq, "VERSION()", "5.7.0-fake")
		default:
			err = writePacket(conn, seq+1, mysqlOK())
		}
		if err != nil {
			return
		}
	}
}

// holdUntilClientClose blocks until the client closes the socket or a deadline passes.
// It keeps reading so a client packet already in the buffer does not end the stall.
func holdUntilClientClose(conn net.Conn) {
	// Longer than the client timeout passed by the stall tests, so the server
	// stays silent until the client cancels instead of closing the socket first.
	_ = conn.SetReadDeadline(time.Now().Add(20 * time.Second))
	buf := make([]byte, 1)
	for {
		if _, err := conn.Read(buf); err != nil {
			return
		}
	}
}

func mysqlGreeting() []byte {
	// Capability flags the go-sql-driver handshake parser requires:
	// protocol 4.1, secure connection, and plugin auth.
	var caps uint32 = (1 << 0) | (1 << 9) | (1 << 13) | (1 << 15) | (1 << 19) | (1 << 21)
	raw := make([]byte, 0, 128)
	raw = append(raw, 10) // protocol version
	raw = append(raw, []byte("5.7.0-fake")...)
	raw = append(raw, 0)
	raw = append(raw, 1, 0, 0, 0)            // connection id
	raw = append(raw, []byte("12345678")...) // auth plugin data part 1
	raw = append(raw, 0)                     // filler
	raw = append(raw, byte(caps), byte(caps>>8))
	raw = append(raw, 45)   // utf8mb4_general_ci
	raw = append(raw, 2, 0) // autocommit
	raw = append(raw, byte(caps>>16), byte(caps>>24))
	raw = append(raw, 21) // auth plugin data length, including the terminating NUL
	raw = append(raw, make([]byte, 10)...)
	raw = append(raw, []byte("abcdefghijkl")...)
	raw = append(raw, 0)
	raw = append(raw, []byte("mysql_native_password")...)
	raw = append(raw, 0)
	return raw
}

func mysqlOK() []byte {
	return []byte{
		0x00,       // OK
		0x00,       // affected rows
		0x00,       // last insert id
		0x02, 0x00, // status flags
		0x00, 0x00, // warnings
	}
}

func writeResultSet(conn net.Conn, clientSeq byte, column, value string) error {
	seq := clientSeq + 1
	if err := writePacket(conn, seq, []byte{0x01}); err != nil {
		return err
	}
	seq++
	if err := writePacket(conn, seq, columnDefinition(column)); err != nil {
		return err
	}
	seq++
	if err := writePacket(conn, seq, eofPacket()); err != nil {
		return err
	}
	seq++
	if err := writePacket(conn, seq, appendLenEnc(nil, value)); err != nil {
		return err
	}
	seq++
	return writePacket(conn, seq, eofPacket())
}

func columnDefinition(name string) []byte {
	raw := make([]byte, 0, 64)
	raw = appendLenEnc(raw, "def")
	raw = appendLenEnc(raw, "")
	raw = appendLenEnc(raw, "")
	raw = appendLenEnc(raw, "")
	raw = appendLenEnc(raw, name)
	raw = appendLenEnc(raw, name)
	raw = append(raw, 0x0c)
	fixed := make([]byte, 0x0c)
	binary.LittleEndian.PutUint16(fixed[0:2], 45)  // utf8mb4
	binary.LittleEndian.PutUint32(fixed[2:6], 256) // column length
	fixed[6] = 0xfd                                // VAR_STRING
	raw = append(raw, fixed...)
	return raw
}

func eofPacket() []byte {
	return []byte{0xfe, 0x00, 0x00, 0x02, 0x00}
}

func appendLenEnc(dst []byte, value string) []byte {
	dst = append(dst, byte(len(value)))
	return append(dst, value...)
}

func writePacket(conn net.Conn, seq byte, payload []byte) error {
	hdr := []byte{byte(len(payload)), byte(len(payload) >> 8), byte(len(payload) >> 16), seq}
	if _, err := conn.Write(hdr); err != nil {
		return err
	}
	_, err := conn.Write(payload)
	return err
}

func readPacket(conn net.Conn) (byte, []byte, error) {
	var hdr [4]byte
	if _, err := io.ReadFull(conn, hdr[:]); err != nil {
		return 0, nil, err
	}
	n := int(hdr[0]) | int(hdr[1])<<8 | int(hdr[2])<<16
	seq := hdr[3]
	payload := make([]byte, n)
	if _, err := io.ReadFull(conn, payload); err != nil {
		return 0, nil, err
	}
	return seq, payload, nil
}

type connectKind int

const (
	kindGorm connectKind = iota
	kindSqlx
)

type connectResult int

const (
	// resultTimeout means NewGormDB or NewSqlxDB returns an error within the timeout.
	resultTimeout connectResult = iota
	// resultMiss means OptionTimeout elapses while the call is still blocked.
	resultMiss
	// resultConnect means the call succeeds and the server version is readable.
	resultConnect
)

// connectCase is one protocol-server scenario.
type connectCase struct {
	// kind selects NewGormDB or NewSqlxDB. Only GORM receives SkipInitializeWithVersion.
	kind connectKind
	// stall is where the simulated server stops answering:
	// before the greeting, after the greeting, on the first SQL, or not at all.
	stall protocolStall
	// skipVersion is used only for GORM. True passes SkipInitializeWithVersion(true),
	// so the first Connect is Conn and OptionTimeout covers it. False lets GORM run
	// SELECT VERSION() inside gorm.Open, which OptionTimeout does not cover.
	skipVersion bool
	// clearCharset passes an empty charset, so the DSN has no charset and the driver
	// does not send SET NAMES. The first SQL after authentication is then SELECT VERSION().
	clearCharset bool
	// result is the expected outcome: timeout error, still blocked after the timeout, or a successful connect.
	result connectResult
}

func runConnectCase(t *testing.T, c connectCase) {
	t.Helper()
	srv := startProtocolServer(t, c.stall)
	host, port := srv.hostPort(t)

	// Matches defaultOptions.logSlowConnect. Failures are logged; successes under this stay quiet.
	const timeout = 3 * time.Second
	opts := []hamysql.Option{
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser("u"),
		hamysql.OptionPassword("p"),
		hamysql.OptionTimeout(timeout),
	}
	if c.kind == kindGorm {
		opts = append(opts, hamysql.OptionSkipInitializeWithVersion(c.skipVersion))
	}
	if c.clearCharset {
		opts = append(opts, hamysql.OptionCharset(""))
	}

	if c.result == resultMiss {
		assertStillBlocked(t, c.kind, opts, timeout, srv.ln.Close)
		return
	}

	start := time.Now()
	db, err := openProtocolDB(c.kind, opts...)
	elapsed := time.Since(start)
	if c.result == resultTimeout {
		if db != nil {
			db.Close()
			t.Fatal("expected no database after timeout")
		}
		if err == nil {
			t.Fatal("expected timeout error")
		}
		if elapsed > 2*timeout {
			t.Fatalf("did not time out, elapsed=%s, err=%v", elapsed, err)
		}
		return
	}

	if err != nil {
		t.Fatalf("connect: %s", err)
	}
	defer db.Close()
	if version := protocolVersion(t, db); version != "5.7.0-fake" {
		t.Fatalf("version: got %q", version)
	}
}

func assertStillBlocked(t *testing.T, kind connectKind, opts []hamysql.Option, timeout time.Duration, release func() error) {
	t.Helper()
	done := make(chan struct{})
	go func() {
		defer close(done)
		db, _ := openProtocolDB(kind, opts...)
		if db != nil {
			db.Close()
		}
	}()
	select {
	case <-done:
		t.Fatal("connect returned within OptionTimeout")
	case <-time.After(timeout + 500*time.Millisecond):
	}
	// The timings log is written when the call returns. Close the listener so a
	// retry cannot sit on an unaccepted port, then wait for that return.
	_ = release()
	select {
	case <-done:
	case <-time.After(25 * time.Second):
		t.Fatal("connect did not return after the simulated server stopped holding the connection")
	}
}

type protocolDB interface {
	Close()
}

func openProtocolDB(kind connectKind, opts ...hamysql.Option) (protocolDB, error) {
	if kind == kindSqlx {
		db, err := hamysql.NewSqlxDB(opts...)
		if err != nil {
			return nil, err
		}
		return db, nil
	}
	db, err := hamysql.NewGormDB(opts...)
	if err != nil {
		return nil, err
	}
	return db, nil
}

func protocolVersion(t *testing.T, db protocolDB) string {
	t.Helper()
	switch opened := db.(type) {
	case *hamysql.GormDB:
		version, err := opened.Version(context.Background())
		if err != nil {
			t.Fatalf("version: %s", err)
		}
		return version
	case *hamysql.SqlxDB:
		var version string
		if err := opened.DB().QueryRow("select version()").Scan(&version); err != nil {
			t.Fatalf("version: %s", err)
		}
		return version
	default:
		t.Fatalf("unexpected database %T", db)
		return ""
	}
}

func assertNewGormDBWithTimeoutTimesOut(t *testing.T, stall protocolStall, extra ...hamysql.Option) {
	t.Helper()
	srv := startProtocolServer(t, stall)
	host, port := srv.hostPort(t)

	const timeout = 3 * time.Second
	opts := []hamysql.Option{
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser("u"),
		hamysql.OptionPassword("p"),
		hamysql.OptionTimeout(timeout),
	}
	opts = append(opts, extra...)

	start := time.Now()
	db, err := hamysql.NewGormDBWithTimeout(opts...)
	elapsed := time.Since(start)
	if db != nil {
		db.Close()
		t.Fatal("expected no database after timeout")
	}
	if err == nil {
		t.Fatal("expected timeout error")
	}
	if elapsed > 2*timeout {
		t.Fatalf("did not time out, elapsed=%s, err=%v", elapsed, err)
	}
}

// GORM runs SELECT VERSION() inside gorm.Open. OptionTimeout does not cover that connect.
func TestGormInitBeforeHandshakeMiss(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallBeforeHandshake, skipVersion: false, result: resultMiss})
}

func TestGormInitAfterHandshakeMiss(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallAfterHandshake, skipVersion: false, result: resultMiss})
}

func TestGormInitSetNamesMiss(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallOnQuery, skipVersion: false, result: resultMiss})
}

func TestGormInitVersionMiss(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallOnQuery, skipVersion: false, clearCharset: true, result: resultMiss})
}

func TestGormInitConnect(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallNone, skipVersion: false, result: resultConnect})
}

// Skipping version init makes the first Connect happen in Conn, so OptionTimeout applies.
func TestGormSkipVersionBeforeHandshakeTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallBeforeHandshake, skipVersion: true, result: resultTimeout})
}

func TestGormSkipVersionAfterHandshakeTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallAfterHandshake, skipVersion: true, result: resultTimeout})
}

func TestGormSkipVersionSetNamesTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallOnQuery, skipVersion: true, result: resultTimeout})
}

func TestGormSkipVersionConnect(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindGorm, stall: stallNone, skipVersion: true, result: resultConnect})
}

func TestSqlxBeforeHandshakeTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindSqlx, stall: stallBeforeHandshake, result: resultTimeout})
}

func TestSqlxAfterHandshakeTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindSqlx, stall: stallAfterHandshake, result: resultTimeout})
}

func TestSqlxSetNamesTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindSqlx, stall: stallOnQuery, result: resultTimeout})
}

func TestSqlxVersionTimeout(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindSqlx, stall: stallOnQuery, clearCharset: true, result: resultTimeout})
}

func TestSqlxConnect(t *testing.T) {
	runConnectCase(t, connectCase{kind: kindSqlx, stall: stallNone, result: resultConnect})
}

func TestNewGormDBWithTimeoutBeforeHandshake(t *testing.T) {
	assertNewGormDBWithTimeoutTimesOut(t, stallBeforeHandshake)
}

func TestNewGormDBWithTimeoutAfterHandshake(t *testing.T) {
	assertNewGormDBWithTimeoutTimesOut(t, stallAfterHandshake)
}

func TestNewGormDBWithTimeoutSetNames(t *testing.T) {
	assertNewGormDBWithTimeoutTimesOut(t, stallOnQuery, hamysql.OptionCharset("utf8mb4"))
}

func TestNewGormDBWithTimeoutVersion(t *testing.T) {
	assertNewGormDBWithTimeoutTimesOut(t, stallOnQuery, hamysql.OptionCharset(""))
}

func TestNewGormDBWithTimeoutMaxAllowedPacket(t *testing.T) {
	assertNewGormDBWithTimeoutTimesOut(t, stallOnQuery,
		hamysql.OptionCharset(""),
		hamysql.OptionAutoMaxAllowedPacket(true),
	)
}

func TestNewGormDBWithTimeoutConnect(t *testing.T) {
	srv := startProtocolServer(t, stallNone)
	host, port := srv.hostPort(t)

	db, err := hamysql.NewGormDBWithTimeout(
		hamysql.OptionProto("tcp"),
		hamysql.OptionIP(host),
		hamysql.OptionPort(port),
		hamysql.OptionUser("u"),
		hamysql.OptionPassword("p"),
		hamysql.OptionTimeout(3*time.Second),
		hamysql.OptionCharset("utf8mb4"),
		hamysql.OptionAutoMaxAllowedPacket(true),
	)
	if err != nil {
		t.Fatalf("connect: %s", err)
	}
	defer db.Close()

	version, err := db.Version(context.Background())
	if err != nil {
		t.Fatalf("version: %s", err)
	}
	if version != "5.7.0-fake" {
		t.Fatalf("version: got %q", version)
	}
}
