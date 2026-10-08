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
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	mysqldriver "github.com/go-sql-driver/mysql"
	gormmysql "gorm.io/driver/mysql"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type fakeChunkWriter struct {
	mu      sync.Mutex
	calls   int
	errSeq  []error
	panicOn int
	fn      func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error
}

func (f *fakeChunkWriter) write(
	ctx context.Context,
	db *gorm.DB,
	rows []*hamodel.DbhaDataStatus,
) error {
	f.mu.Lock()
	f.calls++
	call := f.calls
	f.mu.Unlock()
	if f.panicOn > 0 && call == f.panicOn {
		panic("chunk writer panic")
	}
	if f.fn != nil {
		return f.fn(ctx, db, rows)
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	if len(f.errSeq) > 0 {
		err := f.errSeq[0]
		f.errSeq = f.errSeq[1:]
		return err
	}
	return nil
}

func (f *fakeChunkWriter) callCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.calls
}

func newTestMysql(t *testing.T, nEp int, writer chunkWriter) *mysql {
	t.Helper()
	s := &mysql{
		writer:            writer,
		batchChunkSize:    2,
		chunkMaxBytes:     defaultChunkMaxBytes,
		writeRetryTimeout: 200 * time.Millisecond,
	}
	for i := 0; i < nEp; i++ {
		gdb, err := gorm.Open(gormmysql.New(gormmysql.Config{
			Conn:                      &stubConnPool{},
			SkipInitializeWithVersion: true,
		}), &gorm.Config{})
		if err != nil {
			t.Fatalf("open gorm failed, errmsg: %s", err)
		}
		s.dbs = append(s.dbs, hamysql.WithGormDB(gdb, nil))
	}
	return s
}

type stubConnPool struct {
	beginCalls atomic.Int32
	mu         sync.Mutex
	execSQLs   []string
}

func (p *stubConnPool) PrepareContext(context.Context, string) (*sql.Stmt, error) {
	return nil, errors.New("not implemented")
}
func (p *stubConnPool) ExecContext(_ context.Context, query string, _ ...interface{}) (sql.Result, error) {
	p.mu.Lock()
	p.execSQLs = append(p.execSQLs, query)
	p.mu.Unlock()
	return stubResult{}, nil
}
func (p *stubConnPool) QueryContext(context.Context, string, ...interface{}) (*sql.Rows, error) {
	return nil, errors.New("not implemented")
}
func (p *stubConnPool) QueryRowContext(context.Context, string, ...interface{}) *sql.Row {
	return nil
}
func (p *stubConnPool) BeginTx(context.Context, *sql.TxOptions) (gorm.ConnPool, error) {
	p.beginCalls.Add(1)
	return p, nil
}
func (p *stubConnPool) Commit() error   { return nil }
func (p *stubConnPool) Rollback() error { return nil }

type stubResult struct{}

func (stubResult) LastInsertId() (int64, error) { return 0, nil }
func (stubResult) RowsAffected() (int64, error) { return 1, nil }

func sampleMsg(t *testing.T, ip string, port int, harvest string) *Message {
	t.Helper()
	hd := &haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			MachineID:   "m1",
			BkCloudID:   0,
			DbIp:        ip,
			DbPort:      port,
			HarvestType: haprobe.HarvestType(harvest),
			DbTypeName:  haprobe.DbTypeMySql,
		},
	}
	if harvest == "" {
		hd.HarvestType = ""
	}
	b, err := json.Marshal(hd)
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}
	return &Message{Topic: "t", Data: b}
}

func TestSaveBatchDedupAndSort(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{}
	s := newTestMysql(t, 1, w)

	msgs := []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
		sampleMsg(t, "127.0.0.1", 3307, "default"),
		sampleMsg(t, "127.0.0.1", 3306, "default"),
		sampleMsg(t, "127.0.0.1", 3306, ""),
	}
	result, err := s.SaveBatch(context.Background(), msgs)
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Valid != 4 || result.Invalid != 0 || result.Failed != 0 {
		t.Fatalf("unexpected result: %+v", result)
	}
	if w.callCount() != 1 {
		t.Fatalf("expected 1 chunk write after dedup, got %d", w.callCount())
	}
}

func TestSaveBatchInvalidJSON(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{}
	s := newTestMysql(t, 1, w)
	result, err := s.SaveBatch(context.Background(), []*Message{
		{Topic: "t", Data: []byte("not-json")},
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Valid != 1 || result.Invalid != 1 || result.Failed != 0 {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestSaveBatchChunking(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{}
	s := newTestMysql(t, 1, w)
	s.batchChunkSize = 2
	msgs := []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
		sampleMsg(t, "127.0.0.1", 3307, "default"),
		sampleMsg(t, "127.0.0.1", 3308, "default"),
	}
	_, err := s.SaveBatch(context.Background(), msgs)
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if w.callCount() != 2 {
		t.Fatalf("expected 2 chunks, got %d", w.callCount())
	}
}

func TestSaveBatchAnyEndpointSuccess(t *testing.T) {
	t.Parallel()
	var calls atomic.Int32
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		n := calls.Add(1)
		if n%2 == 1 {
			return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
		}
		return nil
	}}
	s := newTestMysql(t, 2, w)
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Failed != 0 {
		t.Fatalf("expected Failed=0 when any endpoint ok, got %d", result.Failed)
	}
}

func TestSaveBatchRetryThenFail(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
	}}
	s := newTestMysql(t, 1, w)
	s.writeRetryTimeout = 150 * time.Millisecond
	start := time.Now()
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	if err != nil {
		t.Fatalf("expected nil error on retry timeout, got: %s", err)
	}
	if result.Failed != 1 {
		t.Fatalf("expected Failed=1, got %d", result.Failed)
	}
	if time.Since(start) > 2*time.Second {
		t.Fatalf("retry took too long: %s", time.Since(start))
	}
}

func TestSaveBatchRetryBackoffStopsAtDeadline(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
	}}
	s := newTestMysql(t, 1, w)
	s.writeRetryTimeout = time.Second
	start := time.Now()
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	elapsed := time.Since(start)
	if err != nil || result.Failed != 1 || result.Stats.DropCount("mysql", ReasonRetryTimeout) != 1 {
		t.Fatalf("err: %v, failed: %d, stats: %+v", err, result.Failed, result.Stats)
	}
	if elapsed >= 1300*time.Millisecond {
		t.Fatalf("retry exceeded clamped deadline, elapsed: %s", elapsed)
	}
}

func TestSaveBatchCtxCancel(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		return context.DeadlineExceeded
	}}
	s := newTestMysql(t, 1, w)
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	result, err := s.SaveBatch(ctx, []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	if err == nil {
		t.Fatal("expected non-nil error when ctx done")
	}
	if result.Failed < 1 {
		t.Fatalf("expected Failed>=1, got %d", result.Failed)
	}
}

func TestSaveBatchDataFallback(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if len(rows) > 1 {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		if rows[0].DbPort == 3307 {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		return nil
	}}
	s := newTestMysql(t, 1, w)
	s.batchChunkSize = 10
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
		sampleMsg(t, "127.0.0.1", 3307, "default"),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Failed != 1 {
		t.Fatalf("expected Failed=1 bad row, got %d", result.Failed)
	}
}

func TestSaveBatchEndpointPanicRepanic(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{panicOn: 1}
	s := newTestMysql(t, 2, w)
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected re-panic from SaveBatch")
		}
	}()
	_, _ = s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	t.Fatal("should not reach")
}

func TestGormChunkWriterNoTx(t *testing.T) {
	t.Parallel()
	pool := &stubConnPool{}
	gdb, err := gorm.Open(gormmysql.New(gormmysql.Config{
		Conn:                      pool,
		SkipInitializeWithVersion: true,
	}), &gorm.Config{})
	if err != nil {
		t.Fatalf("open gorm failed, errmsg: %s", err)
	}
	row := hamodel.NewDbhaData(&haprobe.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			MachineID:   "m1",
			DbIp:        "127.0.0.1",
			DbPort:      3306,
			HarvestType: haprobe.HarvestTypeDefault,
			DbTypeName:  haprobe.DbTypeMySql,
		},
	})
	_ = gdb.Session(&gorm.Session{SkipDefaultTransaction: true}).
		Clauses(clause.OnConflict{UpdateAll: true}).
		Create(row).Error
	if pool.beginCalls.Load() != 0 {
		t.Fatalf("expected BeginTx=0 with SkipDefaultTransaction, got %d", pool.beginCalls.Load())
	}
}

func TestSaveBatchRetriesTransientRowBesideDataError(t *testing.T) {
	t.Parallel()
	var mu sync.Mutex
	attempts := map[int]int{}
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if len(rows) > 1 {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		port := rows[0].DbPort
		mu.Lock()
		attempts[port]++
		n := attempts[port]
		mu.Unlock()
		if port == 3306 && n == 1 {
			return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
		}
		if port == 3307 {
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		return nil
	}}
	s := newTestMysql(t, 1, w)
	s.batchChunkSize = 10
	s.writeRetryTimeout = time.Second
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
		sampleMsg(t, "127.0.0.1", 3307, "default"),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Failed != 1 {
		t.Fatalf("expected Failed=1, got %d", result.Failed)
	}
	mu.Lock()
	defer mu.Unlock()
	if attempts[3306] < 2 {
		t.Fatalf("expected transient row to be retried, attempts: %d", attempts[3306])
	}
	if attempts[3307] != 1 {
		t.Fatalf("expected data-error row not retried, attempts: %d", attempts[3307])
	}
}

func TestSaveBatchRetriesOtherEndpointAfterDataError(t *testing.T) {
	t.Parallel()
	s := newTestMysql(t, 2, nil)
	badDB := s.dbs[0].DB()
	var badCalls atomic.Int32
	var goodCalls atomic.Int32
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if db == badDB {
			badCalls.Add(1)
			return &mysqldriver.MySQLError{Number: 1406, Message: "too long"}
		}
		if goodCalls.Add(1) == 1 {
			return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
		}
		return nil
	}}
	s.writer = w
	s.writeRetryTimeout = time.Second
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Failed != 0 {
		t.Fatalf("expected Failed=0 after the other endpoint recovered, got %d", result.Failed)
	}
	if goodCalls.Load() < 2 {
		t.Fatalf("expected transient endpoint to retry, calls: %d", goodCalls.Load())
	}
	if badCalls.Load() != 2 {
		t.Fatalf("expected data-error endpoint not retried, calls: %d", badCalls.Load())
	}
}

func TestSaveBatchFatalSkipsSuccessfulRows(t *testing.T) {
	t.Parallel()
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		if rows[0].DbPort == 3306 {
			return nil
		}
		return sql.ErrConnDone
	}}
	s := newTestMysql(t, 1, w)
	s.batchChunkSize = 1
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
		sampleMsg(t, "127.0.0.1", 3307, "default"),
	})
	if err == nil {
		t.Fatal("expected non-nil error on fatal write")
	}
	if result.Failed != 1 {
		t.Fatalf("expected Failed=1, got %d", result.Failed)
	}
	if w.callCount() != 2 {
		t.Fatalf("expected no retry after fatal, calls: %d", w.callCount())
	}
}

func TestSaveBatchDurationObservedOncePerEndpoint(t *testing.T) {
	t.Parallel()
	var mu sync.Mutex
	attempts := map[*gorm.DB]int{}
	w := &fakeChunkWriter{fn: func(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
		mu.Lock()
		attempts[db]++
		n := attempts[db]
		mu.Unlock()
		if n == 1 {
			return &mysqldriver.MySQLError{Number: 1290, Message: "readonly"}
		}
		return nil
	}}
	s := newTestMysql(t, 2, w)
	s.writeRetryTimeout = time.Second
	var observes atomic.Int32
	s.recordDuration = func(topic string, ms float64) {
		observes.Add(1)
	}
	result, err := s.SaveBatch(context.Background(), []*Message{
		sampleMsg(t, "127.0.0.1", 3306, "default"),
	})
	if err != nil {
		t.Fatalf("SaveBatch failed, errmsg: %s", err)
	}
	if result.Failed != 0 {
		t.Fatalf("expected Failed=0, got %d", result.Failed)
	}
	if observes.Load() != 2 {
		t.Fatalf("expected one duration observe per endpoint, got %d", observes.Load())
	}
}

func TestSplitChunksSingleOversizedRow(t *testing.T) {
	t.Parallel()
	rows := []preparedRow{
		{data: &hamodel.DbhaDataStatus{DbIp: "127.0.0.1", DbPort: 1}, size: 10},
		{data: &hamodel.DbhaDataStatus{DbIp: "127.0.0.1", DbPort: 2}, size: 100},
		{data: &hamodel.DbhaDataStatus{DbIp: "127.0.0.1", DbPort: 3}, size: 10},
	}
	chunks := splitChunks(rows, 10, 50)
	if len(chunks) != 3 {
		t.Fatalf("expected 3 chunks for oversized middle row, got %d", len(chunks))
	}
}
