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
	"net/http"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
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

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, _ := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
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
			{
				BkBizID:     100,
				BkCloudID:   1,
				ClusterID:   10,
				ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
				MachineType: haprobe.DbmMetadataMachineTypeProxy,
			},
			{
				BkBizID:      100,
				BkCloudID:    1,
				ClusterID:    10,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
				MachineType:  haprobe.DbmMetadataMachineTypeBackend,
				InstanceRole: haprobe.MySQLStorageMaster,
			},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, _ := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
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

	matched, _ := executor.MatchStrategyForGroup(context.Background(), group)
	if matched {
		t.Error("expected matched=false when event name does not match")
	}
}

func setupDbmMetadataAPIForSwitchFlowTest(t *testing.T, serverURL string) {
	t.Helper()
	old := config.Cfg.Workflow.DbmApiMetadata
	config.Cfg.Workflow.DbmApiMetadata.Api = serverURL
	config.Cfg.Workflow.DbmApiMetadata.Token = "test-token"
	config.Cfg.Workflow.DbmApiMetadata.Timeout = time.Second
	t.Cleanup(func() {
		config.Cfg.Workflow.DbmApiMetadata = old
	})
}

func newSwitchExecutorForCreateRequestTests(t *testing.T) *SwitchExecutor {
	t.Helper()
	td := testutil.NewTestDbhaData(t)
	return &SwitchExecutor{
		hadata: td.DbhaData,
		dbmSync: &Synchronizer{
			cli: &dbm.Client{},
		},
	}
}

func TestCreateRequestWithGroup_EmptyIPs(t *testing.T) {
	executor := newSwitchExecutorForCreateRequestTests(t)
	group := &FailureGroup{BkCloudID: 1, DbType: haprobe.DbTypeMySql}

	req := executor.CreateRequestWithGroup(context.Background(), group)
	if req != nil {
		t.Fatal("expected nil request for empty ips")
	}
}

func TestCreateRequestWithGroup_DbmErrNoResponse(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, nil)
	setupDbmMetadataAPIForSwitchFlowTest(t, server.URL)

	executor := newSwitchExecutorForCreateRequestTests(t)
	group := &FailureGroup{
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Instances: []FailureInstanceInfo{
			{IP: "127.0.0.1", DbType: haprobe.DbTypeMySql},
		},
	}

	req := executor.CreateRequestWithGroup(context.Background(), group)
	if req != nil {
		t.Fatal("expected nil request when dbm returns no response")
	}
}

func TestCreateRequestWithGroup_DbmGeneralError(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusInternalServerError, nil)
	setupDbmMetadataAPIForSwitchFlowTest(t, server.URL)

	executor := newSwitchExecutorForCreateRequestTests(t)
	group := &FailureGroup{
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Instances: []FailureInstanceInfo{
			{IP: "127.0.0.2", DbType: haprobe.DbTypeMySql},
		},
	}

	req := executor.CreateRequestWithGroup(context.Background(), group)
	if req != nil {
		t.Fatal("expected nil request when dbm responds with http error")
	}
}

func TestCreateRequestWithGroup_FilterUnavailableAndKeepAvailable(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, []*dbm.DbInstMetadata{
		{BkCloudID: 1, IP: "127.0.0.3", Port: 3306, Status: dbm.Unavailable},
		{BkCloudID: 1, IP: "127.0.0.4", Port: 3307, Status: dbm.Available},
	})
	setupDbmMetadataAPIForSwitchFlowTest(t, server.URL)

	executor := newSwitchExecutorForCreateRequestTests(t)
	group := &FailureGroup{
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Instances: []FailureInstanceInfo{
			{IP: "127.0.0.3", DbType: haprobe.DbTypeMySql},
			{IP: "127.0.0.4", DbType: haprobe.DbTypeMySql},
		},
	}

	req := executor.CreateRequestWithGroup(context.Background(), group)
	if req == nil {
		t.Fatal("expected non-nil request")
	}
	if !req.HasDbInstMetadata() {
		t.Fatal("expected request has metadata after filtering")
	}

	metas := req.GetDbInstMetadata()
	if len(metas) != 1 {
		t.Fatalf("expected 1 available metadata, got %d", len(metas))
	}
	if metas[0].IP != "127.0.0.4" {
		t.Fatalf("expected only available ip=127.0.0.4, got %s", metas[0].IP)
	}
}

func TestMatchStrategyForGroup_TriggerCountNegativeDefaultsToOne(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "neg-count",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     -3,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure}},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
	if !matched {
		t.Fatal("expected matched when triggerCount is negative and defaults to 1")
	}
	if strategy == nil || strategy.Name != "neg-count" {
		t.Fatalf("expected strategy neg-count, got %+v", strategy)
	}
}

func TestMatchStrategyForGroup_DisabledStrategyIgnored(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "disabled-strategy",
			BkBizID:          100,
			Status:           hamodel.StatusTypeDisabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure}},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
	if matched {
		t.Fatal("expected not matched when only disabled strategy exists")
	}
	if strategy != nil {
		t.Fatalf("expected nil strategy, got %+v", strategy)
	}
}

func TestMatchStrategyForGroup_NormalAndSpecialBothMatchedChooseHigherPriority(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "normal-p2",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         2,
		},
		&hamodel.DbSwitchingStrategy{
			Name:             "special-p1",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     1,
			Priority:         1,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 100, EventName: haprobe.DbEventNameDetectFailure},
			{
				BkBizID:      100,
				BkCloudID:    1,
				ClusterID:    10,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
				MachineType:  haprobe.DbmMetadataMachineTypeProxy,
				EventName:    haprobe.DbEventNameDetectFailure,
				InstanceRole: "",
			},
			{
				BkBizID:      100,
				BkCloudID:    1,
				ClusterID:    10,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
				MachineType:  haprobe.DbmMetadataMachineTypeBackend,
				InstanceRole: haprobe.MySQLStorageMaster,
				EventName:    haprobe.DbEventNameDetectFailure,
			},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
	if !matched {
		t.Fatal("expected matched=true when normal and special strategies both match")
	}
	if strategy == nil {
		t.Fatal("expected non-nil strategy")
	}
	if strategy.Name != "special-p1" {
		t.Fatalf("expected special-p1 due to higher priority, got %s", strategy.Name)
	}
}

func TestMatchStrategyForGroup_DbEventNameDoubleCheckSshFailureV1(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// insert strategy
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{ // target strategy
			Name:             "target-ssh-failure",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDoubleCheckSshFailureV1,
			TriggerCount:     3,
			Priority:         2,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // global strategy
			Name:             "global-ssh-failure",
			BkBizID:          0, // bizID=0
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDoubleCheckSshFailureV1,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // different event name
			Name:             "interference-diff-event",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameProbeOffline,
			TriggerCount:     3,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // different bizID
			Name:             "interference-diff-biz",
			BkBizID:          99,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDoubleCheckSshFailureV1,
			TriggerCount:     3,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // disabled strategy
			Name:             "interference-disabled",
			BkBizID:          21,
			Status:           hamodel.StatusTypeDisabled,
			TriggerEventName: haprobe.DbEventNameDoubleCheckSshFailureV1,
			TriggerCount:     3,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // deleted strategy
			Name:             "interference-deleted",
			BkBizID:          21,
			Status:           hamodel.StatusTypeDeleted,
			TriggerEventName: haprobe.DbEventNameDoubleCheckSshFailureV1,
			TriggerCount:     3,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // lower priority
			Name:             "interference-lower-priority",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDoubleCheckSshFailureV1,
			TriggerCount:     1,
			Priority:         5,
			Action:           hamodel.ActionTypeSwitch,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{BkBizID: 21, EventName: haprobe.DbEventNameDoubleCheckSshFailureV1},
			{BkBizID: 21, EventName: haprobe.DbEventNameDoubleCheckSshFailureV1},
			{BkBizID: 21, EventName: haprobe.DbEventNameDoubleCheckSshFailureV1},
			{BkBizID: 21, EventName: haprobe.DbEventNameDoubleCheckSshFailureV1},
			{BkBizID: 21, EventName: haprobe.DbEventNameTendbhaProxyBackendFailure},
			{BkBizID: 21, EventName: haprobe.DbEventNameTendbhaProxyBackendFailure},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
	if !matched {
		t.Fatal("expected matched=true")
	}
	if strategy == nil {
		t.Fatal("expected non-nil strategy")
	}
	if strategy.Name != "target-ssh-failure" {
		t.Errorf("expected strategy name 'target-ssh-failure', got %q", strategy.Name)
	}
}

func TestMatchStrategyForGroup_DbEventNameTendbhaProxyBackendFailure(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// insert strategy
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{ // target strategy
			Name:             "target-tendbha-proxy-backend-failure",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         2,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // global strategy
			Name:             "global-tendbha-proxy-backend-failure",
			BkBizID:          0, // bizID=0
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // different event name
			Name:             "interference-diff-event",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameProbeOffline,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // different bizID
			Name:             "interference-diff-biz",
			BkBizID:          99,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // disabled strategy
			Name:             "interference-disabled",
			BkBizID:          21,
			Status:           hamodel.StatusTypeDisabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // deleted strategy
			Name:             "interference-deleted",
			BkBizID:          21,
			Status:           hamodel.StatusTypeDeleted,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // lower priority
			Name:             "interference-lower-priority",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         5,
			Action:           hamodel.ActionTypeSwitch,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{
				BkBizID:     21,
				BkCloudID:   1,
				ClusterID:   10,
				EventName:   haprobe.DbEventNameTendbhaProxyBackendFailure,
				ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
				MachineType: haprobe.DbmMetadataMachineTypeProxy,
			},
			{
				BkBizID:      21,
				BkCloudID:    1,
				ClusterID:    10,
				EventName:    haprobe.DbEventNameTendbhaProxyBackendFailure,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
				MachineType:  haprobe.DbmMetadataMachineTypeBackend,
				InstanceRole: haprobe.MySQLStorageMaster,
			},
			{
				BkBizID:     21,
				BkCloudID:   2,
				ClusterID:   11,
				EventName:   haprobe.DbEventNameTendbhaProxyBackendFailure,
				ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
				MachineType: haprobe.DbmMetadataMachineTypeProxy,
			},
			{
				BkBizID:      21,
				BkCloudID:    2,
				ClusterID:    11,
				EventName:    haprobe.DbEventNameTendbhaProxyBackendFailure,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
				MachineType:  haprobe.DbmMetadataMachineTypeBackend,
				InstanceRole: haprobe.MySQLStorageMaster,
			},
			{
				BkBizID:     21,
				BkCloudID:   3,
				ClusterID:   12,
				EventName:   haprobe.DbEventNameTendbhaProxyBackendFailure,
				ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
				MachineType: haprobe.DbmMetadataMachineTypeProxy,
			},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
	if !matched {
		t.Fatal("expected matched=true")
	}
	if strategy == nil {
		t.Fatal("expected non-nil strategy")
	}
	if strategy.Name != "target-tendbha-proxy-backend-failure" {
		t.Errorf("expected strategy name 'target-tendbha-proxy-backend-failure', got %q", strategy.Name)
	}
}

func TestMatchStrategyForGroup_DbEventNameTendbclusterSpiderRemoteFailure(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	// insert strategy
	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{ // target strategy
			Name:             "target-tendbha-spider-remote-failure",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
			TriggerCount:     2,
			Priority:         2,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // global strategy
			Name:             "global-tendbha-spider-remote-failure",
			BkBizID:          0, // bizID=0
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // different event name
			Name:             "interference-diff-event",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameProbeOffline,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // different bizID
			Name:             "interference-diff-biz",
			BkBizID:          99,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // disabled strategy
			Name:             "interference-disabled",
			BkBizID:          21,
			Status:           hamodel.StatusTypeDisabled,
			TriggerEventName: haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // deleted strategy
			Name:             "interference-deleted",
			BkBizID:          21,
			Status:           hamodel.StatusTypeDeleted,
			TriggerEventName: haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
			TriggerCount:     2,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{ // lower priority
			Name:             "interference-lower-priority",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
			TriggerCount:     2,
			Priority:         5,
			Action:           hamodel.ActionTypeSwitch,
		},
	)

	group := &FailureGroup{
		Instances: []FailureInstanceInfo{
			{
				BkBizID:     21,
				BkCloudID:   1,
				ClusterID:   10,
				EventName:   haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
				ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
				MachineType: haprobe.DbmMetadataMachineTypeSpider,
			},
			{
				BkBizID:      21,
				BkCloudID:    1,
				ClusterID:    10,
				EventName:    haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbCluster,
				MachineType:  haprobe.DbmMetadataMachineTypeRemote,
				InstanceRole: haprobe.TenDBClusterStorageMaster,
			},
			{
				BkBizID:     21,
				BkCloudID:   2,
				ClusterID:   11,
				EventName:   haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
				ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
				MachineType: haprobe.DbmMetadataMachineTypeSpider,
			},
			{
				BkBizID:      21,
				BkCloudID:    2,
				ClusterID:    11,
				EventName:    haprobe.DbEventNameTendbclusterSpiderRemoteFailure,
				ClusterType:  haprobe.DbmMetadataClusterTypeTendbCluster,
				MachineType:  haprobe.DbmMetadataMachineTypeRemote,
				InstanceRole: haprobe.TenDBClusterStorageMaster,
			},
		},
	}

	matched, strategy := executor.MatchStrategyForGroup(context.Background(), group)
	if !matched {
		t.Fatal("expected matched=true")
	}
	if strategy == nil {
		t.Fatal("expected non-nil strategy")
	}
	if strategy.Name != "target-tendbha-spider-remote-failure" {
		t.Errorf("expected strategy name 'target-tendbha-spider-remote-failure', got %q", strategy.Name)
	}
}
