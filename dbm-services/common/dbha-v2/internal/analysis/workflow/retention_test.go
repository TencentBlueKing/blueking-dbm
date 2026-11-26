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

package workflow

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"

	mysqldriver "github.com/go-sql-driver/mysql"
)

var retentionTestEpoch = time.Date(2026, 1, 1, 0, 0, 0, 0, time.Local)

// fakeRetentionClock advances its own time on every timer instead of sleeping.
type fakeRetentionClock struct {
	mu     sync.Mutex
	now    time.Time
	sleeps []time.Duration
}

func (c *fakeRetentionClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.now
}

func (c *fakeRetentionClock) NewTimer(d time.Duration) (<-chan time.Time, func() bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.sleeps = append(c.sleeps, d)
	c.now = c.now.Add(d)
	ch := make(chan time.Time, 1)
	ch <- c.now
	return ch, func() bool { return true }
}

func (c *fakeRetentionClock) advance(d time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.now = c.now.Add(d)
}

// fakeRetentionStore emulates both tables in memory with the same window and delete semantics as
// the MySQL implementation.
type fakeRetentionStore struct {
	clock       *fakeRetentionClock
	status      []storage.StatusWindowRow
	metadata    []storage.MetadataWindowRow
	switchFound bool
	switchErr   error
	switchCalls int
	unhealthy   map[string]bool
	healthErr   error
	healthCalls map[string]int
	healthPanic bool
	scanErr     error
	deleteErrs  []error
	deleteDelay time.Duration
	deleteCalls int
}

func newFakeRetentionStore(clock *fakeRetentionClock) *fakeRetentionStore {
	return &fakeRetentionStore{clock: clock, unhealthy: map[string]bool{}, healthCalls: map[string]int{}}
}

func (s *fakeRetentionStore) HasSwitchInProgress(context.Context, time.Time, time.Duration) (bool, error) {
	s.switchCalls++
	return s.switchFound, s.switchErr
}

func (s *fakeRetentionStore) HasRecentUpdate(_ context.Context, table string, _ time.Time,
	_ time.Duration) (bool, error) {

	if s.healthPanic {
		panic("health check exploded")
	}
	s.healthCalls[table]++
	return !s.unhealthy[table], s.healthErr
}

func (s *fakeRetentionStore) ScanStatusWindow(_ context.Context, cursor storage.StatusCursor, limit int,
	_ time.Duration) ([]storage.StatusWindowRow, error) {

	if s.scanErr != nil {
		return nil, s.scanErr
	}
	var out []storage.StatusWindowRow
	for _, row := range s.status {
		id := row.Key.MachineID
		if id < cursor.MachineID || (cursor.Exclusive && id == cursor.MachineID) {
			continue
		}
		if len(out) == limit {
			break
		}
		out = append(out, row)
	}
	return out, nil
}

func (s *fakeRetentionStore) ScanMetadataWindow(_ context.Context, cursor storage.MetadataCursor, limit int,
	_ time.Duration) ([]storage.MetadataWindowRow, error) {

	if s.scanErr != nil {
		return nil, s.scanErr
	}
	var out []storage.MetadataWindowRow
	for _, row := range s.metadata {
		if cursor.Set {
			k := row.Key
			before := k.BkCloudID < cursor.BkCloudID || (k.BkCloudID == cursor.BkCloudID && k.IP < cursor.IP)
			same := k.BkCloudID == cursor.BkCloudID && k.IP == cursor.IP
			if before || (cursor.Exclusive && same) {
				continue
			}
		}
		if len(out) == limit {
			break
		}
		out = append(out, row)
	}
	return out, nil
}

func (s *fakeRetentionStore) nextDeleteErr() error {
	s.deleteCalls++
	s.clock.advance(s.deleteDelay)
	if len(s.deleteErrs) == 0 {
		return nil
	}
	err := s.deleteErrs[0]
	s.deleteErrs = s.deleteErrs[1:]
	return err
}

func (s *fakeRetentionStore) DeleteStatusByPK(_ context.Context, keys []storage.StatusKey, cutoff time.Time,
	_ time.Duration) (int64, error) {

	if err := s.nextDeleteErr(); err != nil {
		return 0, err
	}
	want := map[storage.StatusKey]bool{}
	for _, k := range keys {
		want[k] = true
	}

	var kept []storage.StatusWindowRow
	var deleted int64
	for _, row := range s.status {
		if want[row.Key] && row.UpdatedAt.Before(cutoff) {
			deleted++
			continue
		}
		kept = append(kept, row)
	}
	s.status = kept
	return deleted, nil
}

func (s *fakeRetentionStore) DeleteMetadataByPK(_ context.Context, keys []storage.MetadataKey, cutoff time.Time,
	_ time.Duration) (int64, error) {

	if err := s.nextDeleteErr(); err != nil {
		return 0, err
	}
	want := map[storage.MetadataKey]bool{}
	for _, k := range keys {
		want[k] = true
	}

	var kept []storage.MetadataWindowRow
	var deleted int64
	for _, row := range s.metadata {
		if want[row.Key] && row.UpdatedAt.Before(cutoff) {
			deleted++
			continue
		}
		kept = append(kept, row)
	}
	s.metadata = kept
	return deleted, nil
}

// fakeRetentionMetrics records every report keyed by its labels.
type fakeRetentionMetrics struct {
	counts       map[string]int
	sums         map[string]int64
	passes       map[string][2]int64
	stalledState map[string]bool
	electedAt    time.Time
	electedFor   []string
	lostCalls    int
	enabledState *bool
}

func newFakeRetentionMetrics() *fakeRetentionMetrics {
	return &fakeRetentionMetrics{counts: map[string]int{}, sums: map[string]int64{},
		passes: map[string][2]int64{}, stalledState: map[string]bool{}}
}

func (m *fakeRetentionMetrics) enabled(on bool) { m.enabledState = &on }
func (m *fakeRetentionMetrics) elected(tables []string, at time.Time) {
	m.electedFor, m.electedAt = tables, at
}
func (m *fakeRetentionMetrics) lost() { m.lostCalls++ }
func (m *fakeRetentionMetrics) statement(table, stage string, _ time.Duration) {
	m.counts["statement|"+table+"|"+stage]++
}
func (m *fakeRetentionMetrics) round(table string, _ time.Duration) { m.counts["round|"+table]++ }
func (m *fakeRetentionMetrics) skipped(table, reason string) {
	m.counts["skipped|"+table+"|"+reason]++
}
func (m *fakeRetentionMetrics) failed(table, stage, kind string) {
	m.counts["failed|"+table+"|"+stage+"|"+kind]++
}
func (m *fakeRetentionMetrics) attempted(table string, rows int) {
	m.sums["attempted|"+table] += int64(rows)
}
func (m *fakeRetentionMetrics) deleted(table string, rows int64) { m.sums["deleted|"+table] += rows }
func (m *fakeRetentionMetrics) passCompleted(table string, staleRows, scannedRows int64, _ time.Time) {
	m.passes[table] = [2]int64{staleRows, scannedRows}
}
func (m *fakeRetentionMetrics) stalled(table string, on bool) { m.stalledState[table] = on }

// fakeRetentionElection is an election whose Campaign result and Done channel are scripted.
type fakeRetentionElection struct {
	mu          sync.Mutex
	campaignErr error
	block       bool
	entered     chan struct{}
	done        chan struct{}
	closed      int
}

func (e *fakeRetentionElection) Campaign(ctx context.Context) error {
	if e.block {
		close(e.entered)
		<-ctx.Done()
		return ctx.Err()
	}
	return e.campaignErr
}
func (e *fakeRetentionElection) Close() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.closed++
}
func (e *fakeRetentionElection) closedCount() int {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.closed
}
func (e *fakeRetentionElection) Done() <-chan struct{} { return e.done }

func testRetentionConfig() config.RetentionConfig {
	cfg := config.DefaultRetentionConfig()
	cfg.ScanWindowRows = 4
	cfg.MaxRowsPerRound = 4
	cfg.BatchSize = 2
	return cfg
}

type retentionTestEnv struct {
	clock   *fakeRetentionClock
	store   *fakeRetentionStore
	metrics *fakeRetentionMetrics
	r       *retainer
}

func newRetentionTestEnv(cfg config.RetentionConfig) *retentionTestEnv {
	clock := &fakeRetentionClock{now: retentionTestEpoch}
	store := newFakeRetentionStore(clock)
	metrics := newFakeRetentionMetrics()
	r := newRetainer(cfg, 10*time.Minute, store, metrics, nil)
	r.clock = clock
	r.randInt64N = func(n int64) int64 { return n / 2 }
	r.onElected()
	return &retentionTestEnv{clock: clock, store: store, metrics: metrics, r: r}
}

func (e *retentionTestEnv) table(name string) *retentionTableState {
	for _, st := range e.r.tables {
		if st.target.table() == name {
			return st
		}
	}
	panic("unknown table " + name)
}

func (e *retentionTestEnv) runStatus() *retentionTableState {
	st := e.table(hamodel.DbhaDataStatusTableName)
	e.r.runTable(context.Background(), nil, st)
	return st
}

// statusRows builds rows for machines in order; stale rows are 20 days old, fresh rows are current.
func statusRows(now time.Time, spec ...string) []storage.StatusWindowRow {
	var rows []storage.StatusWindowRow
	for i, s := range spec {
		updated := now
		machine := s
		if len(s) > 1 && s[0] == '!' {
			updated = now.Add(-20 * 24 * time.Hour)
			machine = s[1:]
		}
		rows = append(rows, storage.StatusWindowRow{
			Key: storage.StatusKey{MachineID: machine, DbIP: "127.0.0.1", DbPort: 20000 + i,
				HarvestType: "default"},
			UpdatedAt: updated,
		})
	}
	sort.SliceStable(rows, func(i, j int) bool { return rows[i].Key.MachineID < rows[j].Key.MachineID })
	return rows
}

const statusTable = hamodel.DbhaDataStatusTableName

func TestRetentionDeletesOnlyStaleRows(t *testing.T) {
	cfg := testRetentionConfig()
	cfg.ScanWindowRows, cfg.MaxRowsPerRound = 100, 100
	env := newRetentionTestEnv(cfg)
	env.store.status = statusRows(env.clock.Now(), "!m1", "m1", "!m2", "m3", "!m3")

	st := env.runStatus()

	if len(env.store.status) != 2 {
		t.Fatalf("only fresh rows should remain, left: %d", len(env.store.status))
	}
	if env.metrics.sums["attempted|"+statusTable] != 3 || env.metrics.sums["deleted|"+statusTable] != 3 {
		t.Fatalf("attempted/deleted mismatch: %v", env.metrics.sums)
	}
	if got := env.metrics.passes[statusTable]; got != [2]int64{3, 5} {
		t.Fatalf("pass should report 3 stale of 5 scanned, got: %v", got)
	}
	if st.cursor != (retentionCursor{}) || !st.nextRunAt.Equal(env.clock.Now().Add(cfg.Interval)) {
		t.Fatalf("completed pass must reset cursor and wait interval, cursor: %+v, next: %s", st.cursor, st.nextRunAt)
	}
}

func TestRetentionMetadataTableFlow(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	now := env.clock.Now()
	stale := now.Add(-20 * 24 * time.Hour)
	for i, cloud := range []int{0, 0, 1, 1, 2} {
		updated := now
		if i%2 == 0 {
			updated = stale
		}
		env.store.metadata = append(env.store.metadata, storage.MetadataWindowRow{
			Key:       storage.MetadataKey{BkCloudID: cloud, IP: "127.0.0.1", Port: 20000 + i},
			UpdatedAt: updated,
		})
	}

	st := env.table(hamodel.DbmMetadataTableName)
	env.r.runTable(context.Background(), nil, st)
	want := retentionCursor{set: true, prefix: retentionPrefix{bkCloudID: 1, ip: "127.0.0.1"}}
	if st.cursor != want {
		t.Fatalf("metadata cursor must move to the (bk_cloud_id, ip) of the window end, got: %+v", st.cursor)
	}

	env.r.runTable(context.Background(), nil, st)
	if st.cursor.set || len(env.store.metadata) != 2 {
		t.Fatalf("metadata pass must finish with only fresh rows left, left: %d", len(env.store.metadata))
	}
	if got := env.metrics.passes[hamodel.DbmMetadataTableName]; got != [2]int64{3, 5} {
		t.Fatalf("metadata pass should report 3 stale of 5 scanned, got: %v", got)
	}
}

func TestRetentionWindowCursorAdvancesAcrossPass(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "m1", "m1", "m2", "m2", "m3", "m3", "m4", "m4", "m5", "m5")

	st := env.runStatus()
	if st.cursor != (retentionCursor{set: true, prefix: retentionPrefix{machineID: "m2"}}) {
		t.Fatalf("full window must move cursor to the last prefix, got: %+v", st.cursor)
	}
	if !st.nextRunAt.Equal(env.clock.Now().Add(env.r.cfg.DrainInterval)) {
		t.Fatalf("an unfinished pass must continue after drainInterval")
	}

	for i := 0; i < 10 && st.cursor.set; i++ {
		env.runStatus()
	}
	if st.cursor.set {
		t.Fatalf("pass did not finish")
	}
	if got := env.metrics.passes[statusTable]; got != [2]int64{0, 10} {
		t.Fatalf("each row must be counted once per pass, got: %v", got)
	}
}

func TestRetentionCursorSkipsWindowInsideOnePrefix(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "m1", "m1", "m1", "m1", "m1", "m1", "m2")

	st := env.runStatus()
	st = env.runStatus()
	if !st.cursor.exclusive || st.cursor.prefix.machineID != "m1" {
		t.Fatalf("unchanged cursor after a full window must become exclusive, got: %+v", st.cursor)
	}

	env.runStatus()
	if st.cursor.set {
		t.Fatalf("the window after the exclusive cursor should reach the table end, got: %+v", st.cursor)
	}
}

func TestRetentionTruncatedWindowResumesAtLastProcessed(t *testing.T) {
	cfg := testRetentionConfig()
	cfg.MaxRowsPerRound = 2
	env := newRetentionTestEnv(cfg)
	env.store.status = statusRows(env.clock.Now(), "!m1", "!m1", "!m2", "!m2")

	st := env.runStatus()
	if st.cursor.prefix.machineID != "m1" || len(env.store.status) != 2 {
		t.Fatalf("truncated run must stop at the last processed prefix, cursor: %+v, left: %d",
			st.cursor, len(env.store.status))
	}

	env.runStatus()
	if len(env.store.status) != 0 || st.cursor.set {
		t.Fatalf("second run must finish the stale rows and the pass, left: %d", len(env.store.status))
	}
	if env.metrics.sums["attempted|"+statusTable] != 4 {
		t.Fatalf("re-read candidates must not be counted twice, attempted: %d",
			env.metrics.sums["attempted|"+statusTable])
	}
	if got := env.metrics.passes[statusTable]; got != [2]int64{4, 4} {
		t.Fatalf("an interrupted pass must count each row once, got: %v", got)
	}
}

func TestRetentionUnhealthyWriterSkipsTable(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "!m1")
	env.store.unhealthy[statusTable] = true

	st := env.runStatus()
	if len(env.store.status) != 1 || env.metrics.counts["skipped|"+statusTable+"|unhealthy"] != 1 {
		t.Fatalf("unhealthy writer must skip the table: %v", env.metrics.counts)
	}
	if !st.nextRunAt.Equal(env.clock.Now().Add(env.r.cfg.Interval)) || st.evidence {
		t.Fatalf("unhealthy skip waits interval and is neutral for the stall alert")
	}
}

func TestRetentionStatementErrorsKeepCursor(t *testing.T) {
	cases := []struct {
		name   string
		setup  func(s *fakeRetentionStore)
		metric string
	}{
		{"health error", func(s *fakeRetentionStore) { s.healthErr = errors.New("connection refused") },
			"failed|" + statusTable + "|health_check|error"},
		{"scan timeout", func(s *fakeRetentionStore) {
			s.scanErr = gerrors.NewE(gerrors.Timeout, &mysqldriver.MySQLError{Number: 3024})
		}, "failed|" + statusTable + "|scan|timeout"},
		{"delete denied", func(s *fakeRetentionStore) {
			s.deleteErrs = []error{&mysqldriver.MySQLError{Number: 1142}}
		}, "failed|" + statusTable + "|delete|error"},
	}

	for _, c := range cases {
		env := newRetentionTestEnv(testRetentionConfig())
		env.store.status = statusRows(env.clock.Now(), "!m1", "!m2")
		c.setup(env.store)

		st := env.runStatus()
		if env.metrics.counts[c.metric] != 1 {
			t.Fatalf("%s: metric %s missing: %v", c.name, c.metric, env.metrics.counts)
		}
		if st.cursor.set || !st.evidence || len(env.store.status) != 2 {
			t.Fatalf("%s: cursor must stay and the error counts toward the stall alert", c.name)
		}
		if env.metrics.sums["attempted|"+statusTable] != 0 {
			t.Fatalf("%s: unprocessed batches must not count as attempted", c.name)
		}
		if !st.nextRunAt.Equal(env.clock.Now().Add(env.r.cfg.DrainInterval)) {
			t.Fatalf("%s: errors retry after drainInterval", c.name)
		}
	}
}

func TestRetentionShutdownErrorsAreNotRecorded(t *testing.T) {
	metric := "failed|" + statusTable + "|health_check|error"

	env := newRetentionTestEnv(testRetentionConfig())
	env.store.healthErr = context.Canceled
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	env.r.runTable(ctx, nil, env.table(statusTable))
	if env.metrics.counts[metric] != 0 {
		t.Fatalf("a statement cancelled by shutdown must not be recorded as a failure")
	}

	env = newRetentionTestEnv(testRetentionConfig())
	env.store.healthErr = context.Canceled
	env.runStatus()
	if env.metrics.counts[metric] != 1 {
		t.Fatalf("the same error must still be recorded while analysis is running")
	}
}

func TestRetentionDeleteConflictSkipsBatch(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "!m1", "!m1", "!m2", "!m2")
	env.store.deleteErrs = []error{gerrors.NewE(gerrors.MysqlFailure, &mysqldriver.MySQLError{Number: 1213})}

	env.runStatus()
	if env.metrics.counts["failed|"+statusTable+"|delete|deadlock"] != 1 {
		t.Fatalf("deadlock must be recorded: %v", env.metrics.counts)
	}
	if env.metrics.sums["attempted|"+statusTable] != 4 || env.metrics.sums["deleted|"+statusTable] != 2 {
		t.Fatalf("conflicted batch is processed but not deleted: %v", env.metrics.sums)
	}
	if len(env.store.status) != 2 || env.store.deleteCalls != 2 {
		t.Fatalf("deleting must continue after a conflict, left: %d", len(env.store.status))
	}
}

func TestRetentionDeleteTimeoutIsUnknown(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "!m1", "!m1", "!m2", "!m2")
	env.store.deleteErrs = []error{gerrors.NewE(gerrors.Timeout, context.DeadlineExceeded)}

	st := env.runStatus()
	if env.metrics.counts["failed|"+statusTable+"|delete|unknown"] != 1 || env.store.deleteCalls != 1 {
		t.Fatalf("client timeout must be unknown and end the run: %v", env.metrics.counts)
	}
	if st.cursor.prefix.machineID != "m1" || !st.evidence {
		t.Fatalf("timed out batch counts as processed, cursor: %+v", st.cursor)
	}
}

func TestRetentionSlowDeleteYields(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "!m1", "!m1", "!m2", "!m2")
	env.store.deleteDelay = 2 * env.r.cfg.SlowDeleteThreshold

	st := env.runStatus()
	if env.metrics.counts["skipped|"+statusTable+"|backpressure"] != 1 || env.store.deleteCalls != 1 {
		t.Fatalf("slow batch must stop the run: %v", env.metrics.counts)
	}
	if st.cursor.prefix.machineID != "m1" {
		t.Fatalf("cursor must stay at the last processed candidate, got: %+v", st.cursor)
	}
}

func TestRetentionRoundBudgetYields(t *testing.T) {
	cfg := testRetentionConfig()
	cfg.RoundTimeBudget = 150 * time.Millisecond
	env := newRetentionTestEnv(cfg)
	env.store.status = statusRows(env.clock.Now(), "!m1", "!m1", "!m2", "!m2")

	env.runStatus()
	if env.metrics.counts["skipped|"+statusTable+"|budget"] != 1 || env.store.deleteCalls != 1 {
		t.Fatalf("exhausted budget must stop the run: %v", env.metrics.counts)
	}
}

func TestRetentionSwitchCheckedEveryTenBatches(t *testing.T) {
	cfg := testRetentionConfig()
	cfg.ScanWindowRows, cfg.MaxRowsPerRound, cfg.BatchSize = 20, 20, 1
	cfg.BatchSleep = 0
	env := newRetentionTestEnv(cfg)
	spec := make([]string, 0, 12)
	for i := 0; i < 12; i++ {
		spec = append(spec, fmt.Sprintf("!m%02d", i))
	}
	env.store.status = statusRows(env.clock.Now(), spec...)
	env.store.switchFound = true

	env.runStatus()
	if env.store.deleteCalls != 10 || env.metrics.counts["skipped|"+statusTable+"|switching"] != 1 {
		t.Fatalf("a switch seen at batch 10 must stop the run, deletes: %d", env.store.deleteCalls)
	}
	if env.store.switchCalls != 1 {
		t.Fatalf("the switch must be checked only before batch 10, checks: %d", env.store.switchCalls)
	}
}

func TestRetentionGlobalSwitchDefersDueTables(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	for _, st := range env.r.tables {
		st.nextRunAt = env.clock.Now()
	}
	env.store.switchFound = true

	env.r.runDue(context.Background(), nil)
	for _, st := range env.r.tables {
		table := st.target.table()
		if env.metrics.counts["skipped|"+table+"|switching"] != 1 || env.store.healthCalls[table] != 0 {
			t.Fatalf("switch in progress must defer %s without touching it", table)
		}
		if !st.nextRunAt.Equal(env.clock.Now().Add(env.r.cfg.DrainInterval)) || st.evidence {
			t.Fatalf("switching defers by drainInterval and is neutral for the stall alert")
		}
	}

	env.store.switchFound, env.store.switchErr = false, errors.New("table missing")
	for _, st := range env.r.tables {
		st.nextRunAt = env.clock.Now()
	}
	env.r.runDue(context.Background(), nil)
	for _, st := range env.r.tables {
		table := st.target.table()
		if env.metrics.counts["failed|"+table+"|switch_check|error"] != 1 || !st.evidence {
			t.Fatalf("a failed switch check must be recorded per table and count toward the stall alert")
		}
	}
}

func TestRetentionTablesScheduleIndependently(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.table(hamodel.DbmMetadataTableName).nextRunAt = env.clock.Now().Add(time.Hour)
	env.table(statusTable).nextRunAt = env.clock.Now()

	env.r.runDue(context.Background(), nil)
	if env.store.healthCalls[statusTable] != 1 || env.store.healthCalls[hamodel.DbmMetadataTableName] != 0 {
		t.Fatalf("only the due table may run: %v", env.store.healthCalls)
	}
}

func TestRetentionPanicStillAdvancesSchedule(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	st := env.table(statusTable)
	st.nextRunAt = env.clock.Now()
	env.table(hamodel.DbmMetadataTableName).nextRunAt = env.clock.Now().Add(time.Hour)
	env.store.healthPanic = true

	env.r.runDue(context.Background(), nil)
	if !st.nextRunAt.Equal(env.clock.Now().Add(env.r.cfg.DrainInterval)) {
		t.Fatalf("a panicking run must not leave the table due, next: %s", st.nextRunAt)
	}
}

func TestRetentionStallAlert(t *testing.T) {
	cfg := testRetentionConfig()
	cfg.StallAlertAfter = time.Hour
	env := newRetentionTestEnv(cfg)
	env.store.status = statusRows(env.clock.Now(), "!m1")
	conflict := &mysqldriver.MySQLError{Number: 1213}

	for i := 0; i < 3; i++ {
		env.store.deleteErrs = []error{conflict}
		env.runStatus()
		env.clock.advance(40 * time.Minute)
	}
	env.store.deleteErrs = []error{conflict}
	env.runStatus()
	if !env.metrics.stalledState[statusTable] {
		t.Fatalf("pending rows with no progress for stallAlertAfter must raise the stall flag")
	}

	env.store.unhealthy[statusTable] = true
	env.runStatus()
	if !env.metrics.stalledState[statusTable] {
		t.Fatalf("an unhealthy skip is neutral and must not clear the stall flag")
	}

	env.store.unhealthy[statusTable] = false
	env.runStatus()
	if env.metrics.stalledState[statusTable] {
		t.Fatalf("deleting rows must clear the stall flag")
	}
}

func TestRetentionIdleRunIsProgress(t *testing.T) {
	cfg := testRetentionConfig()
	cfg.StallAlertAfter = time.Hour
	env := newRetentionTestEnv(cfg)
	env.store.status = statusRows(env.clock.Now(), "m1")

	env.clock.advance(2 * time.Hour)
	env.runStatus()
	st := env.table(statusTable)
	if st.evidence || !st.lastProgressAt.Equal(env.clock.Now()) || env.metrics.stalledState[statusTable] {
		t.Fatalf("a run with nothing to delete counts as progress")
	}
}

func TestRetentionLeadershipLostStopsDeleting(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	env.store.status = statusRows(env.clock.Now(), "!m1", "!m2")
	done := make(chan struct{})
	close(done)

	env.r.runTable(context.Background(), done, env.table(statusTable))
	if env.store.deleteCalls != 0 || len(env.store.status) != 2 {
		t.Fatalf("a lost leadership must stop before deleting")
	}
}

func TestRetentionElectionMetrics(t *testing.T) {
	env := newRetentionTestEnv(testRetentionConfig())
	if len(env.metrics.electedFor) != 2 || !env.metrics.electedAt.Equal(retentionTestEpoch) {
		t.Fatalf("election must start both pass timers at the election time: %v", env.metrics.electedFor)
	}
	for _, st := range env.r.tables {
		delay := st.nextRunAt.Sub(retentionTestEpoch)
		if delay < retentionFirstRunMin || delay > retentionFirstRunMax {
			t.Fatalf("first run must be 1m to 10m after election, got: %s", delay)
		}
	}

	env.r.onLost()
	if env.metrics.lostCalls != 1 {
		t.Fatalf("losing leadership must clear the state metrics")
	}
}

func TestRetentionElectionBackoff(t *testing.T) {
	clock := &fakeRetentionClock{now: retentionTestEpoch}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	calls := 0
	var elections []*fakeRetentionElection
	factory := func() (discovery.ConcurrencyElection, error) {
		calls++
		switch {
		case calls <= 3:
			return nil, errors.New("etcd unavailable")
		case calls <= 7:
			e := &fakeRetentionElection{campaignErr: errors.New("campaign failed")}
			elections = append(elections, e)
			return e, nil
		default:
			cancel()
			return nil, errors.New("stop")
		}
	}

	r := newRetainer(testRetentionConfig(), time.Minute, newFakeRetentionStore(clock), newFakeRetentionMetrics(),
		factory)
	r.clock = clock
	r.run(ctx)

	want := []time.Duration{1, 2, 4, 8, 16, 30, 30}
	if len(clock.sleeps) != len(want) {
		t.Fatalf("unexpected backoff sleeps: %v", clock.sleeps)
	}
	for i, d := range want {
		if clock.sleeps[i] != d*time.Second {
			t.Fatalf("backoff %d: got %s, want %ds", i, clock.sleeps[i], d)
		}
	}
	for _, e := range elections {
		if e.closedCount() != 1 {
			t.Fatalf("a failed campaign must close its election")
		}
	}
}

func TestRetentionRunStopsWhileCampaigning(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	election := &fakeRetentionElection{block: true, entered: make(chan struct{})}
	r := newRetainer(testRetentionConfig(), time.Minute, newFakeRetentionStore(&fakeRetentionClock{}),
		newFakeRetentionMetrics(), func() (discovery.ConcurrencyElection, error) { return election, nil })

	finished := make(chan struct{})
	go func() {
		r.run(ctx)
		close(finished)
	}()
	<-election.entered
	cancel()

	select {
	case <-finished:
	case <-time.After(5 * time.Second):
		t.Fatalf("run must return when ctx is cancelled during Campaign")
	}
	if election.closedCount() != 1 {
		t.Fatalf("the blocked election must be closed")
	}
}

func TestRetentionBackoffResetsAfterLeading(t *testing.T) {
	clock := &fakeRetentionClock{now: retentionTestEpoch}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	lost := make(chan struct{})
	close(lost)
	leader := &fakeRetentionElection{done: lost}
	calls := 0
	factory := func() (discovery.ConcurrencyElection, error) {
		calls++
		switch calls {
		case 3:
			return leader, nil
		case 5:
			cancel()
		}
		return nil, errors.New("etcd unavailable")
	}

	r := newRetainer(testRetentionConfig(), time.Minute, newFakeRetentionStore(clock), newFakeRetentionMetrics(),
		factory)
	r.clock = clock
	r.run(ctx)

	// Waits inside lead are either zero (a table already due) or at least a minute, so the sleeps in
	// between are the election backoff.
	var backoff []time.Duration
	for _, d := range clock.sleeps {
		if d > 0 && d < time.Minute {
			backoff = append(backoff, d)
		}
	}
	want := []time.Duration{time.Second, 2 * time.Second, time.Second}
	if fmt.Sprint(backoff) != fmt.Sprint(want) {
		t.Fatalf("backoff must restart from 1s after leading, got: %v", backoff)
	}
	if leader.closedCount() != 1 {
		t.Fatalf("the election must be closed once leadership ends, closed: %d", leader.closedCount())
	}
}

// startBlockedRetention starts retention through startRetentionWith with an election that blocks in
// Campaign, and returns once Campaign has been entered.
func startBlockedRetention(t *testing.T, metrics *fakeRetentionMetrics) (*Workflow, *fakeRetentionElection) {
	t.Helper()

	election := &fakeRetentionElection{block: true, entered: make(chan struct{})}
	w := &Workflow{quit: make(chan struct{})}
	w.startRetentionWith(context.Background(), config.DefaultRetentionConfig(), metrics,
		func() (discovery.ConcurrencyElection, error) { return election, nil })

	select {
	case <-election.entered:
	case <-time.After(5 * time.Second):
		t.Fatalf("retention never started campaigning")
	}

	return w, election
}

func waitRetentionWorkflow(t *testing.T, w *Workflow, timeout time.Duration) bool {
	t.Helper()

	waited := make(chan struct{})
	go func() {
		w.wg.Wait()
		close(waited)
	}()

	select {
	case <-waited:
		return true
	case <-time.After(timeout):
		return false
	}
}

func TestRetentionQuitStopsCampaign(t *testing.T) {
	w, election := startBlockedRetention(t, newFakeRetentionMetrics())

	close(w.quit)
	if !waitRetentionWorkflow(t, w, 5*time.Second) {
		t.Fatalf("closing w.quit must stop retention while it is campaigning")
	}
	if election.closedCount() != 1 {
		t.Fatalf("the blocked election must be closed once, closed: %d", election.closedCount())
	}
}

func TestRetentionEnabledReportsMetric(t *testing.T) {
	metrics := newFakeRetentionMetrics()
	w, _ := startBlockedRetention(t, metrics)
	defer func() {
		close(w.quit)
		waitRetentionWorkflow(t, w, 5*time.Second)
	}()

	if metrics.enabledState == nil || !*metrics.enabledState {
		t.Fatalf("enabled retention must report retention_enabled as 1")
	}
}

func TestRetentionDisabledStartsNothing(t *testing.T) {
	cfg := config.DefaultRetentionConfig()
	cfg.Enabled = false
	metrics := newFakeRetentionMetrics()
	called := false

	w := &Workflow{quit: make(chan struct{})}
	w.startRetentionWith(context.Background(), cfg, metrics, func() (discovery.ConcurrencyElection, error) {
		called = true
		return nil, errors.New("must not campaign")
	})

	if !waitRetentionWorkflow(t, w, time.Second) || called {
		t.Fatalf("disabled retention must not start a goroutine or campaign")
	}
	if metrics.enabledState == nil || *metrics.enabledState {
		t.Fatalf("disabled retention must report retention_enabled as 0")
	}
}
