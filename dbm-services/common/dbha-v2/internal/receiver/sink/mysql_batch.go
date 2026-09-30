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
	"encoding/json"
	"sort"
	"strconv"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/apm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const (
	defaultBatchChunkSize    = 200
	defaultChunkMaxBytes     = 1 << 20 // 1MB
	defaultWriteRetryTimeout = 30 * time.Second
	defaultMaxIdleConns      = 16
	defaultConnMaxLifetime   = 5 * time.Minute
	deadlockMaxRetries       = 3
	retryBackoffStart        = 100 * time.Millisecond
	retryBackoffMax          = 5 * time.Second
)

type chunkWriter interface {
	write(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error
}

type gormChunkWriter struct{}

func (gormChunkWriter) write(ctx context.Context, db *gorm.DB, rows []*hamodel.DbhaDataStatus) error {
	return db.Session(&gorm.Session{SkipDefaultTransaction: true}).
		WithContext(ctx).
		Clauses(clause.OnConflict{UpdateAll: true}).
		Create(rows).Error
}

type preparedRow struct {
	data *hamodel.DbhaDataStatus
	size int
}

type endpointChunkResult struct {
	attempted    []bool
	rowOK        []bool
	rowOKAt      []time.Time
	rowPermanent []bool
	err          error
	fatal        bool
}

type chunkWriteOutcome struct {
	failed int
	exit   string
	rowOK  [][]bool
	rowAt  [][]time.Time
	perm   [][][]bool
}

// SaveBatch writes msgs with parse-once, dedup, chunked upsert and bounded retry.
// Panic in an endpoint goroutine is re-raised on the caller after wait, so the
// handler can degrade to per-message writes. Metrics counted before a panic may
// be counted again on degrade; upsert is idempotent.
func (s *mysql) SaveBatch(ctx context.Context, msgs []*Message) (BatchResult, error) {
	if s.closed.Load() {
		return BatchResult{Stats: dropAll(len(msgs), ReasonSinkClosed)}, context.Canceled
	}
	if err := ctx.Err(); err != nil {
		return BatchResult{Stats: dropAll(len(msgs), ReasonCtxDone)}, err
	}
	if len(msgs) == 0 {
		return BatchResult{}, nil
	}

	topic := msgs[0].Topic
	rows, result, totalBytes := s.prepareBatch(msgs, topic)
	dedupDropped := result.Valid - len(rows)
	s.recordPrepareMetrics(topic, result.Valid, result.Invalid, dedupDropped, totalBytes)
	if len(rows) == 0 {
		return result, nil
	}

	chunks := splitChunks(rows, s.batchChunkSize, s.chunkMaxBytes)
	if err := apm.MySqlWriteBatchSize.ObserveWithLabels(map[string]string{
		apm.MetricLabelMysql: topic,
	}, float64(len(rows))); err != nil {
		logger.Warn("update mysql write batch size metric failed, errmsg: %s", err)
	}

	outcome, err := s.writeChunks(ctx, topic, chunks)
	result.Failed = outcome.failed
	applyWriteStats(&result, rows, chunks, outcome)
	return result, err
}

func dropAll(n int, reason string) WriteStats {
	var stats WriteStats
	stats.AddDrop("", reason, n)
	return stats
}

func (s *mysql) prepareBatch(msgs []*Message, topic string) ([]preparedRow, BatchResult, int) {
	var result BatchResult
	totalBytes := 0
	byKey := make(map[string]preparedRow, len(msgs))
	order := make([]string, 0, len(msgs))

	for _, msg := range msgs {
		hd := &haprobe.HarvestData{}
		if err := json.Unmarshal(msg.Data, hd); err != nil {
			result.Invalid++
			result.Stats.AddDrop("", ReasonInvalidJSON, 1)
			if metricErr := apm.MySqlReadErrorsTotal.IncWithLabels(map[string]string{
				apm.MetricLabelMysql: topic,
			}); metricErr != nil {
				logger.Warn("update mysql read errors metric failed, errmsg: %s", metricErr)
			}
			continue
		}
		data := hamodel.NewDbhaData(hd)
		if !data.HarvestType.IsKnown() {
			result.Invalid++
			result.Stats.AddDrop(string(data.DbTypeName), ReasonUnknownType, 1)
			continue
		}
		result.Valid++
		totalBytes += len(msg.Data)
		key := rowKey(data)
		if prev, exists := byKey[key]; exists {
			result.Stats.AddDrop(string(prev.data.DbTypeName), ReasonDedup, 1)
		} else {
			order = append(order, key)
		}
		byKey[key] = preparedRow{data: data, size: len(msg.Data)}
	}

	rows := make([]preparedRow, 0, len(order))
	for _, key := range order {
		rows = append(rows, byKey[key])
	}
	sort.Slice(rows, func(i, j int) bool {
		return rowKey(rows[i].data) < rowKey(rows[j].data)
	})
	return rows, result, totalBytes
}

func (s *mysql) recordPrepareMetrics(topic string, valid, invalid, dedupDropped, totalBytes int) {
	if dedupDropped > 0 {
		if err := apm.MySqlDedupDroppedTotal.AddWithLabels(map[string]string{
			apm.MetricLabelMysql: topic,
		}, float64(dedupDropped)); err != nil {
			logger.Warn("update mysql dedup dropped metric failed, errmsg: %s", err)
		}
	}
	if valid > 0 {
		if err := apm.MySqlWriteMessagesTotal.AddWithLabels(map[string]string{
			apm.MetricLabelMysql: topic,
		}, float64(valid)); err != nil {
			logger.Warn("update mysql write messages metric failed, errmsg: %s", err)
		}
		if err := apm.MySqlWriteBytesTotal.AddWithLabels(map[string]string{
			apm.MetricLabelMysql: topic,
		}, float64(totalBytes)); err != nil {
			logger.Warn("update mysql write bytes metric failed, errmsg: %s", err)
		}
	}
	_ = invalid
}

func rowKey(d *hamodel.DbhaDataStatus) string {
	return d.MachineID + "\x00" +
		strconv.Itoa(d.BkCloudID) + "\x00" +
		d.DbIp + "\x00" +
		strconv.Itoa(d.DbPort) + "\x00" +
		string(d.HarvestType)
}

func splitChunks(rows []preparedRow, chunkSize, maxBytes int) [][]*hamodel.DbhaDataStatus {
	if chunkSize <= 0 {
		chunkSize = defaultBatchChunkSize
	}
	if maxBytes <= 0 {
		maxBytes = defaultChunkMaxBytes
	}
	var chunks [][]*hamodel.DbhaDataStatus
	var cur []*hamodel.DbhaDataStatus
	curBytes := 0
	for _, row := range rows {
		size := row.size
		if size > maxBytes && len(cur) > 0 {
			chunks = append(chunks, cur)
			cur = nil
			curBytes = 0
		}
		if len(cur) > 0 && (len(cur) >= chunkSize || curBytes+size > maxBytes) {
			chunks = append(chunks, cur)
			cur = nil
			curBytes = 0
		}
		cur = append(cur, row.data)
		curBytes += size
		if size > maxBytes {
			chunks = append(chunks, cur)
			cur = nil
			curBytes = 0
		}
	}
	if len(cur) > 0 {
		chunks = append(chunks, cur)
	}
	return chunks
}

func (s *mysql) writeChunks(
	ctx context.Context,
	topic string,
	chunks [][]*hamodel.DbhaDataStatus,
) (chunkWriteOutcome, error) {
	rowOK, rowNeed := newRowState(len(s.dbs), chunks)
	rowAt := newRowTimes(chunks)
	perm := newPermState(len(s.dbs), chunks)
	elapsed := make([]int64, len(s.dbs))
	ran := make([]bool, len(s.dbs))
	defer s.flushBatchDurations(topic, elapsed, ran)

	deadline := time.Time{}
	backoff := retryBackoffStart
	for {
		if err := ctx.Err(); err != nil {
			return newChunkOutcome(rowOK, rowAt, perm, ReasonCtxDone), err
		}
		results, fatal := s.writeRound(ctx, topic, chunks, rowNeed, elapsed, ran)
		updateRowOutcomes(results, rowOK, rowNeed, rowAt)
		accumulatePermanent(results, perm)
		if fatal != nil {
			return newChunkOutcome(rowOK, rowAt, perm, exitFromFatal(fatal)), fatal
		}
		pending := pendingChunkCount(rowNeed)
		if pending == 0 {
			return newChunkOutcome(rowOK, rowAt, perm, ""), nil
		}
		if deadline.IsZero() {
			deadline = time.Now().Add(s.writeRetryTimeout)
		}
		if time.Now().After(deadline) {
			logger.Warn(
				"mysql batch write retry timeout, topic: %s, pending_chunks: %d",
				topic, pending,
			)
			return newChunkOutcome(rowOK, rowAt, perm, ReasonRetryTimeout), nil
		}
		if !waitCtx(ctx, backoff) {
			return newChunkOutcome(rowOK, rowAt, perm, ReasonCtxDone), ctx.Err()
		}
		backoff = growBackoff(backoff)
		if err := apm.MySqlRetryTotal.AddWithLabels(map[string]string{
			apm.MetricLabelMysql: topic,
		}, float64(pending)); err != nil {
			logger.Warn("update mysql retry metric failed, errmsg: %s", err)
		}
	}
}

func newRowState(nEp int, chunks [][]*hamodel.DbhaDataStatus) ([][]bool, [][][]bool) {
	rowOK := make([][]bool, len(chunks))
	rowNeed := make([][][]bool, nEp)
	for i := range rowNeed {
		rowNeed[i] = make([][]bool, len(chunks))
	}
	for c, chunk := range chunks {
		rowOK[c] = make([]bool, len(chunk))
		for i := 0; i < nEp; i++ {
			rowNeed[i][c] = make([]bool, len(chunk))
			for j := range chunk {
				rowNeed[i][c][j] = true
			}
		}
	}
	return rowOK, rowNeed
}

func (s *mysql) writeRound(
	ctx context.Context,
	topic string,
	chunks [][]*hamodel.DbhaDataStatus,
	rowNeed [][][]bool,
	elapsed []int64,
	ran []bool,
) ([][]endpointChunkResult, error) {
	nEp := len(s.dbs)
	results := make([][]endpointChunkResult, nEp)
	for i := range results {
		results[i] = make([]endpointChunkResult, len(chunks))
	}

	var (
		panicOnce sync.Once
		panicInfo safe.PanicInfo
		sawPanic  bool
	)
	fns := make([]func(), 0, nEp)
	for i := 0; i < nEp; i++ {
		i := i
		db := s.dbs[i].DB()
		fns = append(fns, func() {
			start := time.Now()
			ran[i] = true
			defer func() {
				atomic.AddInt64(&elapsed[i], time.Since(start).Milliseconds())
			}()
			for c, chunk := range chunks {
				if !anyTrue(rowNeed[i][c]) {
					continue
				}
				results[i][c] = s.writeChunkOnEndpoint(ctx, topic, db, chunk, rowNeed[i][c])
			}
		})
	}

	wait := safe.GoWaits(fns,
		safe.WithLabel("mysql-batch-endpoint"),
		safe.WithOnPanic(func(pi safe.PanicInfo) {
			panicOnce.Do(func() {
				panicInfo = pi
				sawPanic = true
			})
		}),
	)
	wait()
	if sawPanic {
		panic(panicInfo.Reason)
	}
	if err := ctx.Err(); err != nil {
		return results, err
	}
	for i := range results {
		for c := range results[i] {
			if results[i][c].fatal {
				return results, results[i][c].err
			}
		}
	}
	return results, nil
}

func (s *mysql) writeChunkOnEndpoint(
	ctx context.Context,
	topic string,
	db *gorm.DB,
	chunk []*hamodel.DbhaDataStatus,
	mask []bool,
) endpointChunkResult {
	indexes := maskedIndexes(mask)
	if len(indexes) == 0 {
		return endpointChunkResult{}
	}
	if err := ctx.Err(); err != nil {
		return fatalResult(len(chunk), indexes, err)
	}
	rows := pickRows(chunk, indexes)
	return s.writeSelected(ctx, topic, db, chunk, indexes, rows)
}

func (s *mysql) writeSelected(
	ctx context.Context,
	topic string,
	db *gorm.DB,
	chunk []*hamodel.DbhaDataStatus,
	indexes []int,
	rows []*hamodel.DbhaDataStatus,
) endpointChunkResult {
	var lastErr error
	for attempt := 0; attempt <= deadlockMaxRetries; attempt++ {
		if err := ctx.Err(); err != nil {
			return fatalResult(len(chunk), indexes, err)
		}
		err := s.writer.write(ctx, db, rows)
		if err == nil {
			return successResult(len(chunk), indexes, s.currentTime())
		}
		lastErr = err
		if ctx.Err() != nil {
			return fatalResult(len(chunk), indexes, ctx.Err())
		}
		res, done := s.classifyChunkWrite(ctx, topic, db, chunk, indexes, rows, err, attempt)
		if done {
			return res
		}
	}
	return transientResult(len(chunk), indexes, lastErr)
}

func (s *mysql) classifyChunkWrite(
	ctx context.Context,
	topic string,
	db *gorm.DB,
	chunk []*hamodel.DbhaDataStatus,
	indexes []int,
	rows []*hamodel.DbhaDataStatus,
	err error,
	attempt int,
) (endpointChunkResult, bool) {
	kind := classifyMySQLError(err)
	s.incWriteErrors(topic, len(rows))
	switch kind {
	case mysqlErrFatal:
		return fatalResult(len(chunk), indexes, err), true
	case mysqlErrData:
		return s.fallbackPerRow(ctx, topic, db, chunk, indexes), true
	case mysqlErrDeadlock:
		if attempt >= deadlockMaxRetries {
			return transientResult(len(chunk), indexes, err), true
		}
		if !waitCtx(ctx, time.Duration(attempt+1)*20*time.Millisecond) {
			return fatalResult(len(chunk), indexes, ctx.Err()), true
		}
		return endpointChunkResult{}, false
	default:
		return transientResult(len(chunk), indexes, err), true
	}
}

func (s *mysql) fallbackPerRow(
	ctx context.Context,
	topic string,
	db *gorm.DB,
	chunk []*hamodel.DbhaDataStatus,
	indexes []int,
) endpointChunkResult {
	if err := apm.MySqlBatchFallbackTotal.IncWithLabels(map[string]string{
		apm.MetricLabelMysql: topic,
	}); err != nil {
		logger.Warn("update mysql batch fallback metric failed, errmsg: %s", err)
	}
	res := blankResult(len(chunk), indexes)
	for _, idx := range indexes {
		if err := ctx.Err(); err != nil {
			res.fatal = true
			res.err = err
			return res
		}
		err := s.writer.write(ctx, db, []*hamodel.DbhaDataStatus{chunk[idx]})
		if err == nil {
			res.rowOK[idx] = true
			res.rowOKAt[idx] = s.currentTime()
			continue
		}
		if ctx.Err() != nil {
			res.fatal = true
			res.err = ctx.Err()
			return res
		}
		s.incWriteErrors(topic, 1)
		kind := classifyMySQLError(err)
		if kind == mysqlErrFatal {
			res.fatal = true
			res.err = err
			return res
		}
		if kind == mysqlErrData {
			res.rowPermanent[idx] = true
			continue
		}
		res.err = err
	}
	return res
}

func (s *mysql) incWriteErrors(topic string, n int) {
	if n <= 0 {
		return
	}
	if err := apm.MySqlWriteErrorsTotal.AddWithLabels(map[string]string{
		apm.MetricLabelMysql: topic,
	}, float64(n)); err != nil {
		logger.Warn("update mysql write errors metric failed, errmsg: %s", err)
	}
}

func (s *mysql) flushBatchDurations(topic string, elapsed []int64, ran []bool) {
	for i := range ran {
		if !ran[i] {
			continue
		}
		s.observeBatchDuration(topic, float64(atomic.LoadInt64(&elapsed[i])))
	}
}

func (s *mysql) observeBatchDuration(topic string, ms float64) {
	if s.recordDuration != nil {
		s.recordDuration(topic, ms)
		return
	}
	if err := apm.MySqlBatchWriteDurationMs.ObserveWithLabels(map[string]string{
		apm.MetricLabelMysql: topic,
	}, ms); err != nil {
		logger.Warn("update mysql batch write duration metric failed, errmsg: %s", err)
	}
}

func updateRowOutcomes(
	results [][]endpointChunkResult,
	rowOK [][]bool,
	rowNeed [][][]bool,
	rowAt [][]time.Time,
) {
	for c := range rowOK {
		for j := range rowOK[c] {
			if rowOK[c][j] {
				continue
			}
			ok, at := firstSuccess(results, c, j)
			if !ok {
				continue
			}
			rowOK[c][j] = true
			if !at.IsZero() {
				rowAt[c][j] = at
			}
		}
		applyRowNeed(results, rowOK[c], rowNeed, c)
	}
}

func firstSuccess(results [][]endpointChunkResult, c, j int) (bool, time.Time) {
	var earliest time.Time
	saw := false
	for i := range results {
		r := results[i][c]
		if r.rowOK == nil || j >= len(r.rowOK) || !r.rowOK[j] {
			continue
		}
		saw = true
		if r.rowOKAt == nil || j >= len(r.rowOKAt) || r.rowOKAt[j].IsZero() {
			continue
		}
		at := r.rowOKAt[j]
		if earliest.IsZero() || at.Before(earliest) {
			earliest = at
		}
	}
	return saw, earliest
}

func applyRowNeed(results [][]endpointChunkResult, rowOK []bool, rowNeed [][][]bool, c int) {
	for j := range rowOK {
		if rowOK[j] {
			for i := range results {
				rowNeed[i][c][j] = false
			}
			continue
		}
		for i := range results {
			r := results[i][c]
			if r.attempted == nil || !r.attempted[j] {
				continue
			}
			if r.fatal || (r.rowPermanent != nil && r.rowPermanent[j]) {
				rowNeed[i][c][j] = false
			}
		}
	}
}

func pendingChunkCount(rowNeed [][][]bool) int {
	if len(rowNeed) == 0 {
		return 0
	}
	n := 0
	for c := range rowNeed[0] {
		for i := range rowNeed {
			if anyTrue(rowNeed[i][c]) {
				n++
				break
			}
		}
	}
	return n
}

func countFailedRows(rowOK [][]bool) int {
	failed := 0
	for _, rows := range rowOK {
		for _, ok := range rows {
			if !ok {
				failed++
			}
		}
	}
	return failed
}

func maskedIndexes(mask []bool) []int {
	indexes := make([]int, 0, len(mask))
	for i, on := range mask {
		if on {
			indexes = append(indexes, i)
		}
	}
	return indexes
}

func pickRows(chunk []*hamodel.DbhaDataStatus, indexes []int) []*hamodel.DbhaDataStatus {
	rows := make([]*hamodel.DbhaDataStatus, 0, len(indexes))
	for _, idx := range indexes {
		rows = append(rows, chunk[idx])
	}
	return rows
}

func anyTrue(flags []bool) bool {
	for _, on := range flags {
		if on {
			return true
		}
	}
	return false
}

func blankResult(n int, indexes []int) endpointChunkResult {
	res := endpointChunkResult{
		attempted:    make([]bool, n),
		rowOK:        make([]bool, n),
		rowOKAt:      make([]time.Time, n),
		rowPermanent: make([]bool, n),
	}
	for _, idx := range indexes {
		res.attempted[idx] = true
	}
	return res
}

func successResult(n int, indexes []int, at time.Time) endpointChunkResult {
	res := blankResult(n, indexes)
	for _, idx := range indexes {
		res.rowOK[idx] = true
		res.rowOKAt[idx] = at
	}
	return res
}

func fatalResult(n int, indexes []int, err error) endpointChunkResult {
	res := blankResult(n, indexes)
	res.fatal = true
	res.err = err
	return res
}

func transientResult(n int, indexes []int, err error) endpointChunkResult {
	res := blankResult(n, indexes)
	res.err = err
	return res
}

func waitCtx(ctx context.Context, d time.Duration) bool {
	if d <= 0 {
		return ctx.Err() == nil
	}
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-timer.C:
		return true
	}
}

func newChunkOutcome(rowOK [][]bool, rowAt [][]time.Time, perm [][][]bool, exit string) chunkWriteOutcome {
	return chunkWriteOutcome{
		failed: countFailedRows(rowOK),
		exit:   exit,
		rowOK:  rowOK,
		rowAt:  rowAt,
		perm:   perm,
	}
}

func exitFromFatal(err error) string {
	if err == context.Canceled || err == context.DeadlineExceeded {
		return ReasonCtxDone
	}
	return ReasonFatal
}

func growBackoff(backoff time.Duration) time.Duration {
	if backoff < retryBackoffMax {
		backoff *= 2
		if backoff > retryBackoffMax {
			return retryBackoffMax
		}
	}
	return backoff
}

func newRowTimes(chunks [][]*hamodel.DbhaDataStatus) [][]time.Time {
	rowAt := make([][]time.Time, len(chunks))
	for c, chunk := range chunks {
		rowAt[c] = make([]time.Time, len(chunk))
	}
	return rowAt
}

func newPermState(nEp int, chunks [][]*hamodel.DbhaDataStatus) [][][]bool {
	perm := make([][][]bool, nEp)
	for i := range perm {
		perm[i] = make([][]bool, len(chunks))
		for c, chunk := range chunks {
			perm[i][c] = make([]bool, len(chunk))
		}
	}
	return perm
}

func accumulatePermanent(results [][]endpointChunkResult, perm [][][]bool) {
	for i := range results {
		for c := range results[i] {
			r := results[i][c]
			if r.rowPermanent == nil {
				continue
			}
			for j, on := range r.rowPermanent {
				if on {
					perm[i][c][j] = true
				}
			}
		}
	}
}

func applyWriteStats(
	result *BatchResult,
	rows []preparedRow,
	chunks [][]*hamodel.DbhaDataStatus,
	outcome chunkWriteOutcome,
) {
	idx := 0
	for c, chunk := range chunks {
		for j := range chunk {
			if idx >= len(rows) {
				return
			}
			noteRowStat(&result.Stats, rows[idx], outcome, c, j)
			idx++
		}
	}
}

func noteRowStat(stats *WriteStats, row preparedRow, outcome chunkWriteOutcome, c, j int) {
	dbType := string(row.data.DbTypeName)
	if outcome.rowOK[c][j] {
		stats.Written++
		if ms, ok := DelayMillis(outcome.rowAt[c][j], row.data.ReportTimestamp); ok {
			stats.Samples = append(stats.Samples, DelaySample{DbType: dbType, Ms: ms})
		}
		return
	}
	stats.AddDrop(dbType, rowFailReason(outcome, c, j), 1)
}

func rowFailReason(outcome chunkWriteOutcome, c, j int) string {
	if allEndpointsPermanent(outcome.perm, c, j) || outcome.exit == "" {
		return ReasonDataError
	}
	return outcome.exit
}

func allEndpointsPermanent(perm [][][]bool, c, j int) bool {
	if len(perm) == 0 {
		return false
	}
	for i := range perm {
		if c >= len(perm[i]) || j >= len(perm[i][c]) || !perm[i][c][j] {
			return false
		}
	}
	return true
}

func sampleMillis(results [][]endpointChunkResult, c, j int, reportTs uint64) (float64, bool) {
	saw, at := firstSuccess(results, c, j)
	if !saw {
		return 0, false
	}
	return DelayMillis(at, reportTs)
}

// ensure mysql implements BatchSinker
var _ BatchSinker = (*mysql)(nil)
