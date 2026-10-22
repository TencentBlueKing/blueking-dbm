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
)

type mysqlStore struct {
	endpoint string
	user     string
	password string
	proto    string
	host     string
	port     int
	db       *sql.DB
	conn     *sql.Conn
	ident    Identity
	locked   bool
}

func newMySQLStore(proto, host string, port int, user, password string) *mysqlStore {
	if proto == "" {
		proto = "tcp"
	}
	return &mysqlStore{
		endpoint: net.JoinHostPort(host, strconv.Itoa(port)),
		user:     user,
		password: password,
		proto:    proto,
		host:     host,
		port:     port,
	}
}

func (s *mysqlStore) Endpoint() string { return s.endpoint }

func (s *mysqlStore) connect() error {
	if s.conn != nil {
		return nil
	}
	cfg := mysql.Config{
		User:                 s.user,
		Passwd:               s.password,
		Net:                  s.proto,
		Addr:                 s.endpoint,
		ParseTime:            true,
		Loc:                  time.Local,
		AllowNativePasswords: true,
		Params: map[string]string{
			"charset": "utf8mb4", "timeout": "10s", "readTimeout": "30s", "writeTimeout": "30s",
		},
	}
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

func (s *mysqlStore) readIdentity() (Identity, error) {
	var uuid, host string
	var port int
	err := s.conn.QueryRowContext(
		context.Background(), "SELECT @@server_uuid, @@hostname, @@port",
	).Scan(&uuid, &host, &port)
	if err != nil {
		var serverID int
		err = s.conn.QueryRowContext(
			context.Background(), "SELECT @@server_id, @@hostname, @@port",
		).Scan(&serverID, &host, &port)
		if err != nil {
			return Identity{}, err
		}
		uuid = strconv.Itoa(serverID)
	}
	return Identity{ServerUUID: uuid, Hostname: host, Port: port, Endpoint: s.endpoint}, nil
}

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
