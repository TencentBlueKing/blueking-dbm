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
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/testutil"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

func setupStorageTimeoutForTest(t *testing.T) {
	t.Helper()
	old := config.Cfg.Storage.Timeout
	config.Cfg.Storage.Timeout = time.Second
	t.Cleanup(func() {
		config.Cfg.Storage.Timeout = old
	})
}

// withinSnapshotTestTime tolerates the timestamp precision of the SQLite driver.
func withinSnapshotTestTime(got, want time.Time) bool {
	delta := got.Sub(want)
	return delta > -time.Second && delta < time.Second
}

type snapshotLogFixture struct {
	SwitchID  string
	Action    hamodel.SnapshotActionType
	Status    hamodel.DbSwitchingSnapshotLogStatus
	DbType    string
	EventName string
	Port      int
	StartTime *time.Time
}

func (f snapshotLogFixture) toRecord() *hamodel.DbSwitchingSnapshotLog {
	finished := time.Now()
	if f.StartTime != nil {
		finished = f.StartTime.Add(time.Second)
	}
	return &hamodel.DbSwitchingSnapshotLog{
		SwitchID:     f.SwitchID,
		DbType:       f.DbType,
		Action:       f.Action,
		Status:       f.Status,
		BkBizID:      testBkBizID,
		BkCloudID:    testBkCloudID,
		StartTime:    f.StartTime,
		FinishedTime: &finished,
		Instances: hamodel.JSON[[]*hamodel.SwitchingSnapshotInstance]{
			Valid: true,
			Data: []*hamodel.SwitchingSnapshotInstance{
				{IP: testIP, Port: f.Port, EventName: f.EventName},
			},
		},
	}
}

func writeSnapshotLog(t *testing.T, td *testutil.TestDbhaData, f snapshotLogFixture) {
	t.Helper()
	if err := td.GormDB.Create(f.toRecord()).Error; err != nil {
		t.Fatalf("failed to insert snapshot log %s: %v", f.SwitchID, err)
	}
}

func newSnapshotQueryWorkflow(t *testing.T) (*Workflow, *testutil.TestDbhaData) {
	t.Helper()
	td := testutil.NewTestDbhaData(t)
	return &Workflow{hadata: td.DbhaData}, td
}

func newSnapshotQueryGroup() *FailureGroup {
	return &FailureGroup{
		BkBizID:   testBkBizID,
		BkCloudID: testBkCloudID,
		DbType:    testMysqlDbType,
	}
}

func skippedSwitchFixture(switchID, event string, start time.Time) snapshotLogFixture {
	return snapshotLogFixture{
		SwitchID:  switchID,
		Action:    hamodel.SnapshotActionTypePreSwitch,
		Status:    hamodel.DbSwitchingSnapshotLogStatusFailed,
		DbType:    string(testMysqlDbType),
		EventName: event,
		Port:      testPort,
		StartTime: &start,
	}
}

func TestReadReportedInstancesByKind(t *testing.T) {
	setupStorageTimeoutForTest(t)
	w, td := newSnapshotQueryWorkflow(t)
	now := time.Now()
	writeSnapshotLog(t, td, skippedSwitchFixture("skip-1", string(testEventA), now))
	notify := skippedSwitchFixture("notify-1", string(testEventB), now)
	notify.Action = hamodel.SnapshotActionTypeNotify
	notify.Status = hamodel.DbSwitchingSnapshotLogStatusSuccess
	writeSnapshotLog(t, td, notify)

	group := newSnapshotQueryGroup()
	key := reportedTestKey(testPort, testMysqlDbType)

	skipped := w.readReportedInstancesFromSnapshotLogs(
		context.Background(), group, reportLogSkippedSwitch)
	if len(skipped) != 1 || skipped[key].EventName != testEventA {
		t.Fatalf("skipped-switch query returned %+v", skipped)
	}
	if !withinSnapshotTestTime(skipped[key].StartTime, now) || skipped[key].TTL <= 0 {
		t.Fatalf("snapshot window was not carried: %+v", skipped[key])
	}

	notified := w.readReportedInstancesFromSnapshotLogs(
		context.Background(), group, reportLogNotifyOnly)
	if len(notified) != 1 || notified[key].EventName != testEventB {
		t.Fatalf("notify-only query returned %+v", notified)
	}
}

func TestReadReportedInstancesKeepsNewestRecord(t *testing.T) {
	setupStorageTimeoutForTest(t)
	w, td := newSnapshotQueryWorkflow(t)
	older := time.Now().Add(-5 * time.Minute)
	newer := time.Now().Add(-time.Minute)
	writeSnapshotLog(t, td, skippedSwitchFixture("older", string(testEventA), older))
	writeSnapshotLog(t, td, skippedSwitchFixture("newer", string(testEventB), newer))

	group := newSnapshotQueryGroup()
	got := w.readReportedInstancesFromSnapshotLogs(
		context.Background(), group, reportLogSkippedSwitch)
	key := reportedTestKey(testPort, testMysqlDbType)
	if len(got) != 1 {
		t.Fatalf("expected 1 key, got %d: %+v", len(got), got)
	}
	if got[key].EventName != testEventB || !withinSnapshotTestTime(got[key].StartTime, newer) {
		t.Fatalf("newest record must win: %+v", got[key])
	}
}

func TestReadReportedInstancesSeparatesDbType(t *testing.T) {
	setupStorageTimeoutForTest(t)
	w, td := newSnapshotQueryWorkflow(t)
	now := time.Now()
	writeSnapshotLog(t, td, skippedSwitchFixture("snap-mysql", string(testEventA), now))
	redis := skippedSwitchFixture("snap-redis", string(testEventA), now)
	redis.DbType = string(testRedisDbType)
	writeSnapshotLog(t, td, redis)

	group := newSnapshotQueryGroup()
	got := w.readReportedInstancesFromSnapshotLogs(
		context.Background(), group, reportLogSkippedSwitch)
	if len(got) != 2 {
		t.Fatalf("different dbType records must produce separate keys, got %d: %+v", len(got), got)
	}
	for _, key := range []string{
		reportedTestKey(testPort, testMysqlDbType),
		reportedTestKey(testPort, testRedisDbType),
	} {
		if _, ok := got[key]; !ok {
			t.Fatalf("missing key %s in %+v", key, got)
		}
	}
}

func TestReadReportedInstancesIgnoresNullStartTime(t *testing.T) {
	setupStorageTimeoutForTest(t)
	w, td := newSnapshotQueryWorkflow(t)
	now := time.Now()
	nullStart := skippedSwitchFixture("null-start", string(testEventA), now)
	nullStart.StartTime = nil
	writeSnapshotLog(t, td, nullStart)

	// Gorm's autoCreateTime fills the column on insert; force it back to NULL so the
	// query's start_time condition is exercised. The reader's nil guard is defensive:
	// the SQL condition already filters NULL rows out.
	if err := td.GormDB.Model(&hamodel.DbSwitchingSnapshotLog{}).
		Where("switch_id = ?", "null-start").
		UpdateColumn("start_time", nil).Error; err != nil {
		t.Fatalf("failed to clear start_time: %v", err)
	}

	group := newSnapshotQueryGroup()
	got := w.readReportedInstancesFromSnapshotLogs(
		context.Background(), group, reportLogSkippedSwitch)
	if len(got) != 0 {
		t.Fatalf("a record without start_time must not be reported: %+v", got)
	}
}

func TestReadReportedInstancesFailOpenOnCancelledContext(t *testing.T) {
	setupStorageTimeoutForTest(t)
	w, td := newSnapshotQueryWorkflow(t)
	writeSnapshotLog(t, td, skippedSwitchFixture("cancel", string(testEventA), time.Now()))

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	got := w.readReportedInstancesFromSnapshotLogs(ctx, newSnapshotQueryGroup(), reportLogSkippedSwitch)
	if len(got) != 0 {
		t.Fatalf("a failed query must fail-open with an empty result, got %+v", got)
	}
}
