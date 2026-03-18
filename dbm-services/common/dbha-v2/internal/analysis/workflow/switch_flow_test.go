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
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/testutil"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// ============================================================
// MatchStrategyForGroup integration tests (SQLite in-memory database)
// ============================================================

// newTestSwitchExecutor creates a SwitchExecutor backed by SQLite in-memory database for testing.
func newTestSwitchExecutor(t *testing.T) (*SwitchExecutor, *testutil.TestDbhaData) {
	t.Helper()
	td := testutil.NewTestDbhaData(t)
	executor := &SwitchExecutor{hadata: td.DbhaData}
	return executor, td
}

func TestMatchStrategyForGroup_EmptyGroup(t *testing.T) {
	executor, _ := newTestSwitchExecutor(t)
	group := &FailureGroup{Instances: nil}

	matched, strategy := executor.MatchStrategyForGroup(group)
	if matched {
		t.Error("expected matched=false for empty group")
	}
	if strategy != nil {
		t.Error("expected strategy=nil for empty group")
	}
}

func TestMatchStrategyForGroup_NoStrategies(t *testing.T) {
	executor, _ := newTestSwitchExecutor(t)
	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(group)
	if matched {
		t.Error("expected matched=false when no strategies exist")
	}
	if strategy != nil {
		t.Error("expected strategy=nil when no strategies exist")
	}
}

func TestMatchStrategyForGroup_NormalStrategyMatched(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// insert strategy: event name matches, triggerCount=2
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "test-normal",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     2,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(group)
	if !matched {
		t.Fatal("expected matched=true")
	}
	if strategy == nil {
		t.Fatal("expected non-nil strategy")
	}
	if strategy.Name != "test-normal" {
		t.Errorf("expected strategy name 'test-normal', got %q", strategy.Name)
	}
}

func TestMatchStrategyForGroup_NormalStrategyBelowThreshold(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "test-threshold",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     2,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
		},
	}

	matched, _ := executor.MatchStrategyForGroup(group)
	if matched {
		t.Error("expected matched=false when count < triggerCount")
	}
}

func TestMatchStrategyForGroup_TriggerCountZeroDefaultsToOne(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// triggerCount=0, should default to 1
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "test-zero-count",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     0,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(group)
	if !matched {
		t.Fatal("expected matched=true when triggerCount<=0 defaults to 1")
	}
	if strategy.Name != "test-zero-count" {
		t.Errorf("expected strategy name 'test-zero-count', got %q", strategy.Name)
	}
}

func TestMatchStrategyForGroup_SpecialStrategyMatched(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "test-special",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, BkCloudID: 1, ClusterID: 10, MachineType: haprobe.DbmMetadataMachineTypeProxy},
			{BkBizID: 100, BkCloudID: 1, ClusterID: 10, MachineType: haprobe.DbmMetadataMachineTypeBackend},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(group)
	if !matched {
		t.Fatal("expected matched=true for special strategy")
	}
	if strategy.Name != "test-special" {
		t.Errorf("expected strategy name 'test-special', got %q", strategy.Name)
	}
}

func TestMatchStrategyForGroup_SpecialStrategyBelowThreshold(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "test-special-nope",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	// same cluster has only proxy, no backend
	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, BkCloudID: 1, ClusterID: 10, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		},
	}

	matched, _ := executor.MatchStrategyForGroup(group)
	if matched {
		t.Error("expected matched=false when special strategy condition not met")
	}
}

func TestMatchStrategyForGroup_BizStrategyPrioritized(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// global strategy: priority=1
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "global-p1",
			BkBizID:          0,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
		},
		// biz-level strategy: priority=3
		&hamodel.DbSwitchingStrategy{
			Name:             "biz-p3",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         3,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(group)
	if !matched {
		t.Fatal("expected matched=true")
	}
	// biz-level strategy should take priority over global strategy
	if strategy.Name != "biz-p3" {
		t.Errorf("expected biz strategy 'biz-p3' to be selected, got %q", strategy.Name)
	}
}

func TestMatchStrategyForGroup_EventNameMismatch(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// strategy event name is ProbeOffline, but instance event name is DetectFailure
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "wrong-event",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameProbeOffline,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
		},
	}

	matched, _ := executor.MatchStrategyForGroup(group)
	if matched {
		t.Error("expected matched=false when event name does not match")
	}
}
