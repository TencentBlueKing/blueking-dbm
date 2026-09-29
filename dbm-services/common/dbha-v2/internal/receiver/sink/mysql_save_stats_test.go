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

package sink

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	mysqldriver "github.com/go-sql-driver/mysql"
	gormmysql "gorm.io/driver/mysql"
	"gorm.io/gorm"
)

type errConnPool struct {
	stubConnPool
	err error
}

func (p *errConnPool) BeginTx(context.Context, *sql.TxOptions) (gorm.ConnPool, error) {
	return p, nil
}

func (p *errConnPool) ExecContext(context.Context, string, ...interface{}) (sql.Result, error) {
	if p.err != nil {
		return nil, p.err
	}
	return stubResult{}, nil
}

func openPoolDB(t *testing.T, pool gorm.ConnPool) *hamysql.GormDB {
	t.Helper()
	gdb, err := gorm.Open(gormmysql.New(gormmysql.Config{
		Conn:                      pool,
		SkipInitializeWithVersion: true,
	}), &gorm.Config{})
	if err != nil {
		t.Fatalf("open gorm failed, errmsg: %s", err)
	}
	return hamysql.WithGormDB(gdb, nil)
}

func mysqlWithPool(t *testing.T, pools ...gorm.ConnPool) *mysql {
	t.Helper()
	s := &mysql{writer: &fakeChunkWriter{}, writeRetryTimeout: time.Second}
	for _, pool := range pools {
		s.dbs = append(s.dbs, openPoolDB(t, pool))
	}
	return s
}

func captureSave(t *testing.T, s *mysql, msg *Message) (error, WriteStats) {
	t.Helper()
	var got WriteStats
	s.recordStats = func(topic string, stats WriteStats) {
		if topic != msg.Topic {
			t.Fatalf("topic = %s", topic)
		}
		got = stats
	}
	err := s.Save(msg)
	return err, got
}

func TestSaveStatsSuccessAndInvalid(t *testing.T) {
	t.Parallel()
	s := mysqlWithPool(t, &stubConnPool{})
	s.nowFn = func() time.Time { return time.Unix(1000, 0) }
	err, stats := captureSave(t, s, sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 990))
	if err != nil || stats.Written != 1 || len(stats.Samples) != 1 || stats.Samples[0].Ms != 10000 {
		t.Fatalf("success: err=%v stats=%+v", err, stats)
	}

	err, stats = captureSave(t, s, &Message{Topic: "t", Data: []byte("{")})
	if err == nil || stats.DropCount("", ReasonInvalidJSON) != 1 || stats.Written != 0 {
		t.Fatalf("invalid json: err=%v stats=%+v", err, stats)
	}

	err, stats = captureSave(t, s, sampleAt(t, 3306, "nope", haprobe.DbTypeRedis, 1))
	if err == nil || stats.DropCount("redis", ReasonUnknownType) != 1 {
		t.Fatalf("unknown type: err=%v stats=%+v", err, stats)
	}
}

func TestSaveStatsEndpointErrors(t *testing.T) {
	t.Parallel()
	dataErr := &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
	s := mysqlWithPool(t, &errConnPool{err: dataErr}, &errConnPool{err: dataErr})
	_, stats := captureSave(t, s, sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1))
	if stats.Written != 0 || stats.DropCount("mysql", ReasonDataError) != 1 {
		t.Fatalf("expected data_error, got %+v", stats)
	}

	transient := mysqlWithPool(t, &errConnPool{err: errors.New("readonly")}, &errConnPool{err: errors.New("readonly")})
	err, stats := captureSave(t, transient, sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1))
	if err != nil || stats.DropCount("mysql", ReasonWriteError) != 1 {
		t.Fatalf("expected write_error and nil error, err=%v stats=%+v", err, stats)
	}
}
