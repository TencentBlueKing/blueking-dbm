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

	"dbm-services/common/dbha-v2/internal/analysis/failure"
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
		{EventName: haprobe.DbEventNameDetectFailure, Count: 2},
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
	}
	matched := FilterInstancesByEventAndCount(instances, haprobe.DbEventNameDetectFailure, 2)
	if len(matched) != 1 {
		t.Errorf("expected 1, got %d", len(matched))
	}
}

func TestFilterInstancesByEventAndCount_NoMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameProbeOffline, Count: 1},
		{EventName: haprobe.DbEventNameProbeOffline, Count: 2},
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
// 2. GetSpecialMatchFunc tests
// ============================================================

func TestGetSpecialMatchFunc_RegisteredEvent(t *testing.T) {
	eventName := haprobe.DbEventName("test_special_match")
	failure.RegisterSpecialMatch(eventName, func(instances []failure.Instance, threshold int) []failure.Instance {
		return instances
	})
	fn := GetSpecialMatchFunc(eventName)
	if fn == nil {
		t.Error("expected non-nil match func for registered special event")
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
// 3. SortCandidates tests
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
		t.Errorf("expected switch before notify, got action: %s", candidates[0].Action)
	}
}

func TestSortCandidates_HigherPriorityNotifyBeforeSwitch(t *testing.T) {
	candidates := []*hamodel.DbSwitchingStrategy{
		{BkBizID: 100, Priority: 2, Action: hamodel.ActionTypeSwitch},
		{BkBizID: 100, Priority: 1, Action: hamodel.ActionTypeNotify},
	}
	SortCandidates(candidates)
	if candidates[0].Action != hamodel.ActionTypeNotify {
		t.Errorf("expected higher-priority notify first, got action: %s", candidates[0].Action)
	}
}

// ============================================================
// 4. FormatInstanceNotifySummary tests
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
	expected := strings.Join([]string{
		"cluster:c1(1),inst:127.0.0.1:3306,event:dbha_detect_db_failure,reason:connection exception",
		"cluster:c2(2),inst:127.0.0.2:3307,event:dbha_probe_offline,reason:missed probe",
	}, " | ")
	if result != expected {
		t.Errorf("expected %q, got %q", expected, result)
	}
}
