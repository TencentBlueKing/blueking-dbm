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
	"dbm-services/common/dbha-v2/internal/analysis/switcher"

	"dbm-services/common/dbha-v2/internal/analysis/testutil"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func setupMetadataAPIForTest(t *testing.T, serverURL string) {
	t.Helper()
	old := config.Cfg.Workflow.DbmApiMetadata
	config.Cfg.Workflow.DbmApiMetadata.Api = serverURL
	config.Cfg.Workflow.DbmApiMetadata.Token = "test-token"
	config.Cfg.Workflow.DbmApiMetadata.Timeout = time.Second
	t.Cleanup(func() {
		config.Cfg.Workflow.DbmApiMetadata = old
	})
}

func newWorkflowForHandleFailureGroupTests(t *testing.T, dbmClient *dbm.Client) *Workflow {
	t.Helper()
	td := testutil.NewTestDbhaData(t)
	return &Workflow{
		hadata:    td.DbhaData,
		alarm:     NewAlarmNotifier(),
		windowMgr: NewBizWindowManager(10*time.Second, 30*time.Second),
		switchExecutor: &SwitchExecutor{
			hadata: td.DbhaData,
			dbmSync: &Synchronizer{
				cli: dbmClient,
			},
			switchers: nil,
		},
	}
}

func buildSingleFailureGroup() *FailureGroup {
	return &FailureGroup{
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Instances: []FailureInstanceInfo{
			{
				BkCloudID: 1,
				IP:        "127.0.0.10",
				Port:      3306,
				BkBizID:   100,
				DbType:    haprobe.DbTypeMySql,
				EventName: haprobe.DbEventNameDetectFailure,
			},
		},
	}
}

func markGroupInflight(w *Workflow, group *FailureGroup) string {
	inst := group.Instances[0]
	key := instanceWindowKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType)
	w.windowMgr.mu.Lock()
	w.windowMgr.inflight[key] = time.Now()
	w.windowMgr.mu.Unlock()
	return key
}

func inflightExists(w *Workflow, key string) bool {
	w.windowMgr.mu.RLock()
	defer w.windowMgr.mu.RUnlock()
	_, exists := w.windowMgr.inflight[key]
	return exists
}

func TestHandleFailureGroup_RequestNilReleasesInflight(t *testing.T) {
	w := newWorkflowForHandleFailureGroupTests(t, nil)
	group := buildSingleFailureGroup()
	key := markGroupInflight(w, group)

	w.handleFailureGroup(context.Background(), group)

	if inflightExists(w, key) {
		t.Fatal("expected inflight mark released when request is nil")
	}
}

func TestHandleFailureGroup_RequestWithoutMetadataReleasesInflight(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, []*dbm.DbInstMetadata{
		{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, Status: dbm.Unavailable},
	})
	setupMetadataAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	key := markGroupInflight(w, group)

	w.handleFailureGroup(context.Background(), group)

	if inflightExists(w, key) {
		t.Fatal("expected inflight mark released when request has no metadata")
	}
}

func TestHandleFailureGroup_NoMatchedStrategyReleasesInflight(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, []*dbm.DbInstMetadata{
		{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, Status: dbm.Available},
	})
	setupMetadataAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	key := markGroupInflight(w, group)

	w.handleFailureGroup(context.Background(), group)

	if inflightExists(w, key) {
		t.Fatal("expected inflight mark released when strategy not matched")
	}
}

func TestHandleFailureGroup_NotifyStrategyReleasesInflight(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, []*dbm.DbInstMetadata{
		{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, Status: dbm.Available},
	})
	setupMetadataAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	testutil.InsertStrategies(t, w.hadata,
		&hamodel.DbSwitchingStrategy{
			Name:             "notify-strategy",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
			Action:           hamodel.ActionTypeNotify,
			Scope:            hamodel.ActionScopeTypeHost,
		},
	)

	group := buildSingleFailureGroup()
	key := markGroupInflight(w, group)

	w.handleFailureGroup(context.Background(), group)

	if inflightExists(w, key) {
		t.Fatal("expected inflight mark released for notify action")
	}
}

func TestHandleFailureGroup_SwitchStrategyReleasesInflightWithoutSwitcher(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, []*dbm.DbInstMetadata{
		{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, Status: dbm.Available},
	})
	setupMetadataAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})

	testutil.InsertStrategies(t, w.hadata,
		&hamodel.DbSwitchingStrategy{
			Name:             "switch-strategy",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
			Action:           hamodel.ActionTypeSwitch,
			Scope:            hamodel.ActionScopeTypeHost,
		},
	)

	group := buildSingleFailureGroup()
	key := markGroupInflight(w, group)

	w.handleFailureGroup(context.Background(), group)

	if inflightExists(w, key) {
		t.Fatal("expected inflight mark released for switch action")
	}
}

func TestHandleFailureGroup_UnknownActionReleasesInflight(t *testing.T) {
	server := testutil.NewDbmMetadataTestServer(t, http.StatusOK, []*dbm.DbInstMetadata{
		{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, Status: dbm.Available},
	})
	setupMetadataAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	testutil.InsertStrategies(t, w.hadata,
		&hamodel.DbSwitchingStrategy{
			Name:             "unknown-action",
			BkBizID:          100,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameDetectFailure,
			TriggerCount:     1,
			Priority:         1,
			Action:           hamodel.ActionType("unknown"),
			Scope:            hamodel.ActionScopeTypeHost,
		},
	)

	group := buildSingleFailureGroup()
	key := markGroupInflight(w, group)

	w.handleFailureGroup(context.Background(), group)

	if inflightExists(w, key) {
		t.Fatal("expected inflight mark released for unknown action")
	}
}

func TestMarkDoneAllReleasesAllKeys(t *testing.T) {
	w := &Workflow{windowMgr: NewBizWindowManager(10*time.Second, 30*time.Second)}
	keys := []string{"1:127.0.0.11:3306:mysql", "1:127.0.0.12:3306:mysql"}

	w.windowMgr.mu.Lock()
	for _, k := range keys {
		w.windowMgr.inflight[k] = time.Now()
	}
	w.windowMgr.mu.Unlock()

	w.markDoneAll(keys)

	for _, k := range keys {
		if inflightExists(w, k) {
			t.Fatalf("expected key %s released", k)
		}
	}
}

func TestFilterWhitelistedInstances_NoWhitelistRemovesNothing(t *testing.T) {
	w := newWorkflowForHandleFailureGroupTests(t, nil)
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Status: dbm.Available},
		},
	}

	w.filterWhitelistedInstances(context.Background(), group, req)

	if len(req.MySqlInstData) != 1 {
		t.Fatalf("expected 1 instance remaining, got %d", len(req.MySqlInstData))
	}
}

func TestFilterWhitelistedInstances_WhitelistedInstanceRemoved(t *testing.T) {
	w := newWorkflowForHandleFailureGroupTests(t, nil)

	testutil.InsertBlackWhiteList(t, w.hadata,
		&hamodel.DbBlackWhiteList{
			BkBizID:       100,
			BkCloudID:     1,
			ClusterID:     200,
			ClusterName:   "test-cluster",
			SwitchVersion: hamodel.SwitchVersionV2,
			Status:        hamodel.StatusTypeEnabled,
		},
	)

	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "test-cluster", Status: dbm.Available},
		},
	}

	w.filterWhitelistedInstances(context.Background(), group, req)

	if len(req.MySqlInstData) != 0 {
		t.Fatalf("expected 0 instances remaining (whitelisted), got %d", len(req.MySqlInstData))
	}
}

func TestFilterWhitelistedInstances_PartialWhitelisted(t *testing.T) {
	w := newWorkflowForHandleFailureGroupTests(t, nil)

	testutil.InsertBlackWhiteList(t, w.hadata,
		&hamodel.DbBlackWhiteList{
			BkBizID:       100,
			BkCloudID:     1,
			ClusterID:     200,
			ClusterName:   "whitelisted-cluster",
			SwitchVersion: hamodel.SwitchVersionV2,
			Status:        hamodel.StatusTypeEnabled,
		},
	)

	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "whitelisted-cluster", Status: dbm.Available},
			{BkCloudID: 1, IP: "127.0.0.11", Port: 3306, ClusterID: 300, Cluster: "normal-cluster", Status: dbm.Available},
		},
	}

	w.filterWhitelistedInstances(context.Background(), group, req)

	if len(req.MySqlInstData) != 1 {
		t.Fatalf("expected 1 instance remaining, got %d", len(req.MySqlInstData))
	}
	if req.MySqlInstData[0].ClusterID != 300 {
		t.Fatalf("expected remaining instance clusterId=300, got %d", req.MySqlInstData[0].ClusterID)
	}
}

func TestFilterWhitelistedInstances_V1SwitchVersionNotFiltered(t *testing.T) {
	w := newWorkflowForHandleFailureGroupTests(t, nil)

	testutil.InsertBlackWhiteList(t, w.hadata,
		&hamodel.DbBlackWhiteList{
			BkBizID:       100,
			BkCloudID:     1,
			ClusterID:     200,
			ClusterName:   "v1-cluster",
			SwitchVersion: hamodel.SwitchVersionV1,
			Status:        hamodel.StatusTypeEnabled,
		},
	)

	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "v1-cluster", Status: dbm.Available},
		},
	}

	w.filterWhitelistedInstances(context.Background(), group, req)

	if len(req.MySqlInstData) != 1 {
		t.Fatalf("expected 1 instance remaining (v1 switch version not filtered), got %d", len(req.MySqlInstData))
	}
}

func TestFilterWhitelistedInstances_DisabledWhitelistNotFiltered(t *testing.T) {
	w := newWorkflowForHandleFailureGroupTests(t, nil)

	testutil.InsertBlackWhiteList(t, w.hadata,
		&hamodel.DbBlackWhiteList{
			BkBizID:       100,
			BkCloudID:     1,
			ClusterID:     200,
			ClusterName:   "disabled-cluster",
			SwitchVersion: hamodel.SwitchVersionV2,
			Status:        hamodel.StatusTypeDisabled,
		},
	)

	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "disabled-cluster", Status: dbm.Available},
		},
	}

	w.filterWhitelistedInstances(context.Background(), group, req)

	if len(req.MySqlInstData) != 1 {
		t.Fatalf("expected 1 instance remaining (disabled whitelist not filtered), got %d", len(req.MySqlInstData))
	}
}
