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
	"fmt"
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// ============================================================
// buildGroupTasks tests
// ============================================================

func taskStrategy(id int, action hamodel.ActionType) *hamodel.DbSwitchingStrategy {
	return &hamodel.DbSwitchingStrategy{
		ID:     id,
		Name:   fmt.Sprintf("strategy-%d", id),
		Action: action,
	}
}

func taskGroup(strategy *hamodel.DbSwitchingStrategy, instances ...FailureInstanceInfo) *FailureGroup {
	return &FailureGroup{
		BkBizID:   100,
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Strategy:  strategy,
		Instances: instances,
	}
}

func taskMeta(ip string, port int) *dbm.DbInstMetadata {
	return &dbm.DbInstMetadata{BkCloudID: 1, IP: ip, Port: port}
}

// assertTask checks a task's action, bound instances and request instance set.
func assertTask(t *testing.T, task *groupTask, wantAction hamodel.ActionType,
	wantInstKeys []string, wantReqKeys []string) {
	t.Helper()

	if task.action != wantAction {
		t.Fatalf("expected action %s, got %s", wantAction, task.action)
	}

	gotKeys := make([]string, 0, len(task.group.Instances))
	for _, in := range task.group.Instances {
		gotKeys = append(gotKeys, instanceKey(in.BkCloudID, in.IP, in.Port))
	}
	if !sameStringSet(gotKeys, wantInstKeys) {
		t.Fatalf("group instances: expected %v, got %v", wantInstKeys, gotKeys)
	}

	if wantReqKeys == nil {
		if task.req != nil {
			t.Fatalf("expected nil req, got %v", task.req)
		}
		return
	}
	if task.req == nil {
		t.Fatalf("expected non-nil req")
	}
	gotReqKeys := make([]string, 0, len(task.req.MySqlInstData))
	for _, meta := range task.req.MySqlInstData {
		gotReqKeys = append(gotReqKeys, fmt.Sprintf("%s:%d", meta.IP, meta.Port))
	}
	if !sameStringSet(gotReqKeys, wantReqKeys) {
		t.Fatalf("req instances: expected %v, got %v", wantReqKeys, gotReqKeys)
	}
}

// buildGroupTasksCase describes one buildGroupTasks scenario.
type buildGroupTasksCase struct {
	name      string
	desc      string
	req       *switcher.Request
	groups    []*FailureGroup
	wantTasks []wantTask
}

// wantTask describes one expected task produced by buildGroupTasks.
type wantTask struct {
	action    hamodel.ActionType
	instances []string // instance keys, order-insensitive
	reqKeys   []string // request instance keys (ip:port); nil means req should be nil
}

func runBuildGroupTasksCase(t *testing.T, tc buildGroupTasksCase) {
	t.Helper()

	tasks := (&Workflow{}).buildGroupTasks(tc.req, tc.groups)
	if len(tasks) != len(tc.wantTasks) {
		t.Fatalf("expected %d tasks, got %d", len(tc.wantTasks), len(tasks))
	}
	for i, wt := range tc.wantTasks {
		assertTask(t, tasks[i], wt.action, wt.instances, wt.reqKeys)
	}
}

// buildGroupTasksCases holds all buildGroupTasks scenarios, grouped by the aspect they verify.
var buildGroupTasksCases = []buildGroupTasksCase{
	{
		name: "switch_and_notify_split",
		desc: "switch and notify groups split into their own tasks with correct action and req",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
				taskMeta("127.0.0.2", 3306),
			},
		},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
			taskGroup(taskStrategy(2, hamodel.ActionTypeNotify),
				inst("127.0.0.2", 3306, haprobe.DbEventNameProbeOffline)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.1:3306"}, reqKeys: []string{"127.0.0.1:3306"}},
			{action: hamodel.ActionTypeNotify, instances: []string{"1:127.0.0.2:3306"}, reqKeys: nil},
		},
	},
	{
		name: "host_dedup",
		desc: "same host occupied by a higher-priority switch is skipped in later switch groups",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
				taskMeta("127.0.0.1", 3307),
			},
		},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
				inst("127.0.0.1", 3307, haprobe.DbEventNameDetectFailure)),
			taskGroup(taskStrategy(2, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3308, haprobe.DbEventNameSshTimeout)),
		},
		wantTasks: []wantTask{
			{
				action:    hamodel.ActionTypeSwitch,
				instances: []string{"1:127.0.0.1:3306", "1:127.0.0.1:3307"},
				reqKeys:   []string{"127.0.0.1:3306", "127.0.0.1:3307"},
			},
		},
	},
	{
		name: "different_host_independent",
		desc: "different hosts are not affected by each other's occupancy",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
				taskMeta("127.0.0.2", 3306),
			},
		},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
			taskGroup(taskStrategy(2, hamodel.ActionTypeSwitch),
				inst("127.0.0.2", 3306, haprobe.DbEventNameSshTimeout)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.1:3306"}, reqKeys: []string{"127.0.0.1:3306"}},
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.2:3306"}, reqKeys: []string{"127.0.0.2:3306"}},
		},
	},
	{
		name: "notify_not_deduped",
		desc: "notify groups do not participate in host dedup",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
			},
		},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
			taskGroup(taskStrategy(2, hamodel.ActionTypeNotify),
				inst("127.0.0.1", 3307, haprobe.DbEventNameSshTimeout)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.1:3306"}, reqKeys: []string{"127.0.0.1:3306"}},
			{action: hamodel.ActionTypeNotify, instances: []string{"1:127.0.0.1:3307"}, reqKeys: nil},
		},
	},
	{
		name: "all_hosts_occupied_skip",
		desc: "a switch group whose hosts are all occupied is skipped entirely",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
			},
		},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
			taskGroup(taskStrategy(2, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3307, haprobe.DbEventNameSshTimeout)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.1:3306"}, reqKeys: []string{"127.0.0.1:3306"}},
		},
	},
	{
		name: "req_contains_only_group_hosts",
		desc: "switch task req keeps only the metadata of its own group hosts",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
				taskMeta("127.0.0.2", 3306),
			},
		},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.1:3306"}, reqKeys: []string{"127.0.0.1:3306"}},
		},
	},
	{
		name: "empty_group_req_skip",
		desc: "no metadata available for the group results in no task",
		req:  &switcher.Request{DbType: haprobe.DbTypeMySql},
		groups: []*FailureGroup{
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
		},
		wantTasks: nil,
	},
	{
		name: "nil_strategy_notify",
		desc: "nil strategy (unmatched instances) produces a notify task",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
			},
		},
		groups: []*FailureGroup{
			taskGroup(nil,
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeNotify, instances: []string{"1:127.0.0.1:3306"}, reqKeys: nil},
		},
	},
	{
		name: "complex_mixed_groups",
		desc: "mixed switch/notify/nil groups with host overlap dedup correctly and independently",
		req: &switcher.Request{
			DbType: haprobe.DbTypeMySql,
			MySqlInstData: []*dbm.DbInstMetadata{
				taskMeta("127.0.0.1", 3306),
				taskMeta("127.0.0.2", 3306),
				taskMeta("127.0.0.3", 3306),
				taskMeta("127.0.0.4", 3306),
			},
		},
		groups: []*FailureGroup{
			// switch strategy 1: host A (127.0.0.1), DetectFailure
			taskGroup(taskStrategy(1, hamodel.ActionTypeSwitch),
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)),
			// switch strategy 2: host B (127.0.0.2), SshTimeout
			taskGroup(taskStrategy(2, hamodel.ActionTypeSwitch),
				inst("127.0.0.2", 3306, haprobe.DbEventNameSshTimeout)),
			// nil strategy: host C (127.0.0.3), ProbeOffline
			taskGroup(nil,
				inst("127.0.0.3", 3306, haprobe.DbEventNameProbeOffline)),
			// notify strategy: host D (127.0.0.4), DiskWriteFailure
			taskGroup(taskStrategy(3, hamodel.ActionTypeNotify),
				inst("127.0.0.4", 3306, haprobe.DbEventNameDiskWriteFailure)),
		},
		wantTasks: []wantTask{
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.1:3306"}, reqKeys: []string{"127.0.0.1:3306"}},
			{action: hamodel.ActionTypeSwitch, instances: []string{"1:127.0.0.2:3306"}, reqKeys: []string{"127.0.0.2:3306"}},
			{action: hamodel.ActionTypeNotify, instances: []string{"1:127.0.0.3:3306"}, reqKeys: nil},
			{action: hamodel.ActionTypeNotify, instances: []string{"1:127.0.0.4:3306"}, reqKeys: nil},
		},
	},
}

func TestBuildGroupTasks(t *testing.T) {
	for _, tc := range buildGroupTasksCases {
		t.Run(tc.name, func(t *testing.T) {
			runBuildGroupTasksCase(t, tc)
		})
	}
}

// ============================================================
// filterHostsNotOccupied / filterRequestByHosts / filterUnboundInstances tests
// ============================================================

func TestFilterHostsNotOccupied(t *testing.T) {
	insts := []FailureInstanceInfo{
		inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
		inst("127.0.0.2", 3306, haprobe.DbEventNameDetectFailure),
	}

	// empty occupied: all kept
	if got := filterHostsNotOccupied(insts, map[string]struct{}{}); len(got) != 2 {
		t.Fatalf("empty occupied: expected 2, got %d", len(got))
	}

	// partial: only 127.0.0.1 occupied
	occupied := map[string]struct{}{hostKey(1, "127.0.0.1"): {}}
	got := filterHostsNotOccupied(insts, occupied)
	if len(got) != 1 || got[0].IP != "127.0.0.2" {
		t.Fatalf("partial occupied: expected [127.0.0.2], got %v", got)
	}

	// all occupied
	occupied = map[string]struct{}{hostKey(1, "127.0.0.1"): {}, hostKey(1, "127.0.0.2"): {}}
	if got := filterHostsNotOccupied(insts, occupied); len(got) != 0 {
		t.Fatalf("all occupied: expected 0, got %d", len(got))
	}
}

func TestFilterRequestByHosts(t *testing.T) {
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			taskMeta("127.0.0.1", 3306),
			taskMeta("127.0.0.2", 3306),
		},
	}
	insts := []FailureInstanceInfo{inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure)}

	got := filterRequestByHosts(req, insts)
	if got == nil || len(got.MySqlInstData) != 1 || got.MySqlInstData[0].IP != "127.0.0.1" {
		t.Fatalf("expected only 127.0.0.1, got %v", got)
	}

	if filterRequestByHosts(nil, insts) != nil {
		t.Fatal("nil req should return nil")
	}
	if filterRequestByHosts(req, nil) != nil {
		t.Fatal("empty instances should return nil")
	}
}

func TestFilterUnboundInstances(t *testing.T) {
	insts := []FailureInstanceInfo{
		inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
		inst("127.0.0.2", 3306, haprobe.DbEventNameDetectFailure),
	}

	// none bound: all kept
	if got := filterUnboundInstances(insts, map[string]struct{}{}); len(got) != 2 {
		t.Fatalf("none bound: expected 2, got %d", len(got))
	}

	// partial: 127.0.0.1 bound
	bound := map[string]struct{}{instanceKey(1, "127.0.0.1", 3306): {}}
	got := filterUnboundInstances(insts, bound)
	if len(got) != 1 || got[0].IP != "127.0.0.2" {
		t.Fatalf("partial bound: expected [127.0.0.2], got %v", got)
	}

	// all bound
	bound = map[string]struct{}{
		instanceKey(1, "127.0.0.1", 3306): {},
		instanceKey(1, "127.0.0.2", 3306): {},
	}
	if got := filterUnboundInstances(insts, bound); len(got) != 0 {
		t.Fatalf("all bound: expected 0, got %d", len(got))
	}
}
