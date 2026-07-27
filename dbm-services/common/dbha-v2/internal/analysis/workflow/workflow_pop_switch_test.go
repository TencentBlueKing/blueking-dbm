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

func setupEnableSwitchingForTest(t *testing.T) {
	t.Helper()
	old := config.Cfg.Workflow.EnableSwitching
	config.Cfg.Workflow.EnableSwitching = true
	t.Cleanup(func() {
		config.Cfg.Workflow.EnableSwitching = old
	})
}

func setupEnableWhiteListForTest(t *testing.T) {
	t.Helper()
	old := config.Cfg.Workflow.EnableWhiteList
	config.Cfg.Workflow.EnableWhiteList = true
	t.Cleanup(func() {
		config.Cfg.Workflow.EnableWhiteList = old
	})
}

func setupBlackWhiteListAPIForTest(t *testing.T, serverURL string) {
	t.Helper()
	old := config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet
	config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Api = serverURL
	config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Token = "test-token"
	config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Timeout = time.Second
	t.Cleanup(func() {
		config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet = old
	})
}

func newWorkflowForHandleFailureGroupTests(t *testing.T, dbmClient *dbm.Client) *Workflow {
	t.Helper()
	td := testutil.NewTestDbhaData(t)
	return &Workflow{
		hadata:    td.DbhaData,
		alarm:     NewAlarmNotifier(),
		dbmSync:   &Synchronizer{cli: dbmClient},
		windowMgr: NewBizWindowManager(10*time.Second, 30*time.Second, "test-service"),
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
	w := &Workflow{windowMgr: NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")}
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

func TestFilterWhitelistedInstances_NoWhitelistNotifiesAll(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)

	// dbha-v1 returns an empty whitelist
	server := testutil.NewDbhaV1BlackWhiteListTestServer(t, nil)
	setupBlackWhiteListAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "test-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// whitelist is empty: no instance is authorised to switch, all are notified
	if len(req.InstData) != 0 {
		t.Fatalf("expected 0 instances remaining (no whitelist, all notified), got %d", len(req.InstData))
	}
}

func TestFilterWhitelistedInstances_WhitelistedInstanceKept(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)

	// dbha-v1 whitelist contains cluster 200
	server := testutil.NewDbhaV1BlackWhiteListTestServer(t, []*dbm.Dbhav1BlackWhiteListItem{
		{
			BkBizID:       100,
			ClusterID:     200,
			ClusterName:   "test-cluster",
			SwitchVersion: string(hamodel.SwitchVersionV2),
			Status:        string(hamodel.StatusTypeEnabled),
		},
	})
	setupBlackWhiteListAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "test-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// whitelisted instance is kept for switching
	if len(req.InstData) != 1 {
		t.Fatalf("expected 1 instance remaining (whitelisted, kept for switching), got %d", len(req.InstData))
	}
}

func TestFilterWhitelistedInstances_PartialWhitelisted(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)

	// dbha-v1 whitelist contains only cluster 200
	server := testutil.NewDbhaV1BlackWhiteListTestServer(t, []*dbm.Dbhav1BlackWhiteListItem{
		{
			BkBizID:       100,
			ClusterID:     200,
			ClusterName:   "whitelisted-cluster",
			SwitchVersion: string(hamodel.SwitchVersionV2),
			Status:        string(hamodel.StatusTypeEnabled),
		},
	})
	setupBlackWhiteListAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "whitelisted-cluster", Status: dbm.Available},
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.11", Port: 3306, ClusterID: 300, Cluster: "normal-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// only the whitelisted instance (ClusterID=200) is kept for switching;
	// the non-whitelisted instance (ClusterID=300) is filtered out and notified
	if len(req.InstData) != 1 {
		t.Fatalf("expected 1 instance remaining, got %d", len(req.InstData))
	}
	if req.InstData[0].ClusterID != 200 {
		t.Fatalf("expected remaining instance clusterId=200, got %d", req.InstData[0].ClusterID)
	}
}

func TestFilterWhitelistedInstances_V1SwitchVersionNotWhitelisted(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)

	// dbha-v1 filters out v1 switch version, so the whitelist is empty
	server := testutil.NewDbhaV1BlackWhiteListTestServer(t, nil)
	setupBlackWhiteListAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "v1-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// whitelist is empty (v1 excluded): instance is treated as non-whitelisted, notify only
	if len(req.InstData) != 0 {
		t.Fatalf("expected 0 instances remaining (v1 excluded, whitelist empty, notify only), got %d", len(req.InstData))
	}
}

func TestFilterWhitelistedInstances_DisabledWhitelistNotWhitelisted(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)

	// dbha-v1 filters out disabled entries, so the whitelist is empty
	server := testutil.NewDbhaV1BlackWhiteListTestServer(t, nil)
	setupBlackWhiteListAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "disabled-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// whitelist is empty (disabled excluded): instance is treated as non-whitelisted, notify only
	if len(req.InstData) != 0 {
		t.Fatalf("expected 0 instances remaining (disabled excluded, whitelist empty, notify only), got %d", len(req.InstData))
	}
}

func TestFilterWhitelistedInstances_WhiteListDisabledSkipsFiltering(t *testing.T) {
	setupEnableSwitchingForTest(t)
	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})

	// whitelist feature is disabled: filtering is skipped, all instances proceed to switching
	config.Cfg.Workflow.EnableWhiteList = false

	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "test-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// whitelist disabled: req.InstData is unchanged, all instances proceed to switching
	if len(req.InstData) != 1 {
		t.Fatalf("expected 1 instance remaining (whitelist disabled, filtering skipped), got %d", len(req.InstData))
	}
}

func TestFilterWhitelistedInstances_SwitchingDisabledSkipsFiltering(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)
	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})

	// switching is disabled: filtering is skipped, req.InstData is unchanged
	config.Cfg.Workflow.EnableSwitching = false

	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "test-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	if len(req.InstData) != 1 {
		t.Fatalf("expected 1 instance remaining (switching disabled), got %d", len(req.InstData))
	}
}

func TestFilterWhitelistedInstances_NoneWhitelisted(t *testing.T) {
	setupEnableSwitchingForTest(t)
	setupEnableWhiteListForTest(t)

	// dbha-v1 whitelist contains cluster 999, which does not match the instance (cluster 200)
	server := testutil.NewDbhaV1BlackWhiteListTestServer(t, []*dbm.Dbhav1BlackWhiteListItem{
		{
			BkBizID:       100,
			ClusterID:     999,
			ClusterName:   "other-cluster",
			SwitchVersion: string(hamodel.SwitchVersionV2),
			Status:        string(hamodel.StatusTypeEnabled),
		},
	})
	setupBlackWhiteListAPIForTest(t, server.URL)

	w := newWorkflowForHandleFailureGroupTests(t, &dbm.Client{})
	group := buildSingleFailureGroup()
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		InstData: []*dbm.DbInstMetadata{
			{BkBizID: 100, BkCloudID: 1, IP: "127.0.0.10", Port: 3306, ClusterID: 200, Cluster: "unmatched-cluster", Status: dbm.Available},
		},
	}

	w.filterByWhitelistForSwitch(context.Background(), group, req)

	// no instance matches the whitelist: req.InstData is cleared,
	// and a notification alarm is sent for the non-whitelisted instance
	if len(req.InstData) != 0 {
		t.Fatalf("expected 0 instances remaining (none whitelisted), got %d", len(req.InstData))
	}
}
