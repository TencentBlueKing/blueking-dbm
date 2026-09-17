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

package main

import (
	"encoding/binary"
	"io"
	"log"
	"net"
	"strings"
	"sync/atomic"
)

const (
	comQuit        = 0x01
	comInitDB      = 0x02
	comQuery       = 0x03
	comPing        = 0x0e
	comStmtPrepare = 0x16
	comStmtExecute = 0x17
	comStmtClose   = 0x19
	comStmtReset   = 0x1a
	comReset       = 0x1f
	okHeader       = 0x00
	eofHeader      = 0xfe
	errHeader      = 0xff
	typeVarStr     = 0xfd

	clientLongPassword     uint32 = 1 << 0
	clientFoundRows        uint32 = 1 << 1
	clientLongFlag         uint32 = 1 << 2
	clientConnectWithDB    uint32 = 1 << 3
	clientProtocol41       uint32 = 1 << 9
	clientTransactions     uint32 = 1 << 13
	clientSecureConnection uint32 = 1 << 15
	clientPluginAuth       uint32 = 1 << 19
	clientPluginAuthLenEnc uint32 = 1 << 21

	statusAutocommit uint16 = 0x0002
)

var mysqlConnID atomic.Uint32

func mysqlCaps() uint32 {
	return clientLongPassword | clientFoundRows | clientLongFlag | clientConnectWithDB |
		clientProtocol41 | clientTransactions | clientSecureConnection | clientPluginAuth |
		clientPluginAuthLenEnc
}

func startMySQLMock(addr string) (net.Listener, error) {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	go acceptMySQL(ln)
	return ln, nil
}

func acceptMySQL(ln net.Listener) {
	for {
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		go handleMySQLConn(conn)
	}
}

func handleMySQLConn(conn net.Conn) {
	defer conn.Close()
	seq := byte(0)
	if err := writeMySQLPacket(conn, seq, mysqlHandshake(mysqlConnID.Add(1))); err != nil {
		return
	}
	seq++
	if _, _, err := readMySQLPacket(conn); err != nil {
		return
	}
	seq++
	if err := writeMySQLPacket(conn, seq, mysqlOK()); err != nil {
		return
	}
	for {
		_, payload, err := readMySQLPacket(conn)
		if err != nil {
			return
		}
		if len(payload) == 0 {
			return
		}
		if !serveMySQLCommand(conn, payload) {
			return
		}
	}
}

func serveMySQLCommand(conn net.Conn, payload []byte) bool {
	switch payload[0] {
	case comQuit:
		return false
	case comPing, comInitDB, comReset, comStmtReset:
		return writeMySQLPacket(conn, 1, mysqlOK()) == nil
	case comStmtClose:
		return true
	case comStmtPrepare, comStmtExecute:
		return writeMySQLPacket(conn, 1, mysqlErr("prepared statements unsupported")) == nil
	case comQuery:
		return replyMySQLQuery(conn, string(payload[1:])) == nil
	default:
		return writeMySQLPacket(conn, 1, mysqlErr("unsupported command")) == nil
	}
}

func replyMySQLQuery(conn net.Conn, query string) error {
	upper := strings.ToUpper(strings.TrimSpace(query))
	if strings.HasPrefix(upper, "SELECT") || strings.HasPrefix(upper, "SHOW") {
		if strings.Contains(upper, "VERSION") {
			return writeMySQLResultset(conn, "value", "8.0.36")
		}
		return writeMySQLEmptyResultset(conn, "value")
	}
	return writeMySQLPacket(conn, 1, mysqlOK())
}

func mysqlErr(msg string) []byte {
	buf := []byte{errHeader}
	buf = binary.LittleEndian.AppendUint16(buf, 1105)
	buf = append(buf, '#')
	buf = append(buf, []byte("HY000")...)
	buf = append(buf, []byte(msg)...)
	return buf
}

func mysqlEOF() []byte {
	buf := []byte{eofHeader}
	buf = binary.LittleEndian.AppendUint16(buf, 0)
	buf = binary.LittleEndian.AppendUint16(buf, statusAutocommit)
	return buf
}

func writeMySQLResultset(conn net.Conn, col, value string) error {
	seq := byte(1)
	if err := writeMySQLPacket(conn, seq, lenEncInt(1)); err != nil {
		return err
	}
	seq++
	if err := writeMySQLPacket(conn, seq, mysqlColumnDef(col)); err != nil {
		return err
	}
	seq++
	if err := writeMySQLPacket(conn, seq, mysqlEOF()); err != nil {
		return err
	}
	seq++
	if err := writeMySQLPacket(conn, seq, lenEncStr(value)); err != nil {
		return err
	}
	seq++
	return writeMySQLPacket(conn, seq, mysqlEOF())
}

func writeMySQLEmptyResultset(conn net.Conn, col string) error {
	seq := byte(1)
	if err := writeMySQLPacket(conn, seq, lenEncInt(1)); err != nil {
		return err
	}
	seq++
	if err := writeMySQLPacket(conn, seq, mysqlColumnDef(col)); err != nil {
		return err
	}
	seq++
	if err := writeMySQLPacket(conn, seq, mysqlEOF()); err != nil {
		return err
	}
	seq++
	return writeMySQLPacket(conn, seq, mysqlEOF())
}

func mysqlColumnDef(name string) []byte {
	buf := lenEncStr("def")
	buf = append(buf, lenEncStr("")...)
	buf = append(buf, lenEncStr("")...)
	buf = append(buf, lenEncStr("")...)
	buf = append(buf, lenEncStr(name)...)
	buf = append(buf, lenEncStr(name)...)
	buf = append(buf, 0x0c)
	buf = binary.LittleEndian.AppendUint16(buf, 45)
	buf = binary.LittleEndian.AppendUint32(buf, 64)
	buf = append(buf, typeVarStr)
	buf = binary.LittleEndian.AppendUint16(buf, 0)
	buf = append(buf, 0x00, 0x00, 0x00)
	return buf
}

func mysqlHandshake(connID uint32) []byte {
	scramble := make([]byte, 20)
	for i := range scramble {
		scramble[i] = byte(i + 1)
	}
	caps := mysqlCaps()
	plugin := "mysql_native_password"
	buf := make([]byte, 0, 128)
	buf = append(buf, 10)
	buf = append(buf, []byte("8.0.36-ha-sandbox-mock")...)
	buf = append(buf, 0)
	buf = binary.LittleEndian.AppendUint32(buf, connID)
	buf = append(buf, scramble[:8]...)
	buf = append(buf, 0)
	buf = binary.LittleEndian.AppendUint16(buf, uint16(caps))
	buf = append(buf, 45)
	buf = binary.LittleEndian.AppendUint16(buf, statusAutocommit)
	buf = binary.LittleEndian.AppendUint16(buf, uint16(caps>>16))
	buf = append(buf, 21)
	buf = append(buf, make([]byte, 10)...)
	buf = append(buf, scramble[8:]...)
	buf = append(buf, 0)
	buf = append(buf, []byte(plugin)...)
	buf = append(buf, 0)
	return buf
}

func mysqlOK() []byte {
	buf := []byte{okHeader, 0x00, 0x00}
	buf = binary.LittleEndian.AppendUint16(buf, statusAutocommit)
	buf = binary.LittleEndian.AppendUint16(buf, 0)
	return buf
}

func writeMySQLPacket(w io.Writer, seq byte, payload []byte) error {
	n := len(payload)
	hdr := []byte{byte(n), byte(n >> 8), byte(n >> 16), seq}
	if _, err := w.Write(hdr); err != nil {
		return err
	}
	_, err := w.Write(payload)
	return err
}

func readMySQLPacket(r io.Reader) (byte, []byte, error) {
	hdr := make([]byte, 4)
	if _, err := io.ReadFull(r, hdr); err != nil {
		return 0, nil, err
	}
	n := int(uint32(hdr[0]) | uint32(hdr[1])<<8 | uint32(hdr[2])<<16)
	payload := make([]byte, n)
	if _, err := io.ReadFull(r, payload); err != nil {
		return 0, nil, err
	}
	return hdr[3], payload, nil
}

func lenEncInt(n uint64) []byte {
	if n < 251 {
		return []byte{byte(n)}
	}
	if n < 1<<16 {
		return []byte{0xfc, byte(n), byte(n >> 8)}
	}
	return []byte{0xfd, byte(n), byte(n >> 8), byte(n >> 16)}
}

func lenEncStr(s string) []byte {
	return append(lenEncInt(uint64(len(s))), []byte(s)...)
}

func logMySQLReady(addr string) {
	log.Printf("mysql mock ready, addr: %s", addr)
}
