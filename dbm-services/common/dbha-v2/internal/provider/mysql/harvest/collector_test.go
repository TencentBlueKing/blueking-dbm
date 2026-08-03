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

package harvest

import (
	"database/sql"
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gorm.io/gorm"
)

func TestCollectorClose_Idempotent(t *testing.T) {
	closeCount := 0
	gdb := &gorm.DB{Config: &gorm.Config{}}
	db := hamysql.WithGormDB(gdb, func() { closeCount++ })

	c := &collector{db: db}
	c.close()
	c.close()

	if c.db != nil {
		t.Fatal("expected c.db to be nil after close")
	}
	if closeCount != 1 {
		t.Fatalf("expected Close to run once, got: %d", closeCount)
	}
}

func TestAdoptOpenedDB_ClosesOnDBMethodFailure(t *testing.T) {
	closeCount := 0
	// Nil ConnPool makes gorm.DB.DB() return ErrInvalidDB.
	gdb := &gorm.DB{Config: &gorm.Config{}}
	db := hamysql.WithGormDB(gdb, func() { closeCount++ })

	c := &collector{endpoint: &hanet.Endpoint{Host: "127.0.0.1", Port: 3306}}
	event, err := c.adoptOpenedDB(db)
	if err == nil {
		t.Fatal("expected adoptOpenedDB to fail")
	}
	if !errors.Is(err, gorm.ErrInvalidDB) {
		t.Fatalf("expected ErrInvalidDB, got: %s", err)
	}
	if event == nil {
		t.Fatal("expected non-nil DbEvent on failure")
	}
	if event.Name != haprobe.DbEventNameDetectFailure {
		t.Fatalf("unexpected event name: %s", event.Name)
	}
	if c.db != nil {
		t.Fatal("expected c.db to remain unset on failure")
	}
	if closeCount != 1 {
		t.Fatalf("expected db.Close once on failure, got: %d", closeCount)
	}
}

func TestAdoptOpenedDB_Success(t *testing.T) {
	sqlDB, err := sql.Open("mysql", "probe:test@tcp(127.0.0.1:1)/test")
	if err != nil {
		t.Fatalf("failed to open sql.DB, errmsg: %s", err)
	}
	t.Cleanup(func() { _ = sqlDB.Close() })

	// Wire *sql.DB directly as ConnPool; no dial occurs until the pool is used.
	gdb := &gorm.DB{Config: &gorm.Config{ConnPool: sqlDB}}

	closeCount := 0
	db := hamysql.WithGormDB(gdb, func() { closeCount++ })

	c := &collector{endpoint: &hanet.Endpoint{Host: "127.0.0.1", Port: 3306}}
	event, err := c.adoptOpenedDB(db)
	if err != nil {
		t.Fatalf("adoptOpenedDB failed, errmsg: %s", err)
	}
	if event != nil {
		t.Fatal("expected nil DbEvent on success")
	}
	if c.db == nil {
		t.Fatal("expected c.db to be set on success")
	}

	c.close()
	if c.db != nil {
		t.Fatal("expected c.db nil after close")
	}
	if closeCount != 1 {
		t.Fatalf("expected Close once, got: %d", closeCount)
	}
}
