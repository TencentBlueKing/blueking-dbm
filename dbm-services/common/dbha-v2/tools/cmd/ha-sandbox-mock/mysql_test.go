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
	"context"
	"database/sql"
	"fmt"
	"net"
	"testing"
	"time"

	_ "github.com/go-sql-driver/mysql"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"
)

func TestMySQLMockPing(t *testing.T) {
	ln, err := startMySQLMock("127.0.0.1:0")
	if err != nil {
		t.Fatalf("start mysql mock failed, errmsg: %s", err)
	}
	defer ln.Close()
	addr := ln.Addr().String()
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		t.Fatalf("split host port failed, errmsg: %s", err)
	}

	dsn := fmt.Sprintf("sandbox:sandbox@tcp(%s:%s)/dbha_data?timeout=3s&parseTime=true", host, port)
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatalf("open mysql failed, errmsg: %s", err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		t.Fatalf("ping mysql mock failed, errmsg: %s", err)
	}
	var version string
	if err := db.QueryRow("SELECT VERSION()").Scan(&version); err != nil {
		t.Fatalf("select version failed, errmsg: %s", err)
	}
	if version != "8.0.36" {
		t.Fatalf("version: %s, want: 8.0.36", version)
	}
}

func TestMySQLMockGormParameterizedQueryFailsFast(t *testing.T) {
	ln, err := startMySQLMock("127.0.0.1:0")
	if err != nil {
		t.Fatalf("start mysql mock failed, errmsg: %s", err)
	}
	defer ln.Close()

	dsn := fmt.Sprintf("sandbox:sandbox@tcp(%s)/dbha_data?timeout=2s&parseTime=true", ln.Addr().String())
	gdb, err := gorm.Open(mysql.Open(dsn), &gorm.Config{
		Logger:               gormlogger.Discard,
		DisableAutomaticPing: true,
	})
	if err != nil {
		t.Fatalf("open gorm failed, errmsg: %s", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	var rows []struct {
		IP string
	}
	err = gdb.WithContext(ctx).Raw("SELECT ip FROM t_dbm_metadata WHERE ip = ?", "127.0.0.1").Scan(&rows).Error
	if ctx.Err() != nil {
		t.Fatalf("query hung until context done, errmsg: %s", err)
	}
}
