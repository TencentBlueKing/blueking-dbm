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
	"math/rand/v2"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// retentionStore is the storage subset the retainer depends on; *storage.DbhaData implements it.
type retentionStore interface {
	HasSwitchInProgress(ctx context.Context, since time.Time, timeout time.Duration) (bool, error)
	HasRecentUpdate(ctx context.Context, table string, since time.Time, timeout time.Duration) (bool, error)
	ScanStatusWindow(ctx context.Context, cursor storage.StatusCursor, limit int,
		timeout time.Duration) ([]storage.StatusWindowRow, error)
	ScanMetadataWindow(ctx context.Context, cursor storage.MetadataCursor, limit int,
		timeout time.Duration) ([]storage.MetadataWindowRow, error)
	DeleteStatusByPK(ctx context.Context, keys []storage.StatusKey, cutoff time.Time,
		timeout time.Duration) (int64, error)
	DeleteMetadataByPK(ctx context.Context, keys []storage.MetadataKey, cutoff time.Time,
		timeout time.Duration) (int64, error)
}

// retentionClock abstracts time so that scheduling and pacing can be tested without sleeping.
type retentionClock interface {
	Now() time.Time
	NewTimer(d time.Duration) (<-chan time.Time, func() bool)
}

// retentionElectionFactory creates a fresh election; each call opens its own etcd session.
type retentionElectionFactory func() (discovery.ConcurrencyElection, error)

// retentionTarget adapts one table to the shared window, cursor and delete flow.
type retentionTarget interface {
	table() string
	retention(cfg config.RetentionConfig) time.Duration
	healthWindow(cfg config.RetentionConfig) time.Duration
	scan(ctx context.Context, store retentionStore, cursor retentionCursor, limit int,
		timeout time.Duration) ([]retentionRow, error)
	delete(ctx context.Context, store retentionStore, rows []retentionRow, cutoff time.Time,
		timeout time.Duration) (int64, error)
}

// retentionOutcome is what one run proves to the stall tracker.
type retentionOutcome int

const (
	retentionElectionName         = "gc-dbha-data-retention"
	retentionBackoffMin           = time.Second
	retentionBackoffMax           = 30 * time.Second
	retentionFirstRunMin          = time.Minute
	retentionFirstRunMax          = 10 * time.Minute
	retentionSwitchCheckBatches   = 10
	retentionDefaultSwitchTimeout = 10 * time.Minute

	retentionStageSwitch = "switch_check"
	retentionStageHealth = "health_check"
	retentionStageScan   = "scan"
	retentionStageDelete = "delete"

	retentionKindTimeout  = "timeout"
	retentionKindDeadlock = "deadlock"
	retentionKindError    = "error"
	retentionKindUnknown  = "unknown"

	retentionReasonSwitching    = "switching"
	retentionReasonUnhealthy    = "unhealthy"
	retentionReasonBackpressure = "backpressure"
	retentionReasonBudget       = "budget"
)

const (
	// retentionOutcomeNeutral changes nothing: a switch in progress or a writer without recent rows.
	retentionOutcomeNeutral retentionOutcome = iota
	// retentionOutcomeProgress resets the stall timer: rows were deleted or there was nothing to do.
	retentionOutcomeProgress
	// retentionOutcomeEvidence marks pending work that was not done: candidates left, timeouts, errors.
	retentionOutcomeEvidence
)

// retentionPrefix is the primary key prefix the window cursor walks: machine_id for t_dbha_status,
// (bk_cloud_id, ip) for t_dbm_metadata.
type retentionPrefix struct {
	machineID string
	bkCloudID int
	ip        string
}

// retentionCursor is where the next window of a table starts; the zero value is the table start.
type retentionCursor struct {
	set       bool
	prefix    retentionPrefix
	exclusive bool
}

type retentionRow struct {
	prefix    retentionPrefix
	updatedAt time.Time
	key       any
}

type retentionDeleteResult struct {
	processed int
	deleted   int64
	evidence  bool
}

type retentionRunSummary struct {
	outcome    retentionOutcome
	scanned    int
	candidates int
	deleted    int64
}

// retentionTableState is the per-table scheduling state; it is discarded when leadership is lost.
type retentionTableState struct {
	target         retentionTarget
	cursor         retentionCursor
	nextRunAt      time.Time
	passStale      int64
	passScanned    int64
	lastProgressAt time.Time
	evidence       bool
}

// retainer physically deletes stale rows from t_dbm_metadata and t_dbha_status while it holds the
// retention election, so only one analysis instance per deployment cleans at a time.
type retainer struct {
	cfg           config.RetentionConfig
	switchTimeout time.Duration
	store         retentionStore
	clock         retentionClock
	metrics       retentionMetrics
	newElection   retentionElectionFactory
	randInt64N    func(n int64) int64
	tables        []*retentionTableState
}

type metadataRetentionTarget struct{}

type statusRetentionTarget struct{}

type realRetentionClock struct{}

// startRetention normalizes the retention settings and starts retention with the APM metrics and
// the etcd election of this workflow.
func (w *Workflow) startRetention(ctx context.Context) {
	cli := w.discoveryCli
	w.startRetentionWith(ctx, config.NormalizeRetention(config.Cfg.Workflow), newApmRetentionMetrics(w.myServiceID),
		func() (discovery.ConcurrencyElection, error) {
			return cli.CreateElection(retentionElectionName)
		})
}

// startRetentionWith reports whether retention is enabled and, when it is, starts the retainer
// goroutine tracked by w.wg. The goroutine stops when w.quit is closed or ctx is done. It is a no-op
// beyond the enabled gauge when retention is disabled.
func (w *Workflow) startRetentionWith(ctx context.Context, cfg config.RetentionConfig, metrics retentionMetrics,
	newElection retentionElectionFactory) {

	metrics.enabled(cfg.Enabled)
	if !cfg.Enabled {
		logger.Info("retention disabled by config")
		return
	}

	r := newRetainer(cfg, config.Cfg.Workflow.SwitchTimeout, w.hadata, metrics, newElection)
	logger.Info("retention enabled, metadata_retention: %s, status_retention: %s, interval: %s",
		cfg.MetadataRetention, cfg.StatusRetention, cfg.Interval)

	quit := w.quit
	runCtx, cancel := context.WithCancel(ctx)
	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		defer cancel()

		go func() {
			select {
			case <-quit:
				cancel()
			case <-runCtx.Done():
			}
		}()

		r.run(runCtx)
		logger.Info("the retention loop exited")
	}()
}

func newRetainer(cfg config.RetentionConfig, switchTimeout time.Duration, store retentionStore,
	metrics retentionMetrics, newElection retentionElectionFactory) *retainer {

	if switchTimeout <= 0 {
		switchTimeout = retentionDefaultSwitchTimeout
	}

	return &retainer{
		cfg:           cfg,
		switchTimeout: switchTimeout,
		store:         store,
		clock:         realRetentionClock{},
		metrics:       metrics,
		newElection:   newElection,
		randInt64N:    rand.Int64N,
		tables: []*retentionTableState{
			{target: metadataRetentionTarget{}},
			{target: statusRetentionTarget{}},
		},
	}
}

// run campaigns for the retention election and cleans the tables while leading, until ctx is done.
// Failed elections are retried with exponential backoff so that an unreachable etcd is not hammered.
func (r *retainer) run(ctx context.Context) {
	backoff := retentionBackoffMin
	failures := 0
	cappedLogged := false

	for ctx.Err() == nil {
		election, err := r.campaign(ctx)
		if err != nil {
			if ctx.Err() != nil {
				return
			}

			failures++
			reachedCap := backoff == retentionBackoffMax && !cappedLogged
			if failures == 1 || reachedCap {
				logger.Warn("retention election failed, failures: %d, retry_after: %s, errmsg: %s",
					failures, backoff, err)
				cappedLogged = cappedLogged || reachedCap
			}
			if !r.sleep(ctx, nil, backoff) {
				return
			}
			backoff = min(backoff*2, retentionBackoffMax)
			continue
		}

		backoff, failures, cappedLogged = retentionBackoffMin, 0, false
		r.lead(ctx, election)
		election.Close()
	}
}

func (r *retainer) campaign(ctx context.Context) (discovery.ConcurrencyElection, error) {
	election, err := r.newElection()
	if err != nil {
		return nil, err
	}

	if err := election.Campaign(ctx); err != nil {
		election.Close()
		return nil, err
	}

	return election, nil
}

// lead runs due tables until leadership is lost or ctx is done.
func (r *retainer) lead(ctx context.Context, election discovery.ConcurrencyElection) {
	r.onElected()
	defer r.onLost()

	for {
		wait := max(r.nextWake().Sub(r.clock.Now()), 0)
		if !r.sleep(ctx, election.Done(), wait) {
			return
		}

		r.runDue(ctx, election.Done())
	}
}

func (r *retainer) onElected() {
	now := r.clock.Now()
	tables := make([]string, 0, len(r.tables))
	for _, st := range r.tables {
		span := int64(retentionFirstRunMax - retentionFirstRunMin)
		st.cursor = retentionCursor{}
		st.nextRunAt = now.Add(retentionFirstRunMin + time.Duration(r.randInt64N(span)))
		st.passStale, st.passScanned = 0, 0
		st.lastProgressAt, st.evidence = now, false
		tables = append(tables, st.target.table())
	}

	r.metrics.elected(tables, now)
	logger.Info("retention leadership acquired")
}

func (r *retainer) onLost() {
	r.metrics.lost()
	logger.Info("retention leadership released")
}

func (r *retainer) nextWake() time.Time {
	next := r.tables[0].nextRunAt
	for _, st := range r.tables[1:] {
		if st.nextRunAt.Before(next) {
			next = st.nextRunAt
		}
	}

	return next
}

// runDue runs every table whose nextRunAt has passed. A switch in progress anywhere defers them all.
func (r *retainer) runDue(ctx context.Context, done <-chan struct{}) {
	now := r.clock.Now()
	var due []*retentionTableState
	for _, st := range r.tables {
		if !st.nextRunAt.After(now) {
			due = append(due, st)
		}
	}
	if len(due) == 0 || !r.switchCheckPasses(ctx, due, now) {
		return
	}

	for _, st := range due {
		if ctx.Err() != nil || isRetentionDone(done) {
			return
		}

		// Pushed forward first so that a panic inside the run cannot make the loop spin.
		st.nextRunAt = now.Add(r.cfg.DrainInterval)
		safe.Run(func() { r.runTable(ctx, done, st) }, safe.WithLabel("retention"))
	}
}

// switchCheckPasses reports whether no switch is in progress. On a switch or a failed check every
// due table is deferred by drainInterval; a failed check counts toward the stall alert.
func (r *retainer) switchCheckPasses(ctx context.Context, due []*retentionTableState, now time.Time) bool {
	started := r.clock.Now()
	found, err := r.store.HasSwitchInProgress(ctx, now.Add(-r.switchTimeout), r.cfg.HealthCheckTimeout)
	elapsed := r.clock.Now().Sub(started)
	if err == nil && !found {
		for _, st := range due {
			r.metrics.statement(st.target.table(), retentionStageSwitch, elapsed)
		}
		return true
	}

	for _, st := range due {
		table := st.target.table()
		r.metrics.statement(table, retentionStageSwitch, elapsed)
		st.nextRunAt = now.Add(r.cfg.DrainInterval)
		if err != nil {
			r.recordError(ctx, table, retentionStageSwitch, retentionErrorKind(err), err)
			r.trackStall(st, retentionOutcomeEvidence)
			continue
		}
		r.metrics.skipped(table, retentionReasonSwitching)
	}

	return false
}

func (r *retainer) runTable(ctx context.Context, done <-chan struct{}, st *retentionTableState) {
	started := r.clock.Now()
	summary := r.cleanTable(ctx, done, st, started)
	r.trackStall(st, summary.outcome)

	elapsed := r.clock.Now().Sub(started)
	r.metrics.round(st.target.table(), elapsed)
	logger.Info("retention run finished, table: %s, scanned: %d, candidates: %d, deleted: %d, "+
		"cost_ms: %d, next_run: %s", st.target.table(), summary.scanned, summary.candidates, summary.deleted,
		elapsed.Milliseconds(), st.nextRunAt.Format(time.DateTime))
}

// cleanTable runs the health check, scans one window from the cursor and deletes the stale rows.
func (r *retainer) cleanTable(ctx context.Context, done <-chan struct{}, st *retentionTableState,
	now time.Time) retentionRunSummary {

	if proceed, outcome := r.checkHealth(ctx, st, now); !proceed {
		return retentionRunSummary{outcome: outcome}
	}

	table := st.target.table()
	started := r.clock.Now()
	rows, err := st.target.scan(ctx, r.store, st.cursor, r.cfg.ScanWindowRows, r.cfg.ScanTimeout)
	r.metrics.statement(table, retentionStageScan, r.clock.Now().Sub(started))
	if err != nil {
		r.recordError(ctx, table, retentionStageScan, retentionErrorKind(err), err)
		st.nextRunAt = now.Add(r.cfg.DrainInterval)
		return retentionRunSummary{outcome: retentionOutcomeEvidence}
	}

	cutoff := now.Add(-st.target.retention(r.cfg))
	candidates, truncated := selectRetentionCandidates(rows, cutoff, r.cfg.MaxRowsPerRound)
	result := r.deleteCandidates(ctx, done, st, candidates, cutoff, now)
	r.advanceCursor(st, rows, candidates, result, truncated, r.clock.Now())

	summary := retentionRunSummary{scanned: len(rows), candidates: len(candidates), deleted: result.deleted}
	switch {
	case result.deleted > 0:
		summary.outcome = retentionOutcomeProgress
	case result.evidence || len(candidates) > 0:
		summary.outcome = retentionOutcomeEvidence
	default:
		summary.outcome = retentionOutcomeProgress
	}

	return summary
}

// checkHealth reports whether the table's writer updated a row within the health window. A writer
// without recent rows defers the table by interval; a failed check defers it by drainInterval.
func (r *retainer) checkHealth(ctx context.Context, st *retentionTableState,
	now time.Time) (bool, retentionOutcome) {

	table := st.target.table()
	started := r.clock.Now()
	found, err := r.store.HasRecentUpdate(ctx, table, now.Add(-st.target.healthWindow(r.cfg)),
		r.cfg.HealthCheckTimeout)
	r.metrics.statement(table, retentionStageHealth, r.clock.Now().Sub(started))

	if err != nil {
		r.recordError(ctx, table, retentionStageHealth, retentionErrorKind(err), err)
		st.nextRunAt = now.Add(r.cfg.DrainInterval)
		return false, retentionOutcomeEvidence
	}
	if !found {
		r.metrics.skipped(table, retentionReasonUnhealthy)
		st.nextRunAt = now.Add(r.cfg.Interval)
		return false, retentionOutcomeNeutral
	}

	return true, retentionOutcomeNeutral
}

// deleteCandidates deletes candidates in batches until all are processed or the run has to yield.
// processed counts the batches that need no retry: deleted, skipped on a lock conflict, or sent
// before a client timeout whose server side outcome is unknown.
func (r *retainer) deleteCandidates(ctx context.Context, done <-chan struct{}, st *retentionTableState,
	candidates []retentionRow, cutoff, started time.Time) retentionDeleteResult {

	table := st.target.table()
	result := retentionDeleteResult{}
	lastSlow := false

	for i := 0; i < len(candidates); i += r.cfg.BatchSize {
		if r.shouldYield(ctx, done, table, i/r.cfg.BatchSize, started, lastSlow, &result) {
			return result
		}

		batch := candidates[i:min(i+r.cfg.BatchSize, len(candidates))]
		deleted, elapsed, err := r.deleteBatch(ctx, st, batch, cutoff)
		if err != nil && !r.handleDeleteError(ctx, table, err, len(batch), &result) {
			return result
		}
		if err == nil {
			result.processed += len(batch)
			result.deleted += deleted
			r.metrics.attempted(table, len(batch))
			r.metrics.deleted(table, deleted)
			lastSlow = elapsed > r.cfg.SlowDeleteThreshold
		}

		if result.processed < len(candidates) && !r.sleep(ctx, done, r.cfg.BatchSleep) {
			return result
		}
	}

	return result
}

func (r *retainer) deleteBatch(ctx context.Context, st *retentionTableState, batch []retentionRow,
	cutoff time.Time) (int64, time.Duration, error) {

	started := r.clock.Now()
	deleted, err := st.target.delete(ctx, r.store, batch, cutoff, r.cfg.DeleteTimeout)
	elapsed := r.clock.Now().Sub(started)
	r.metrics.statement(st.target.table(), retentionStageDelete, elapsed)

	return deleted, elapsed, err
}

// handleDeleteError records a failed batch and reports whether deleting may continue. A lock
// conflict skips the batch; a client timeout marks it processed with an unknown outcome and ends
// the run; any other error leaves it unprocessed and ends the run.
func (r *retainer) handleDeleteError(ctx context.Context, table string, err error, size int,
	result *retentionDeleteResult) bool {

	switch storage.RetentionErrorKindOf(err) {
	case storage.RetentionErrorConflict:
		r.recordError(ctx, table, retentionStageDelete, retentionKindDeadlock, err)
		result.processed += size
		r.metrics.attempted(table, size)
		return true

	case storage.RetentionErrorTimeout:
		r.recordError(ctx, table, retentionStageDelete, retentionKindUnknown, err)
		result.processed += size
		r.metrics.attempted(table, size)
		result.evidence = true
		return false

	default:
		r.recordError(ctx, table, retentionStageDelete, retentionKindError, err)
		result.evidence = true
		return false
	}
}

// shouldYield reports whether the run must stop before the next batch: leadership lost, ctx done,
// round budget used up, the previous batch too slow, or (every few batches) a switch started.
func (r *retainer) shouldYield(ctx context.Context, done <-chan struct{}, table string, batchNo int,
	started time.Time, lastSlow bool, result *retentionDeleteResult) bool {

	if ctx.Err() != nil || isRetentionDone(done) {
		return true
	}

	now := r.clock.Now()
	if now.Sub(started) >= r.cfg.RoundTimeBudget {
		r.metrics.skipped(table, retentionReasonBudget)
		return true
	}
	if lastSlow {
		r.metrics.skipped(table, retentionReasonBackpressure)
		return true
	}
	if batchNo == 0 || batchNo%retentionSwitchCheckBatches != 0 {
		return false
	}

	found, err := r.store.HasSwitchInProgress(ctx, now.Add(-r.switchTimeout), r.cfg.HealthCheckTimeout)
	r.metrics.statement(table, retentionStageSwitch, r.clock.Now().Sub(now))
	if err != nil {
		r.recordError(ctx, table, retentionStageSwitch, retentionErrorKind(err), err)
		result.evidence = true
		return true
	}
	if found {
		r.metrics.skipped(table, retentionReasonSwitching)
		return true
	}

	return false
}

// advanceCursor moves the cursor past fully processed windows only, so no stale row is skipped
// until the next pass; an interrupted window resumes at the last processed candidate.
func (r *retainer) advanceCursor(st *retentionTableState, rows, candidates []retentionRow,
	result retentionDeleteResult, truncated bool, now time.Time) {

	st.passStale += int64(result.processed)
	st.nextRunAt = now.Add(r.cfg.DrainInterval)

	processed := candidates[:result.processed]
	if result.processed < len(candidates) || truncated {
		if result.processed > 0 {
			prefix := processed[len(processed)-1].prefix
			st.passScanned += int64(countRetentionRowsCovered(rows, processed, prefix))
			st.cursor = retentionCursor{set: true, prefix: prefix}
		}
		return
	}

	if len(rows) < r.cfg.ScanWindowRows {
		st.passScanned += int64(len(rows))
		r.metrics.passCompleted(st.target.table(), st.passStale, st.passScanned, now)
		st.cursor = retentionCursor{}
		st.passStale, st.passScanned = 0, 0
		st.nextRunAt = now.Add(r.cfg.Interval)
		return
	}

	last := rows[len(rows)-1].prefix
	// The cursor value is compared by MySQL only: an unchanged cursor after a full window means the
	// whole window shares one prefix under the column collation, so the next window skips it.
	if st.cursor.set && !st.cursor.exclusive && st.cursor.prefix == last {
		st.cursor.exclusive = true
		// Counts the whole window; rows of this prefix skipped on a lock conflict and re-read may be
		// counted twice, which is acceptable for retention_pass_scanned_rows, an approximate row count.
		st.passScanned += int64(len(rows))
		return
	}

	st.passScanned += int64(countRetentionRowsCovered(rows, processed, last))
	st.cursor = retentionCursor{set: true, prefix: last}
}

// trackStall updates the stall flag: stalled means no progress for stallAlertAfter while work or
// errors were pending. Neutral outcomes neither reset nor feed the timer.
func (r *retainer) trackStall(st *retentionTableState, outcome retentionOutcome) {
	now := r.clock.Now()
	switch outcome {
	case retentionOutcomeProgress:
		st.lastProgressAt, st.evidence = now, false
	case retentionOutcomeEvidence:
		st.evidence = true
	}

	r.metrics.stalled(st.target.table(), st.evidence && now.Sub(st.lastProgressAt) >= r.cfg.StallAlertAfter)
}

// recordError reports a failed statement. Statements cancelled because analysis is shutting down are
// not failures and are dropped silently.
func (r *retainer) recordError(ctx context.Context, table, stage, kind string, err error) {
	if ctx.Err() != nil {
		return
	}

	r.metrics.failed(table, stage, kind)
	logger.Warn("retention statement failed, table: %s, stage: %s, kind: %s, errmsg: %s",
		table, stage, kind, err)
}

// sleep waits for d and reports false when ctx or done ends first; a nil done never ends.
func (r *retainer) sleep(ctx context.Context, done <-chan struct{}, d time.Duration) bool {
	timerC, stop := r.clock.NewTimer(d)
	defer stop()

	select {
	case <-ctx.Done():
		return false

	case <-done:
		return false

	case <-timerC:
		return true
	}
}

func (metadataRetentionTarget) table() string {
	return hamodel.DbmMetadataTableName
}

func (metadataRetentionTarget) retention(cfg config.RetentionConfig) time.Duration {
	return cfg.MetadataRetention
}

func (metadataRetentionTarget) healthWindow(cfg config.RetentionConfig) time.Duration {
	return cfg.MetadataHealthWindow
}

func (metadataRetentionTarget) scan(ctx context.Context, store retentionStore, cursor retentionCursor,
	limit int, timeout time.Duration) ([]retentionRow, error) {

	window, err := store.ScanMetadataWindow(ctx, storage.MetadataCursor{
		Set:       cursor.set,
		BkCloudID: cursor.prefix.bkCloudID,
		IP:        cursor.prefix.ip,
		Exclusive: cursor.exclusive,
	}, limit, timeout)
	if err != nil {
		return nil, err
	}

	rows := make([]retentionRow, 0, len(window))
	for _, w := range window {
		rows = append(rows, retentionRow{
			prefix:    retentionPrefix{bkCloudID: w.Key.BkCloudID, ip: w.Key.IP},
			updatedAt: w.UpdatedAt,
			key:       w.Key,
		})
	}

	return rows, nil
}

func (metadataRetentionTarget) delete(ctx context.Context, store retentionStore, rows []retentionRow,
	cutoff time.Time, timeout time.Duration) (int64, error) {

	keys := make([]storage.MetadataKey, 0, len(rows))
	for _, row := range rows {
		keys = append(keys, row.key.(storage.MetadataKey))
	}

	return store.DeleteMetadataByPK(ctx, keys, cutoff, timeout)
}

func (statusRetentionTarget) table() string {
	return hamodel.DbhaDataStatusTableName
}

func (statusRetentionTarget) retention(cfg config.RetentionConfig) time.Duration {
	return cfg.StatusRetention
}

func (statusRetentionTarget) healthWindow(cfg config.RetentionConfig) time.Duration {
	return cfg.StatusHealthWindow
}

func (statusRetentionTarget) scan(ctx context.Context, store retentionStore, cursor retentionCursor,
	limit int, timeout time.Duration) ([]retentionRow, error) {

	window, err := store.ScanStatusWindow(ctx, storage.StatusCursor{
		MachineID: cursor.prefix.machineID,
		Exclusive: cursor.exclusive,
	}, limit, timeout)
	if err != nil {
		return nil, err
	}

	rows := make([]retentionRow, 0, len(window))
	for _, w := range window {
		rows = append(rows, retentionRow{
			prefix:    retentionPrefix{machineID: w.Key.MachineID},
			updatedAt: w.UpdatedAt,
			key:       w.Key,
		})
	}

	return rows, nil
}

func (statusRetentionTarget) delete(ctx context.Context, store retentionStore, rows []retentionRow,
	cutoff time.Time, timeout time.Duration) (int64, error) {

	keys := make([]storage.StatusKey, 0, len(rows))
	for _, row := range rows {
		keys = append(keys, row.key.(storage.StatusKey))
	}

	return store.DeleteStatusByPK(ctx, keys, cutoff, timeout)
}

func (realRetentionClock) Now() time.Time {
	return time.Now()
}

func (realRetentionClock) NewTimer(d time.Duration) (<-chan time.Time, func() bool) {
	t := time.NewTimer(d)
	return t.C, t.Stop
}

// selectRetentionCandidates returns the rows older than cutoff, at most limit of them, and whether
// more stale rows were left out.
func selectRetentionCandidates(rows []retentionRow, cutoff time.Time, limit int) ([]retentionRow, bool) {
	candidates := make([]retentionRow, 0)
	for _, row := range rows {
		if !row.updatedAt.Before(cutoff) {
			continue
		}
		if len(candidates) == limit {
			return candidates, true
		}
		candidates = append(candidates, row)
	}

	return candidates, false
}

// countRetentionRowsCovered counts the window rows the new cursor at prefix leaves behind for this
// pass: rows ahead of the first row with prefix, plus processed candidates sharing prefix, which
// are gone or handled and so will not be counted again when the prefix group is re-read.
func countRetentionRowsCovered(rows, processed []retentionRow, prefix retentionPrefix) int {
	covered := len(rows)
	for i, row := range rows {
		if row.prefix == prefix {
			covered = i
			break
		}
	}

	for _, row := range processed {
		if row.prefix == prefix {
			covered++
		}
	}

	return covered
}

func retentionErrorKind(err error) string {
	switch storage.RetentionErrorKindOf(err) {
	case storage.RetentionErrorTimeout:
		return retentionKindTimeout
	case storage.RetentionErrorConflict:
		return retentionKindDeadlock
	default:
		return retentionKindError
	}
}

func isRetentionDone(done <-chan struct{}) bool {
	select {
	case <-done:
		return true
	default:
		return false
	}
}
