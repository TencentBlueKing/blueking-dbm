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
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// ============================================================
// 1. FilterInstancesByEventAndCount tests
// ============================================================

func TestFilterInstancesByEventAndCount_EmptyInstances(t *testing.T) {
	matched := FilterInstancesByEventAndCount(nil, haprobe.DbEventNameDetectFailure, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestFilterInstancesByEventAndCount_AllMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure, Count: 1},
		{EventName: haprobe.DbEventNameDetectFailure, Count: 2},
		{EventName: haprobe.DbEventNameDetectFailure, Count: 3},
	}
	matched := FilterInstancesByEventAndCount(instances, haprobe.DbEventNameDetectFailure, 1)
	if len(matched) != 3 {
		t.Errorf("expected 3, got %d", len(matched))
	}
}

func TestFilterInstancesByEventAndCount_PartialMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure, Count: 1},
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
		{EventName: haprobe.DbEventNameDetectFailure, Count: 1},
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
	}
	matched := FilterInstancesByEventAndCount(instances, haprobe.DbEventNameDetectFailure, 1)
	if len(matched) != 2 {
		t.Errorf("expected 2, got %d", len(matched))
	}
	for _, inst := range matched {
		if inst.EventName != haprobe.DbEventNameDetectFailure {
			t.Errorf("expected only detect-failure instances, got %s", inst.EventName)
		}
	}
}

func TestFilterInstancesByEventAndCount_NoMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
	}
	matched := FilterInstancesByEventAndCount(instances, haprobe.DbEventNameDetectFailure, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestFilterInstancesByEventAndCount_BelowThreshold(t *testing.T) {
	// only instances with Count >= threshold are kept
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure, Count: 1},
		{EventName: haprobe.DbEventNameDetectFailure, Count: 3},
		{EventName: haprobe.DbEventNameDetectFailure, Count: 5},
	}
	matched := FilterInstancesByEventAndCount(instances, haprobe.DbEventNameDetectFailure, 3)
	if len(matched) != 2 {
		t.Errorf("expected 2 (count 3 and 5), got %d", len(matched))
	}
}

// ============================================================
// 2. MatchProxyBackendSimultaneous tests
// ============================================================

func TestMatchProxyBackendSimultaneous_EmptyInstances(t *testing.T) {
	matched := MatchProxyBackendSimultaneous(nil, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_SingleClusterBothTypes(t *testing.T) {
	instances := []FailureInstanceInfo{
		{
			BkCloudID:   1,
			ClusterID:   100,
			ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy,
		},
		{
			BkCloudID:    1,
			ClusterID:    100,
			ClusterType:  haprobe.DbmMetadataClusterTypeTendbha,
			MachineType:  haprobe.DbmMetadataMachineTypeBackend,
			InstanceRole: haprobe.MySQLStorageMaster,
		},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 2 {
		t.Errorf("expected 2 instances, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_SingleClusterOnlyProxy(t *testing.T) {
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_SingleClusterOnlyBackend(t *testing.T) {
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_BackendButNotMaster(t *testing.T) {
	// proxy + backend (but InstanceRole is not backend_master) => not matched
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageSlave},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_MultipleClustersPartialMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		// cluster 100: proxy + backend master => matched
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeBackend,
			InstanceRole: haprobe.MySQLStorageMaster},
		// cluster 200: only proxy => not matched
		{BkCloudID: 1, ClusterID: 200, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		// cluster 300: proxy + backend master => matched
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeBackend,
			InstanceRole: haprobe.MySQLStorageMaster},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 4 {
		t.Errorf("expected 4 instances (cluster 100 + 300), got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_DifferentCloudsSameCluster(t *testing.T) {
	// different BkCloudID with same ClusterID should not be merged into the same cluster
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 2, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_MultipleProxiesAndBackends(t *testing.T) {
	// multiple proxies and backends in the same cluster, count by cluster should be 1
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.1", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.2", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.3", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.4", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.5", ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	matched := MatchProxyBackendSimultaneous(instances, 1)
	if len(matched) != 5 {
		t.Errorf("expected 5 instances, got %d", len(matched))
	}
}

func TestMatchProxyBackendSimultaneous_BelowClusterThreshold(t *testing.T) {
	// one satisfied cluster but threshold=2 => clusterCount(1) < threshold => nil
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeProxy},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbha,
			MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
	}
	matched := MatchProxyBackendSimultaneous(instances, 2)
	if matched != nil {
		t.Fatalf("expected nil when clusterCount(1) < threshold(2), got %d instances", len(matched))
	}
}

// ============================================================
// 3. MatchSpiderRemoteMasterSimultaneous tests
// ============================================================

func TestMatchSpiderRemoteMasterSimultaneous_EmptyInstances(t *testing.T) {
	matched := MatchSpiderRemoteMasterSimultaneous(nil, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_SingleClusterBothTypes(t *testing.T) {
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 2 {
		t.Errorf("expected 2 instances, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_SingleClusterOnlySpider(t *testing.T) {
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_SingleClusterOnlyRemoteMaster(t *testing.T) {
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_RemoteButNotMaster(t *testing.T) {
	// spider + remote (but InstanceRole is not remote_master) => not matched
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageSlave},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_MultipleClustersPartialMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		// cluster 100: spider + remote master => matched
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
		// cluster 200: only spider => not matched
		{BkCloudID: 1, ClusterID: 200, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		// cluster 300: spider + remote master => matched
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 300, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 4 {
		t.Errorf("expected 4 instances (cluster 100 + 300), got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_DifferentCloudsSameCluster(t *testing.T) {
	// different BkCloudID with same ClusterID should not be merged into the same cluster
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 2, ClusterID: 100, MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 0 {
		t.Errorf("expected 0, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_MultipleInstancesSameCluster(t *testing.T) {
	// multiple spiders and remote masters in the same cluster, count by cluster should be 1
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.1", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.2", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.3", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
		{BkCloudID: 1, ClusterID: 100, IP: "127.0.0.4", ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 1)
	if len(matched) != 4 {
		t.Errorf("expected 4 instances, got %d", len(matched))
	}
}

func TestMatchSpiderRemoteMasterSimultaneous_BelowClusterThreshold(t *testing.T) {
	// one satisfied cluster but threshold=2 => clusterCount(1) < threshold => nil
	instances := []FailureInstanceInfo{
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeSpider},
		{BkCloudID: 1, ClusterID: 100, ClusterType: haprobe.DbmMetadataClusterTypeTendbCluster,
			MachineType: haprobe.DbmMetadataMachineTypeRemote, InstanceRole: haprobe.TenDBClusterStorageMaster},
	}
	matched := MatchSpiderRemoteMasterSimultaneous(instances, 2)
	if matched != nil {
		t.Fatalf("expected nil when clusterCount(1) < threshold(2), got %d instances", len(matched))
	}
}

// ============================================================
// 4. GetSpecialMatchFunc tests
// ============================================================

func TestGetSpecialMatchFunc_RegisteredProxyBackendEvent(t *testing.T) {
	fn := GetSpecialMatchFunc(haprobe.DbEventNameTendbhaProxyBackendFailure)
	if fn == nil {
		t.Error("expected non-nil match func for registered proxy-backend special event")
	}
}

func TestGetSpecialMatchFunc_RegisteredSpiderRemoteEvent(t *testing.T) {
	fn := GetSpecialMatchFunc(haprobe.DbEventNameTendbclusterSpiderRemoteFailure)
	if fn == nil {
		t.Error("expected non-nil match func for registered spider-remote special event")
	}
}

func TestGetSpecialMatchFunc_UnregisteredEvent(t *testing.T) {
	fn := GetSpecialMatchFunc(haprobe.DbEventNameDetectFailure)
	if fn != nil {
		t.Error("expected nil for unregistered event")
	}
}

func TestGetSpecialMatchFunc_EmptyEvent(t *testing.T) {
	fn := GetSpecialMatchFunc("")
	if fn != nil {
		t.Error("expected nil for empty event name")
	}
}

// ============================================================
// 5. SortCandidates tests
// ============================================================

func TestSortCandidates_BizPriorityOverGlobal(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 0, Priority: 1},   // global
		{BkBizID: 100, Priority: 2}, // biz-level
	}
	SortCandidates(candidates)
	if candidates[0].BkBizID != 100 {
		t.Errorf("expected biz strategy first, got BkBizID=%d", candidates[0].BkBizID)
	}
}

func TestSortCandidates_SameBizSortByPriority(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 100, Priority: 3},
		{BkBizID: 100, Priority: 1},
	}
	SortCandidates(candidates)
	if candidates[0].Priority != 1 {
		t.Errorf("expected priority=1 first, got priority=%d", candidates[0].Priority)
	}
}

func TestSortCandidates_SameGlobalSortByPriority(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 0, Priority: 5},
		{BkBizID: 0, Priority: 2},
	}
	SortCandidates(candidates)
	if candidates[0].Priority != 2 {
		t.Errorf("expected priority=2 first, got priority=%d", candidates[0].Priority)
	}
}

func TestSortCandidates_MixedStrategies(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 0, Priority: 1},   // global p=1
		{BkBizID: 0, Priority: 3},   // global p=3
		{BkBizID: 100, Priority: 5}, // biz-level p=5
		{BkBizID: 100, Priority: 2}, // biz-level p=2
	}
	SortCandidates(candidates)

	// expected order: biz p=2 -> biz p=5 -> global p=1 -> global p=3
	expected := []struct {
		BkBizID  int
		Priority int
	}{
		{100, 2}, {100, 5}, {0, 1}, {0, 3},
	}
	for i, e := range expected {
		if candidates[i].BkBizID != e.BkBizID || candidates[i].Priority != e.Priority {
			t.Errorf("index %d: expected (BkBizID=%d, Priority=%d), got (BkBizID=%d, Priority=%d)",
				i, e.BkBizID, e.Priority, candidates[i].BkBizID, candidates[i].Priority)
		}
	}
}

func TestSortCandidates_Empty(t *testing.T) {
	var candidates []*hamodel.DbSwitchingStrategy
	SortCandidates(candidates) // should not panic
	if len(candidates) != 0 {
		t.Error("expected empty list")
	}
}

func TestSortCandidates_Single(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 100, Priority: 1},
	}
	SortCandidates(candidates)
	if len(candidates) != 1 || candidates[0].BkBizID != 100 {
		t.Error("single element should remain unchanged")
	}
}

func TestSortCandidates_SamePrioritySwitchBeforeNotify(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 100, Priority: 1, Action: hamodel.ActionTypeNotify},
		{BkBizID: 100, Priority: 1, Action: hamodel.ActionTypeSwitch},
	}
	SortCandidates(candidates)
	if candidates[0].Action != hamodel.ActionTypeSwitch {
		t.Errorf("expected switch before notify, got action=%s", candidates[0].Action)
	}
	if candidates[1].Action != hamodel.ActionTypeNotify {
		t.Errorf("expected notify after switch, got action=%s", candidates[1].Action)
	}
}

func TestSortCandidates_HigherPriorityNotifyBeforeSwitch(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 100, Priority: 2, Action: hamodel.ActionTypeSwitch},
		{BkBizID: 100, Priority: 1, Action: hamodel.ActionTypeNotify},
	}
	SortCandidates(candidates)
	if candidates[0].Action != hamodel.ActionTypeNotify {
		t.Errorf("expected notify (priority=1) before switch (priority=2), got action=%s", candidates[0].Action)
	}
	if candidates[1].Action != hamodel.ActionTypeSwitch {
		t.Errorf("expected switch after notify, got action=%s", candidates[1].Action)
	}
}

// ============================================================
// 6. FormatInstanceNotifySummary tests
// ============================================================

func TestFormatInstanceNotifySummary_Empty(t *testing.T) {
	result := FormatInstanceNotifySummary(nil)
	if result != "" {
		t.Errorf("expected empty string, got %q", result)
	}
}

func TestFormatInstanceNotifySummary_SingleInstance(t *testing.T) {
	instances := []FailureInstanceInfo{
		{
			Cluster:         "test-cluster",
			ClusterID:       10,
			IP:              "127.0.0.1",
			Port:            3306,
			EventName:       haprobe.DbEventNameDetectFailure,
			EventNameReason: haprobe.DbEventNameReasonSSHAuthException,
		},
	}
	result := FormatInstanceNotifySummary(instances)
	expected := "cluster:test-cluster(10),inst:127.0.0.1:3306,event:dbha_detect_db_failure,reason:ssh auth failure"
	if result != expected {
		t.Errorf("expected %q, got %q", expected, result)
	}
}

func TestFormatInstanceNotifySummary_MultipleInstances(t *testing.T) {
	instances := []FailureInstanceInfo{
		{
			Cluster:         "c1",
			ClusterID:       1,
			IP:              "127.0.0.1",
			Port:            3306,
			EventName:       haprobe.DbEventNameDetectFailure,
			EventNameReason: haprobe.DbEventNameReasonConnectionException,
		},
		{
			Cluster:         "c2",
			ClusterID:       2,
			IP:              "127.0.0.2",
			Port:            3307,
			EventName:       haprobe.DbEventNameProbeOffline,
			EventNameReason: haprobe.DbEventNameReasonMissedProbe,
		},
	}
	result := FormatInstanceNotifySummary(instances)

	// instances are joined by " | " in order
	expectedParts := []string{
		"cluster:c1(1),inst:127.0.0.1:3306,event:dbha_detect_db_failure,reason:connection exception",
		"cluster:c2(2),inst:127.0.0.2:3307,event:dbha_probe_offline,reason:missed probe",
	}
	expected := strings.Join(expectedParts, " | ")
	if result != expected {
		t.Errorf("expected %q, got %q", expected, result)
	}
}
