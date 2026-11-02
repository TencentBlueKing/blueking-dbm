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

package migrator

import (
	"context"
	"database/sql"
	"fmt"
	"net"
	"strconv"
	"time"

	"github.com/go-sql-driver/mysql"
	gormmysql "gorm.io/driver/mysql"
	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"
)

// mysqlStore is the MySQL implementation of Store for one endpoint.
type mysqlStore struct {
	endpoint string
	user     string
	password string
	proto    string
	db       *sql.DB
	conn     *sql.Conn
	ident    Identity
	locked   bool
}

// newMySQLStore builds a store for one endpoint, defaulting the protocol to tcp.
func newMySQLStore(proto, host string, port int, user, password string) *mysqlStore {
	if proto == "" {
		proto = "tcp"
	}

	return &mysqlStore{
		endpoint: net.JoinHostPort(host, strconv.Itoa(port)),
		user:     user,
		password: password,
		proto:    proto,
	}
}

// Endpoint returns the "host:port" this store connects to.
func (s *mysqlStore) Endpoint() string { return s.endpoint }

// connect opens a single pinned connection, reused for locks, DDL, and data work.
func (s *mysqlStore) connect() error {
	if s.conn != nil {
		return nil
	}

	cfg := migrateMySQLConfig(s.user, s.password, s.proto, s.endpoint)
	db, err := sql.Open("mysql", cfg.FormatDSN())
	if err != nil {
		return err
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	conn, err := db.Conn(context.Background())
	if err != nil {
		_ = db.Close()
		return err
	}
	s.db = db
	s.conn = conn

	return nil
}

// orm wraps the pinned connection in a GORM session, so data work stays on the locked session.
// It is rebuilt on every call because Unlock closes the connection it would hold.
func (s *mysqlStore) orm() (*gorm.DB, error) {
	if err := s.connect(); err != nil {
		return nil, err
	}

	return gorm.Open(
		gormmysql.New(gormmysql.Config{Conn: s.conn, SkipInitializeWithVersion: true}),
		&gorm.Config{Logger: gormlogger.Discard, SkipDefaultTransaction: true},
	)
}

// Identity returns the server identity, reading it from the server once.
func (s *mysqlStore) Identity() (Identity, error) {
	if err := s.connect(); err != nil {
		return Identity{}, err
	}
	if s.ident.ServerUUID != "" {
		return s.ident, nil
	}

	id, err := s.readIdentity()
	if err != nil {
		return Identity{}, err
	}
	s.ident = id

	return id, nil
}

// readIdentity reads server_uuid, falling back to server_id on older servers.
func (s *mysqlStore) readIdentity() (Identity, error) {
	var uuid, host string
	var port int
	err := s.conn.QueryRowContext(
		context.Background(), "SELECT @@server_uuid, @@hostname, @@port",
	).Scan(&uuid, &host, &port)
	if err == nil {
		return Identity{ServerUUID: uuid, Hostname: host, Port: port, Endpoint: s.endpoint}, nil
	}
	if !unknownVariable(err) {
		return Identity{}, err
	}

	// No server_uuid: identify by server_id and mark the identity as a fallback.
	var serverID int
	err = s.conn.QueryRowContext(
		context.Background(), "SELECT @@server_id, @@hostname, @@port",
	).Scan(&serverID, &host, &port)
	if err != nil {
		return Identity{}, err
	}

	return Identity{
		ServerUUID: "server-id:" + strconv.Itoa(serverID),
		Hostname:   host,
		Port:       port,
		Endpoint:   s.endpoint,
		Fallback:   true,
	}, nil
}

// Lock takes the MySQL advisory lock on the pinned connection.
func (s *mysqlStore) Lock() error {
	if err := s.connect(); err != nil {
		return err
	}
	if s.locked {
		return nil
	}

	var got sql.NullInt64
	err := s.conn.QueryRowContext(
		context.Background(), "SELECT GET_LOCK(?, ?)", lockName(), lockWaitSecond,
	).Scan(&got)
	if err != nil {
		return err
	}
	if !got.Valid || got.Int64 != 1 {
		return fmt.Errorf("lock wait timed out")
	}
	s.locked = true

	return nil
}

// Unlock releases the advisory lock and closes the connection, keeping the first error.
func (s *mysqlStore) Unlock() error {
	conn, db, locked := s.conn, s.db, s.locked
	s.conn, s.db, s.locked = nil, nil, false

	var firstErr error
	if conn != nil {
		if locked {
			if _, err := conn.ExecContext(context.Background(), "SELECT RELEASE_LOCK(?)", lockName()); err != nil {
				firstErr = err
			}
		}
		if err := conn.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	if db != nil {
		if err := db.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}

	return firstErr
}

// migrateMySQLConfig builds the driver config used for migration connections.
// Loc is UTC: times read here are session-zone literals labelled UTC, not real instants. They
// round-trip unchanged, but must not be compared with or converted against time.Now().
func migrateMySQLConfig(user, password, proto, addr string) *mysql.Config {
	if proto == "" {
		proto = "tcp"
	}

	return &mysql.Config{
		User:                 user,
		Passwd:               password,
		Net:                  proto,
		Addr:                 addr,
		ParseTime:            true,
		Loc:                  time.UTC,
		AllowNativePasswords: true,
		Params: map[string]string{
			"charset": "utf8mb4",
			"timeout": "10s",
		},
	}
}
