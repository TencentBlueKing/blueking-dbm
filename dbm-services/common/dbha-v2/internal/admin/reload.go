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

package admin

import (
	"context"
	"reflect"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/apm"
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/slot"
	"dbm-services/common/dbha-v2/pkg/dbcred"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
)

var (
	reloadTotalTimeout = 30 * time.Second
	reloadSlotTimeout  = 8 * time.Second
)

type reloadOutcome struct {
	failed       bool
	slotSuccess  int
	slotFailure  int
	successNames []string
	failureNames []string
}

type slotSkipReason string

func (r slotSkipReason) String() string { return string(r) }

const (
	slotSkipReasonShutdown        slotSkipReason = "shutdown"
	slotSkipReasonBudgetExhausted slotSkipReason = "total budget exhausted"
	slotSkipReasonSkipped         slotSkipReason = "skipped"
)

type logFileFP struct {
	Path      string
	FileCount int
	FileSize  int
}

// lastReloadOutcome is the most recent reloadOnce result; tests assert it instead of scraping gauges.
var lastReloadOutcome reloadOutcome

func (s *Service) requestReload() {
	if s.reloadC == nil {
		return
	}

	select {
	case s.reloadC <- struct{}{}:
	default:
		logger.Info("reload already queued, coalesce request")
	}
}

func (s *Service) runReloadWorker() {
	defer close(s.reloadWorkerDone)

	for {
		select {
		case <-s.shutdown:
			return

		case <-s.reloadC:
			safe.Run(func() {
				s.reloadOnce()
			})
		}
	}
}

// reloadOnce parses, validates, and applies config while rebuilding affected resource slots.
func (s *Service) reloadOnce() {
	started := time.Now()
	outcome := reloadOutcome{}
	defer func() {
		lastReloadOutcome = outcome
		reportReloadMetrics(started, outcome)
	}()

	select {
	case <-s.shutdown:
		outcome.failed = true
		return

	default:
	}

	next, err := config.Parse(s.configPath)
	if err != nil {
		outcome.failed = true
		logger.Warn("parse admin config failed, config_path: %s, errmsg: %s", s.configPath, err)
		return
	}

	if err := config.Validate(next); err != nil {
		outcome.failed = true
		logger.Warn("validate admin config failed, config_path: %s, errmsg: %s", s.configPath, err)
		return
	}

	current := config.Snapshot()
	next = config.RetainIdentity(current, next)

	if reflect.DeepEqual(current, next) && !anySlotNeedsRebuild(s.slots, next) {
		logger.Info("admin config unchanged, skip reload, config_path: %s", s.configPath)
		return
	}

	s.rebuildAffectedSlots(next, &outcome)

	warnRestartRequiredLogFiles(current, next)
	config.Apply(next)

	// Push DbmApis into credential resolvers after Apply so LookupDbmApi sees
	// the new snapshot. ConfigureAll is "Warn continue": never touch outcome.
	if !config.DbmApisEqual(current.DbmApis, next.DbmApis) {
		dbcred.ConfigureAll(config.LookupDbmApi)
	}

	if s.runtimeLogger != nil {
		s.runtimeLogger.SetLevel(logger.Level(next.Log.Level))
	}

	if outcome.failed {
		logger.Warn(
			"admin config snapshot reloaded with resource failures, config_path: %s, "+
				"slot_success: %s, slot_failure: %s",
			s.configPath,
			joinSlotNames(outcome.successNames),
			joinSlotNames(outcome.failureNames),
		)
		return
	}

	logger.Info(
		"admin config snapshot reloaded, config_path: %s, slot_success: %s, slot_failure: %s",
		s.configPath,
		joinSlotNames(outcome.successNames),
		joinSlotNames(outcome.failureNames),
	)
}

func (s *Service) rebuildAffectedSlots(next config.Configuration, outcome *reloadOutcome) {
	totalCtx, cancel := context.WithTimeout(context.Background(), reloadTotalTimeout)
	defer cancel()

	for index, resourceSlot := range s.slots {
		shuttingDown := s.isShuttingDown()
		budgetErr := totalCtx.Err()

		if shuttingDown || budgetErr != nil {
			outcome.failed = true
			skipRemainingSlots(s.slots[index:], next, outcome, skipReason(shuttingDown, budgetErr))
			return
		}

		if !resourceSlot.NeedsRebuild(next) {
			continue
		}

		slotCtx, slotCancel := context.WithTimeout(context.Background(), reloadSlotTimeout)
		err := resourceSlot.Rebuild(slotCtx, next)
		slotCancel()

		if err != nil {
			outcome.failed = true
			outcome.slotFailure++
			outcome.failureNames = append(outcome.failureNames, resourceSlot.Name())
			logger.Warn("admin resource reload failed, slot: %s, errmsg: %s", resourceSlot.Name(), err)
			continue
		}

		outcome.slotSuccess++
		outcome.successNames = append(outcome.successNames, resourceSlot.Name())
	}
}

func anySlotNeedsRebuild(slots []slot.Ops, next config.Configuration) bool {
	for _, resourceSlot := range slots {
		if resourceSlot.NeedsRebuild(next) {
			return true
		}
	}
	return false
}

func skipReason(shuttingDown bool, totalErr error) slotSkipReason {
	if shuttingDown {
		return slotSkipReasonShutdown
	}

	if totalErr != nil {
		return slotSkipReasonBudgetExhausted
	}

	return slotSkipReasonSkipped
}

func skipRemainingSlots(slots []slot.Ops, next config.Configuration, outcome *reloadOutcome, reason slotSkipReason) {
	for _, resourceSlot := range slots {
		if !resourceSlot.NeedsRebuild(next) {
			continue
		}

		outcome.slotFailure++
		outcome.failureNames = append(outcome.failureNames, resourceSlot.Name())
		logger.Warn("admin resource reload skipped, slot: %s, reason: %s", resourceSlot.Name(), reason)
	}
}

func joinSlotNames(names []string) string {
	if len(names) == 0 {
		return "-"
	}
	return strings.Join(names, ",")
}

func warnRestartRequiredLogFiles(oldCfg, next config.Configuration) {
	oldFP := logFileFP{Path: oldCfg.Log.Path, FileCount: oldCfg.Log.FileCount, FileSize: oldCfg.Log.FileSize}
	nextFP := logFileFP{Path: next.Log.Path, FileCount: next.Log.FileCount, FileSize: next.Log.FileSize}

	if !reflect.DeepEqual(oldFP, nextFP) {
		logger.Warn("config block changed, restart required, block: log.file")
	}
}

func reportReloadMetrics(started time.Time, outcome reloadOutcome) {
	success := 1.0
	failure := 0.0

	if outcome.failed {
		success = 0
		failure = 1
	}

	_ = apm.ConfigReloadSuccess.Set(success)
	_ = apm.ConfigReloadFailure.Set(failure)
	_ = apm.ConfigReloadDurationMs.Set(float64(time.Since(started).Milliseconds()))

	_ = apm.ConfigReloadSlotCount.SetWithLabels(
		map[string]string{apm.MetricLabelResult: "success"},
		float64(outcome.slotSuccess),
	)

	_ = apm.ConfigReloadSlotCount.SetWithLabels(
		map[string]string{apm.MetricLabelResult: "failure"},
		float64(outcome.slotFailure),
	)

	if !outcome.failed {
		_ = apm.ConfigReloadLastSuccessUnix.Set(float64(time.Now().Unix()))
	}
}
