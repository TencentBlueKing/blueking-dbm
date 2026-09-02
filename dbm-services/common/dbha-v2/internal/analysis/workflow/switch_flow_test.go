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
	"fmt"
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

// ============================================================
// MatchStrategies table-driven tests
// ============================================================

// newTestSwitchExecutor creates a SwitchExecutor backed by SQLite in-memory database for testing.
func newTestSwitchExecutor(t *testing.T) (*SwitchExecutor, *testutil.TestDbhaData) {
	t.Helper()
	td := testutil.NewTestDbhaData(t)
	executor := &SwitchExecutor{hadata: td.DbhaData}
	return executor, td
}

// matchStrategiesCase describes a single MatchStrategies scenario: the strategies and instances
// fed in, plus the expected groups produced.
type matchStrategiesCase struct {
	name       string
	desc       string                         // what this scenario verifies
	strategies []*hamodel.DbSwitchingStrategy // strategies to match against
	instances  []FailureInstanceInfo          // failure instances to match
	wantGroups []wantGroup                    // expected groups, in order
}

// wantGroup describes one expected failure group in the match result.
type wantGroup struct {
	strategyName string   // matched strategy name; "" means the nil-strategy (unmatched) group
	instances    []string // instance keys, order-insensitive
}

// strat builds an enabled strategy with the given core attributes.
func strat(name string, event haprobe.DbEventName, priority int, action hamodel.ActionType,
	bizID, trigger int, opts ...stratOpt) *hamodel.DbSwitchingStrategy {
	s := &hamodel.DbSwitchingStrategy{
		Name:             name,
		BkBizID:          bizID,
		Status:           hamodel.StatusTypeEnabled,
		TriggerEventName: event,
		TriggerCount:     trigger,
		Priority:         priority,
		Action:           action,
	}
	for _, o := range opts {
		o(s)
	}
	return s
}

type stratOpt func(*hamodel.DbSwitchingStrategy)

// disabledStrategy marks a strategy as disabled.
func disabledStrategy() stratOpt {
	return func(s *hamodel.DbSwitchingStrategy) { s.Status = hamodel.StatusTypeDisabled }
}

// globalStrat builds one of the default global strategies (BkBizID=0, switch, priority 9999).
func globalStrat(event haprobe.DbEventName) *hamodel.DbSwitchingStrategy {
	return strat(event.String(), event, 9999, hamodel.ActionTypeSwitch, 0, 1)
}

// withGlobals returns the five default global strategies plus the given extra strategies.
func withGlobals(extras ...*hamodel.DbSwitchingStrategy) []*hamodel.DbSwitchingStrategy {
	base := []*hamodel.DbSwitchingStrategy{
		globalStrat(haprobe.DbEventNameDoubleCheckSshFailureV1),
		globalStrat(haprobe.DbEventNameSshAuthFailure),
		globalStrat(haprobe.DbEventNameSshTimeout),
		globalStrat(haprobe.DbEventNameDiskWriteFailure),
		globalStrat(haprobe.DbEventNameUptimeFailure),
	}
	return append(base, extras...)
}

// inst builds a failure instance with default BkCloudID=1 and BkBizID=100.
func inst(ip string, port int, event haprobe.DbEventName, opts ...instOpt) FailureInstanceInfo {
	i := FailureInstanceInfo{
		BkBizID:   100,
		BkCloudID: 1,
		IP:        ip,
		Port:      port,
		EventName: event,
	}
	for _, o := range opts {
		o(&i)
	}
	return i
}

type instOpt func(*FailureInstanceInfo)

func withCluster(id int, typ haprobe.DbmMetadataClusterType) instOpt {
	return func(i *FailureInstanceInfo) { i.ClusterID = id; i.ClusterType = typ }
}

func withMachine(m haprobe.DbmMetadataMachineType) instOpt {
	return func(i *FailureInstanceInfo) { i.MachineType = m }
}

func withRole(r haprobe.DbmMetadataInstanceRole) instOpt {
	return func(i *FailureInstanceInfo) { i.InstanceRole = r }
}

func instKey(i FailureInstanceInfo) string {
	return fmt.Sprintf("%d:%s:%d", i.BkCloudID, i.IP, i.Port)
}

// runMatchStrategiesCase executes one scenario and asserts the result.
func runMatchStrategiesCase(t *testing.T, tc matchStrategiesCase) {
	t.Helper()
	executor, td := newTestSwitchExecutor(t)
	testutil.InsertStrategies(t, td.DbhaData, tc.strategies...)

	group := &FailureGroup{BkBizID: 100, Instances: tc.instances}
	result := executor.MatchStrategies(context.Background(), group)

	assertMatchResult(t, tc, result)
}

// assertMatchResult checks the no-duplicate-instance invariant across all groups and then verifies
// the scenario-specific expected groups declared in the case.
func assertMatchResult(t *testing.T, tc matchStrategiesCase, result *MatchResult) {
	t.Helper()

	if result == nil {
		if len(tc.wantGroups) != 0 {
			t.Fatalf("expected %d groups, got nil result", len(tc.wantGroups))
		}
		return
	}

	// invariant: an instance must not appear in more than one group.
	owner := make(map[string]string)
	for _, g := range result.Groups {
		name := "unmatched"
		if g.Strategy != nil {
			name = g.Strategy.Name
		}
		for _, in := range g.Instances {
			k := instKey(in)
			if prev, ok := owner[k]; ok {
				t.Fatalf("invariant violated: instance %s appears in both group %q and %q", k, prev, name)
			}
			owner[k] = name
		}
	}

	if len(result.Groups) != len(tc.wantGroups) {
		t.Fatalf("expected %d groups, got %d", len(tc.wantGroups), len(result.Groups))
	}

	// Match groups by strategy name (order-insensitive): each strategy produces at most one group
	// and the nil-strategy group is unique, so the strategy name identifies a group uniquely.
	used := make([]bool, len(result.Groups))
	for _, wg := range tc.wantGroups {
		found := -1
		for i, g := range result.Groups {
			if used[i] {
				continue
			}
			gotName := ""
			if g.Strategy != nil {
				gotName = g.Strategy.Name
			}
			if gotName == wg.strategyName {
				found = i
				break
			}
		}
		if found == -1 {
			t.Errorf("group with strategy %q not found", wg.strategyName)
			continue
		}
		used[found] = true

		gotKeys := make([]string, 0, len(result.Groups[found].Instances))
		for _, in := range result.Groups[found].Instances {
			gotKeys = append(gotKeys, instKey(in))
		}
		if !sameStringSet(gotKeys, wg.instances) {
			t.Errorf("group %q instances: expected %v, got %v", wg.strategyName, wg.instances, gotKeys)
		}
	}
}

func sameStringSet(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	m := make(map[string]int, len(a))
	for _, k := range a {
		m[k]++
	}
	for _, k := range b {
		if m[k] == 0 {
			return false
		}
		m[k]--
	}
	return true
}

func TestMatchStrategies_Normal(t *testing.T) {
	cases := []matchStrategiesCase{
		{
			name: "empty_group",
			desc: "empty group returns nil result",
		},
		{
			name: "no_strategies",
			desc: "no strategies exist, all instances go to the unmatched group",
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "single_match",
			desc: "single strategy binds all matched instances",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("test-normal", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeSwitch, 100, 2),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
				inst("127.0.0.2", 3306, haprobe.DbEventNameDetectFailure),
				inst("127.0.0.3", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "test-normal", instances: []string{
					"1:127.0.0.1:3306", "1:127.0.0.2:3306", "1:127.0.0.3:3306",
				}},
			},
		},
		{
			name: "below_threshold",
			desc: "matched instance count below TriggerCount forms no group",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("test-threshold", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeSwitch, 100, 2),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "trigger_zero_defaults_one",
			desc: "TriggerCount<=0 defaults to 1",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("test-zero-count", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeSwitch, 100, 0),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "test-zero-count", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "trigger_negative_defaults_one",
			desc: "negative TriggerCount defaults to 1",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("neg-count", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeSwitch, 100, -3),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "neg-count", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "event_mismatch",
			desc: "instance event does not match strategy event, all go to unmatched",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("wrong-event", haprobe.DbEventNameProbeOffline, 1, hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "disabled_ignored",
			desc: "disabled strategy is ignored",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("disabled-strategy", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeSwitch, 100, 1,
					disabledStrategy()),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "biz_prioritized",
			desc: "biz-level strategy takes priority over global strategy regardless of priority value",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("global-p1", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeSwitch, 0, 1),
				strat("biz-p3", haprobe.DbEventNameDetectFailure, 3, hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "biz-p3", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			runMatchStrategiesCase(t, tc)
		})
	}
}

func TestMatchStrategies_Special(t *testing.T) {
	cases := []matchStrategiesCase{
		{
			name: "special_matched",
			desc: "special strategy binds the whole cluster when proxy and backend master both fail",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("test-special", haprobe.DbEventNameTendbhaProxyBackendFailure, 1,
					hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 10000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeProxy)),
				inst("127.0.0.2", 20000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeBackend),
					withRole(haprobe.MySQLStorageMaster)),
			},
			wantGroups: []wantGroup{
				{strategyName: "test-special", instances: []string{
					"1:127.0.0.1:10000", "1:127.0.0.2:20000",
				}},
			},
		},
		{
			name: "special_below_threshold",
			desc: "special condition not met (no backend master) leaves instance unmatched",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("test-special-nope", haprobe.DbEventNameTendbhaProxyBackendFailure, 1,
					hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 10000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeProxy)),
			},
			wantGroups: []wantGroup{
				{strategyName: "", instances: []string{"1:127.0.0.1:10000"}},
			},
		},
		{
			name: "normal_special_both",
			desc: "special (higher priority) grabs cluster instances first, normal binds the rest",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("normal-p2", haprobe.DbEventNameDetectFailure, 2, hamodel.ActionTypeSwitch, 100, 1),
				strat("special-p1", haprobe.DbEventNameTendbhaProxyBackendFailure, 1,
					hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDetectFailure),
				inst("127.0.0.2", 10000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeProxy)),
				inst("127.0.0.3", 20000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeBackend),
					withRole(haprobe.MySQLStorageMaster)),
			},
			wantGroups: []wantGroup{
				{strategyName: "special-p1", instances: []string{
					"1:127.0.0.2:10000", "1:127.0.0.3:20000",
				}},
				{strategyName: "normal-p2", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "proxy_backend_multi_cluster",
			desc: "multi-cluster: matched clusters bind whole cluster, unmatched cluster goes to nil group",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("special-proxy-backend", haprobe.DbEventNameTendbhaProxyBackendFailure, 1,
					hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				// cluster 10: satisfied (proxy + backend master + backend slave)
				inst("127.0.0.1", 10000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeProxy)),
				inst("127.0.0.2", 20000, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeBackend),
					withRole(haprobe.MySQLStorageMaster)),
				inst("127.0.0.3", 20001, haprobe.DbEventNameDetectFailure,
					withCluster(10, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeBackend)),
				// cluster 11: satisfied (proxy + backend master)
				inst("127.0.0.4", 10000, haprobe.DbEventNameDetectFailure,
					withCluster(11, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeProxy)),
				inst("127.0.0.5", 20000, haprobe.DbEventNameDetectFailure,
					withCluster(11, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeBackend),
					withRole(haprobe.MySQLStorageMaster)),
				// cluster 12: not satisfied (proxy only)
				inst("127.0.0.6", 10000, haprobe.DbEventNameDetectFailure,
					withCluster(12, haprobe.DbmMetadataClusterTypeTendbha),
					withMachine(haprobe.DbmMetadataMachineTypeProxy)),
			},
			wantGroups: []wantGroup{
				{strategyName: "special-proxy-backend", instances: []string{
					"1:127.0.0.1:10000", "1:127.0.0.2:20000", "1:127.0.0.3:20001",
					"1:127.0.0.4:10000", "1:127.0.0.5:20000",
				}},
				{strategyName: "", instances: []string{"1:127.0.0.6:10000"}},
			},
		},
		{
			name: "spider_remote_multi_cluster",
			desc: "spider-remote special: matched cluster binds whole cluster, unmatched cluster goes to nil group",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("special-spider-remote", haprobe.DbEventNameTendbclusterSpiderRemoteFailure, 1,
					hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				// cluster 20: satisfied (spider + remote master + remote slave)
				inst("127.0.0.7", 30000, haprobe.DbEventNameDetectFailure,
					withCluster(20, haprobe.DbmMetadataClusterTypeTendbCluster),
					withMachine(haprobe.DbmMetadataMachineTypeSpider)),
				inst("127.0.0.8", 40000, haprobe.DbEventNameDetectFailure,
					withCluster(20, haprobe.DbmMetadataClusterTypeTendbCluster),
					withMachine(haprobe.DbmMetadataMachineTypeRemote),
					withRole(haprobe.TenDBClusterStorageMaster)),
				inst("127.0.0.9", 40001, haprobe.DbEventNameDetectFailure,
					withCluster(20, haprobe.DbmMetadataClusterTypeTendbCluster),
					withMachine(haprobe.DbmMetadataMachineTypeRemote)),
				// cluster 21: not satisfied (spider only)
				inst("127.0.0.10", 30000, haprobe.DbEventNameDetectFailure,
					withCluster(21, haprobe.DbmMetadataClusterTypeTendbCluster),
					withMachine(haprobe.DbmMetadataMachineTypeSpider)),
			},
			wantGroups: []wantGroup{
				{strategyName: "special-spider-remote", instances: []string{
					"1:127.0.0.7:30000", "1:127.0.0.8:40000", "1:127.0.0.9:40001",
				}},
				{strategyName: "", instances: []string{"1:127.0.0.10:30000"}},
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			runMatchStrategiesCase(t, tc)
		})
	}
}

func TestMatchStrategies_Multi(t *testing.T) {
	cases := []matchStrategiesCase{
		{
			name:       "global_strategies_diff_events",
			desc:       "all default global strategies match their own events independently",
			strategies: withGlobals(),
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameDoubleCheckSshFailureV1),
				inst("127.0.0.2", 3306, haprobe.DbEventNameSshAuthFailure),
				inst("127.0.0.3", 3306, haprobe.DbEventNameSshTimeout),
				inst("127.0.0.4", 3306, haprobe.DbEventNameDiskWriteFailure),
				inst("127.0.0.5", 3306, haprobe.DbEventNameUptimeFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: haprobe.DbEventNameDoubleCheckSshFailureV1.String(), instances: []string{"1:127.0.0.1:3306"}},
				{strategyName: haprobe.DbEventNameSshAuthFailure.String(), instances: []string{"1:127.0.0.2:3306"}},
				{strategyName: haprobe.DbEventNameSshTimeout.String(), instances: []string{"1:127.0.0.3:3306"}},
				{strategyName: haprobe.DbEventNameDiskWriteFailure.String(), instances: []string{"1:127.0.0.4:3306"}},
				{strategyName: haprobe.DbEventNameUptimeFailure.String(), instances: []string{"1:127.0.0.5:3306"}},
			},
		},
		{
			name: "custom_notify_over_global_switch",
			desc: "custom biz notify with higher priority wins over global switch (notify not overridden)",
			strategies: withGlobals(
				strat("custom-notify-ssh", haprobe.DbEventNameSshAuthFailure, 1, hamodel.ActionTypeNotify, 100, 1)),
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameSshAuthFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "custom-notify-ssh", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "custom_switch_over_global_switch",
			desc: "custom biz switch with higher priority wins over global switch (switch not overridden)",
			strategies: withGlobals(
				strat("custom-switch-ssh", haprobe.DbEventNameSshAuthFailure, 5, hamodel.ActionTypeSwitch, 100, 1)),
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameSshAuthFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "custom-switch-ssh", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "same_event_same_priority_switch_wins",
			desc: "same event same priority, switch beats notify",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("custom-switch-ssh", haprobe.DbEventNameSshAuthFailure, 1, hamodel.ActionTypeSwitch, 100, 1),
				strat("custom-notify-ssh", haprobe.DbEventNameSshAuthFailure, 1, hamodel.ActionTypeNotify, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameSshAuthFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: "custom-switch-ssh", instances: []string{"1:127.0.0.1:3306"}},
			},
		},
		{
			name: "custom_notify_vs_custom_switch_diff_priority",
			desc: "notify with higher priority binds multiple instances; unmatched instances fall into nil group",
			strategies: []*hamodel.DbSwitchingStrategy{
				strat("custom-notify-ssh", haprobe.DbEventNameSshAuthFailure, 1, hamodel.ActionTypeNotify, 100, 1),
				strat("custom-switch-ssh", haprobe.DbEventNameSshAuthFailure, 2, hamodel.ActionTypeSwitch, 100, 1),
			},
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameSshAuthFailure),
				inst("127.0.0.2", 3306, haprobe.DbEventNameSshAuthFailure),
				inst("127.0.0.3", 3306, haprobe.DbEventNameSshAuthFailure),
				inst("127.0.0.4", 3306, haprobe.DbEventNameDetectFailure),
				inst("127.0.0.5", 3306, haprobe.DbEventNameProbeOffline),
			},
			wantGroups: []wantGroup{
				{strategyName: "custom-notify-ssh", instances: []string{
					"1:127.0.0.1:3306", "1:127.0.0.2:3306", "1:127.0.0.3:3306",
				}},
				{strategyName: "", instances: []string{"1:127.0.0.4:3306", "1:127.0.0.5:3306"}},
			},
		},
		{
			name: "global_switch_and_custom_notify_diff_event",
			desc: "global switch and custom notify with different events match independently",
			strategies: withGlobals(
				strat("custom-notify-detect", haprobe.DbEventNameDetectFailure, 1, hamodel.ActionTypeNotify, 100, 1)),
			instances: []FailureInstanceInfo{
				inst("127.0.0.1", 3306, haprobe.DbEventNameSshAuthFailure),
				inst("127.0.0.2", 3306, haprobe.DbEventNameDetectFailure),
			},
			wantGroups: []wantGroup{
				{strategyName: haprobe.DbEventNameSshAuthFailure.String(), instances: []string{"1:127.0.0.1:3306"}},
				{strategyName: "custom-notify-detect", instances: []string{"1:127.0.0.2:3306"}},
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			runMatchStrategiesCase(t, tc)
		})
	}
}

// ============================================================
// CreateRequestWithGroup tests
// ============================================================

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

// ============================================================
// excludeUnavailableInstances / special strategy tests
// ============================================================

func excludeUnavailableInstancesMakeInst(cloud int, ip string, port int, event haprobe.DbEventName) FailureInstanceInfo {
	return FailureInstanceInfo{
		BkCloudID: cloud,
		IP:        ip,
		Port:      port,
		BkBizID:   1,
		DbType:    haprobe.DbTypeMySql,
		EventName: event,
	}
}

func excludeUnavailableInstancesMakeMeta(cloud int, ip string, port int) *dbm.DbInstMetadata {
	return &dbm.DbInstMetadata{
		BkCloudID: cloud,
		IP:        ip,
		Port:      port,
		BkBizID:   1,
		Status:    dbm.Running,
	}
}

// TestExcludeUnavailableInstances verifies that only instances present in the DBM query result
// (i.e. not unavailable) survive the filter, and that a nil/empty req yields no switchable instance.
func TestExcludeUnavailableInstances(t *testing.T) {
	group := []FailureInstanceInfo{
		excludeUnavailableInstancesMakeInst(0, "127.0.0.1", 3306, haprobe.DbEventNameDetectFailure), // available, in req
		excludeUnavailableInstancesMakeInst(0, "127.0.0.2", 3306, haprobe.DbEventNameDetectFailure), // unavailable, not in req
	}
	req := &switcher.Request{
		DbType:        haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{excludeUnavailableInstancesMakeMeta(0, "127.0.0.1", 3306)},
	}

	got := excludeUnavailableInstances(group, req)
	if len(got) != 1 {
		t.Fatalf("expected 1 available instance, got %d", len(got))
	}
	if got[0].IP != "127.0.0.1" {
		t.Fatalf("expected 127.0.0.1 to survive, got %s", got[0].IP)
	}

	// A nil req means DBM returned nothing usable; no instance should be considered switchable.
	if got := excludeUnavailableInstances(group, nil); got != nil {
		t.Fatalf("expected nil for nil req, got %v", got)
	}
	if got := excludeUnavailableInstances(group, &switcher.Request{}); got != nil {
		t.Fatalf("expected nil for empty req, got %v", got)
	}
}

// TestMatchStrategies_SpecialStrategyExcludesStaleInstances verifies that stale failure events
// (already-switched instances) are excluded before special strategy matching, so the aggressive
// cluster-scope strategy is not wrongly selected when only one cluster is actually switchable.
func TestMatchStrategies_SpecialStrategyExcludesStaleInstances(t *testing.T) {
	executor, td := newTestSwitchExecutor(t)

	testutil.InsertStrategies(t, td.DbhaData,
		&hamodel.DbSwitchingStrategy{
			Name:             "host-switch",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     1,
			Priority:         2,
			Scope:            hamodel.ActionScopeTypeHost,
			Action:           hamodel.ActionTypeSwitch,
		},
		&hamodel.DbSwitchingStrategy{
			Name:             "cluster-switch",
			BkBizID:          21,
			Status:           hamodel.StatusTypeEnabled,
			TriggerEventName: haprobe.DbEventNameTendbhaProxyBackendFailure,
			TriggerCount:     2,
			Priority:         1,
			Scope:            hamodel.ActionScopeTypeCluster,
			Action:           hamodel.ActionTypeSwitch,
		},
	)

	rawGroup := &FailureGroup{
		BkBizID:   21,
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Instances: []FailureInstanceInfo{
			{BkBizID: 21, BkCloudID: 1, ClusterID: 10, IP: "127.0.0.10", Port: 3306, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
			{BkBizID: 21, BkCloudID: 1, ClusterID: 10, IP: "127.0.0.11", Port: 3306, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
			{BkBizID: 21, BkCloudID: 1, ClusterID: 11, IP: "127.0.0.20", Port: 3306, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeProxy},
			{BkBizID: 21, BkCloudID: 1, ClusterID: 11, IP: "127.0.0.21", Port: 3306, ClusterType: haprobe.DbmMetadataClusterTypeTendbha, MachineType: haprobe.DbmMetadataMachineTypeBackend, InstanceRole: haprobe.MySQLStorageMaster},
		},
	}

	// DBM only returns the available instances of cluster 10.
	req := &switcher.Request{
		DbType: haprobe.DbTypeMySql,
		MySqlInstData: []*dbm.DbInstMetadata{
			{BkCloudID: 1, IP: "127.0.0.10", Port: 3306, BkBizID: 21, Status: dbm.Running},
			{BkCloudID: 1, IP: "127.0.0.11", Port: 3306, BkBizID: 21, Status: dbm.Running},
		},
	}
	filteredGroup := &FailureGroup{
		BkBizID:   21,
		BkCloudID: 1,
		DbType:    haprobe.DbTypeMySql,
		Instances: excludeUnavailableInstances(rawGroup.Instances, req),
	}
	if len(filteredGroup.Instances) != 2 {
		t.Fatalf("expected 2 switchable instances after excluding stale cluster, got %d", len(filteredGroup.Instances))
	}

	// Without exclusion both clusters satisfy the special condition, so cluster-scope
	// (threshold 2) matches first and binds all 4 instances.
	result := executor.MatchStrategies(context.Background(), rawGroup)
	if result == nil || len(result.Groups) == 0 {
		t.Fatal("raw group should match some strategy")
	}
	if result.Groups[0].Strategy.Scope != hamodel.ActionScopeTypeCluster {
		t.Fatalf("raw group should select cluster-scope, got %s", result.Groups[0].Strategy.Scope)
	}

	// After excluding the stale cluster, only one cluster remains, so host-scope (threshold 1)
	// is selected.
	result = executor.MatchStrategies(context.Background(), filteredGroup)
	if result == nil || len(result.Groups) == 0 {
		t.Fatal("filtered group should still match a strategy")
	}
	if result.Groups[0].Strategy.Scope != hamodel.ActionScopeTypeHost {
		t.Fatalf("filtered group should select host-scope, got %s", result.Groups[0].Strategy.Scope)
	}
}
