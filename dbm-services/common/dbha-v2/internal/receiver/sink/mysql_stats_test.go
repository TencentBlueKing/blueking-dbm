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
	"encoding/json"
	"math"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	mysqldriver "github.com/go-sql-driver/mysql"
	"gorm.io/gorm"
)

func sampleAt(t *testing.T, port int, harvest string, dbType haprobe.DbType, ts uint64) *Message {
	t.Helper()
	hd := &haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			MachineID:       "m1",
			DbIp:            "127.0.0.1",
			DbPort:          port,
			HarvestType:     haprobe.HarvestType(harvest),
			DbTypeName:      dbType,
			ReportTimestamp: ts,
		},
	}
	b, err := json.Marshal(hd)
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}
	return &Message{Topic: "t", Data: b}
}

func assertConserved(t *testing.T, n int, stats WriteStats) {
	t.Helper()
	if stats.Written+stats.DropTotal() != n {
		t.Fatalf("written %d + drops %d != %d", stats.Written, stats.DropTotal(), n)
	}
}

func TestSaveBatchStatsMixedAndConserved(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if rowsContainPort(rows, 3307) {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		return nil
	}}
	s := newTestMysql(t, 1, w)
	s.batchChunkSize = 10
	fixed := time.Unix(1000, 0)
	s.nowFn = func() time.Time { return fixed }
	msgs := []*Message{
		{Topic: "t", Data: []byte("{")},
		sampleAt(t, 3306, "nope", haprobe.DbTypeMySql, 990),
		sampleAt(t, 3306, "default", haprobe.DbTypeRedis, 990),
		sampleAt(t, 3307, "default", haprobe.DbTypeMySql, 990),
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 990),
	}
	result, err := s.SaveBatch(context.Background(), msgs)
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	assertConserved(t, len(msgs), result.Stats)
	if result.Stats.DropCount("", ReasonInvalidJSON) != 1 {
		t.Fatalf("invalid json: %+v", result.Stats)
	}
	if result.Stats.DropCount("mysql", ReasonUnknownType) != 1 {
		t.Fatalf("unknown type: %+v", result.Stats)
	}
	if result.Stats.DropCount("redis", ReasonDedup) != 1 {
		t.Fatalf("dedup db_type: %+v", result.Stats)
	}
	if result.Stats.DropCount("mysql", ReasonDataError) != 1 || result.Stats.Written != 1 {
		t.Fatalf("write stats: written=%d %+v", result.Stats.Written, result.Stats)
	}
	if len(result.Stats.Samples) != 1 || result.Stats.Samples[0].Ms != 10000 {
		t.Fatalf("expected one 10000ms sample, got %+v", result.Stats.Samples)
	}
}

func rowsContainPort(rows []*hamodel.DbhaDataStatus, port int) bool {
	for _, row := range rows {
		if row.DbPort == port {
			return true
		}
	}
	return false
}

func TestSaveBatchFixedClockSample(t *testing.T) {
	t.Parallel()
	s := newTestMysql(t, 1, &fakeChunkWriter{})
	s.nowFn = func() time.Time { return time.Unix(1000, 0) }
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 990),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Stats.Written != 1 || len(result.Stats.Samples) != 1 || result.Stats.Samples[0].Ms != 10000 {
		t.Fatalf("unexpected sample: %+v", result.Stats)
	}
}

func TestSaveBatchRetrySucceedsOnce(t *testing.T) {
	t.Parallel()
	calls := 0
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		calls++
		if calls == 1 {
			return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
		}
		return nil
	}}
	s := newTestMysql(t, 1, w)
	s.writeRetryTimeout = time.Second
	s.nowFn = func() time.Time { return time.Unix(1000, 0) }
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 990),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Failed != 0 || result.Stats.Written != 1 || len(result.Stats.Samples) != 1 {
		t.Fatalf("expected one success sample, failed=%d stats=%+v", result.Failed, result.Stats)
	}
}

func TestSaveBatchUnusableTimestampsStillWritten(t *testing.T) {
	t.Parallel()
	s := newTestMysql(t, 1, &fakeChunkWriter{})
	s.nowFn = func() time.Time { return time.Unix(1000, 0) }
	msgs := []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 0),
		sampleAt(t, 3307, "default", haprobe.DbTypeMySql, uint64(math.MaxInt64/1000)+1),
		sampleAt(t, 3308, "default", haprobe.DbTypeRedis, 1001),
	}
	result, err := s.SaveBatch(context.Background(), msgs)
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	assertConserved(t, len(msgs), result.Stats)
	if result.Stats.Written != 3 || len(result.Stats.Samples) != 0 {
		t.Fatalf("expected 3 written and no samples, got %+v", result.Stats)
	}
}

func TestSaveBatchEarlyReturnsDoNotCountFailed(t *testing.T) {
	t.Parallel()
	s := newTestMysql(t, 1, &fakeChunkWriter{})
	msgs := []*Message{sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1)}

	closed := newTestMysql(t, 1, &fakeChunkWriter{})
	closed.closed.Store(true)
	closedResult, err := closed.SaveBatch(context.Background(), msgs)
	if err == nil || closedResult.Failed != 0 || closedResult.Stats.DropCount("", ReasonSinkClosed) != 1 {
		t.Fatalf("closed: err=%v result=%+v", err, closedResult)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	doneResult, err := s.SaveBatch(ctx, msgs)
	if err == nil || doneResult.Failed != 0 || doneResult.Stats.DropCount("", ReasonCtxDone) != 1 {
		t.Fatalf("ctx done: err=%v result=%+v", err, doneResult)
	}
	assertConserved(t, 1, closedResult.Stats)
	assertConserved(t, 1, doneResult.Stats)
}

func TestSaveBatchCtxDuringWriteIsCtxDoneNotFatal(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		<-ctx.Done()
		return ctx.Err()
	}}
	s := newTestMysql(t, 1, w)
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	result, err := s.SaveBatch(ctx, []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1),
	})
	if err == nil || result.Failed < 1 {
		t.Fatalf("expected ctx error and Failed>=1, err=%v failed=%d", err, result.Failed)
	}
	if result.Stats.DropCount("mysql", ReasonCtxDone) != 1 || result.Stats.DropCount("mysql", ReasonFatal) != 0 {
		t.Fatalf("expected ctx_done not fatal, got %+v", result.Stats)
	}
}

func TestSaveBatchReasons(t *testing.T) {
	t.Parallel()
	retry := newTestMysql(t, 1, &fakeChunkWriter{fn: func(
		ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus,
	) error {
		return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
	}})
	retry.writeRetryTimeout = 150 * time.Millisecond
	retryResult, err := retry.SaveBatch(context.Background(), []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1),
	})
	if err != nil || retryResult.Stats.DropCount("mysql", ReasonRetryTimeout) != 1 || retryResult.Failed != 1 {
		t.Fatalf("retry: err=%v failed=%d stats=%+v", err, retryResult.Failed, retryResult.Stats)
	}

	fatal := newTestMysql(t, 1, &fakeChunkWriter{fn: func(
		ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus,
	) error {
		return sql.ErrConnDone
	}})
	fatalResult, err := fatal.SaveBatch(context.Background(), []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1),
	})
	if err == nil || fatalResult.Stats.DropCount("mysql", ReasonFatal) != 1 || fatalResult.Failed != 1 {
		t.Fatalf("fatal: err=%v failed=%d stats=%+v", err, fatalResult.Failed, fatalResult.Stats)
	}
}

func TestSaveBatchFallbackCtxKeepsSuccessfulRow(t *testing.T) {
	t.Parallel()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if len(rows) > 1 {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		if rows[0].DbPort == 3306 {
			return nil
		}
		cancel()
		return context.Canceled
	}}
	s := newTestMysql(t, 1, w)
	s.batchChunkSize = 10
	s.nowFn = func() time.Time { return time.Unix(1000, 0) }
	result, err := s.SaveBatch(ctx, []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 990),
		sampleAt(t, 3307, "default", haprobe.DbTypeMySql, 990),
	})
	if err == nil {
		t.Fatal("expected ctx error")
	}
	assertConserved(t, 2, result.Stats)
	if result.Stats.Written != 1 || len(result.Stats.Samples) != 1 {
		t.Fatalf("expected the written row to keep its sample, got %+v", result.Stats)
	}
	if result.Stats.DropCount("mysql", ReasonCtxDone) != 1 {
		t.Fatalf("expected remaining row ctx_done, got %+v", result.Stats)
	}
}

func TestSaveBatchDataErrorVersusRetryTimeout(t *testing.T) {
	t.Parallel()
	both := newTestMysql(t, 1, &fakeChunkWriter{fn: func(
		ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus,
	) error {
		return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
	}})
	bothResult, err := both.SaveBatch(context.Background(), []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1),
	})
	if err != nil || bothResult.Stats.DropCount("mysql", ReasonDataError) != 1 {
		t.Fatalf("data error: err=%v stats=%+v", err, bothResult.Stats)
	}

	mixed := newTestMysql(t, 2, nil)
	badDB := mixed.dbs[0].DB()
	mixed.writer = &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if db == badDB {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
	}}
	mixed.writeRetryTimeout = 150 * time.Millisecond
	mixedResult, err := mixed.SaveBatch(context.Background(), []*Message{
		sampleAt(t, 3306, "default", haprobe.DbTypeMySql, 1),
	})
	if err != nil || mixedResult.Failed != 1 || mixedResult.Stats.DropCount("mysql", ReasonRetryTimeout) != 1 {
		t.Fatalf("mixed: err=%v failed=%d stats=%+v", err, mixedResult.Failed, mixedResult.Stats)
	}
	if mixedResult.Stats.DropCount("mysql", ReasonDataError) != 0 {
		t.Fatalf("partial data error must not win over retry timeout: %+v", mixedResult.Stats)
	}
}
