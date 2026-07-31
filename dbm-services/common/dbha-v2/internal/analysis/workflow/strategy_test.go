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
// 1. CountInstancesByEventName tests
// ============================================================

func TestCountInstancesByEventName_EmptyInstances(t *testing.T) {
	count := CountInstancesByEventName(nil, haprobe.DbEventNameDetectFailure)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

func TestCountInstancesByEventName_AllMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameDetectFailure},
	}
	count := CountInstancesByEventName(instances, haprobe.DbEventNameDetectFailure)
	if count != 3 {
		t.Errorf("expected 3, got %d", count)
	}
}

func TestCountInstancesByEventName_PartialMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameProbeOffline},
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameProbeOffline},
		{EventName: haprobe.DbEventNameProbeOffline},
	}
	count := CountInstancesByEventName(instances, haprobe.DbEventNameDetectFailure)
	if count != 2 {
		t.Errorf("expected 2, got %d", count)
	}
}

func TestCountInstancesByEventName_NoMatch(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameProbeOffline},
		{EventName: haprobe.DbEventNameProbeOffline},
	}
	count := CountInstancesByEventName(instances, haprobe.DbEventNameDetectFailure)
	if count != 0 {
		t.Errorf("expected 0, got %d", count)
	}
}

// ============================================================
// 2. GetSpecialMatchFunc tests
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

// ============================================================
// 4. FormatInstanceEventSummary tests
// ============================================================

func TestFormatInstanceEventSummary_Empty(t *testing.T) {
	result := FormatInstanceEventSummary(nil)
	if result != "" {
		t.Errorf("expected empty string, got %q", result)
	}
}

func TestFormatInstanceEventSummary_SingleEventName(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameDetectFailure},
	}
	result := FormatInstanceEventSummary(instances)
	expected := "dbha_detect_db_failure:3"
	if result != expected {
		t.Errorf("expected %q, got %q", expected, result)
	}
}

func TestFormatInstanceEventSummary_MultipleEventNames(t *testing.T) {
	instances := []FailureInstanceInfo{
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameDetectFailure},
		{EventName: haprobe.DbEventNameProbeOffline},
	}
	result := FormatInstanceEventSummary(instances)

	// map iteration order is non-deterministic, so verify by containment
	if !strings.Contains(result, "dbha_detect_db_failure:2") {
		t.Errorf("result %q should contain 'dbha_detect_db_failure:2'", result)
	}
	if !strings.Contains(result, "dbha_probe_offline:1") {
		t.Errorf("result %q should contain 'dbha_probe_offline:1'", result)
	}
	// verify format: separated by ", "
	if !strings.Contains(result, ", ") {
		t.Errorf("result %q should contain ', ' separator", result)
	}
}
