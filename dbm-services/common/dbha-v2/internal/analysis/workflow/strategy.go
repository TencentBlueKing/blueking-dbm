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
	"sort"
	"strings"

	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// SpecialMatchFunc is the function signature for special strategy matching.
// It takes the unbound instances and the strategy trigger count, and returns the matched
// failure instances, or nil if the matched unit count is below the threshold.
type SpecialMatchFunc func(instances []FailureInstanceInfo, threshold int) []FailureInstanceInfo

// specialStrategyRegistry is the registry of special strategies.
// key: the event name bound to the strategy (TriggerEventName), value: the corresponding match function.
// To add a new special strategy, simply register it here without modifying the main matching flow.
var specialStrategyRegistry = map[haprobe.DbEventName]SpecialMatchFunc{
	haprobe.DbEventNameTendbhaProxyBackendFailure:      MatchProxyBackendSimultaneous,
	haprobe.DbEventNameTendbclusterSpiderRemoteFailure: MatchSpiderRemoteMasterSimultaneous,
}

// GetSpecialMatchFunc returns the special strategy match function for the given event name.
func GetSpecialMatchFunc(eventName haprobe.DbEventName) SpecialMatchFunc {
	return specialStrategyRegistry[eventName]
}

// MatchProxyBackendSimultaneous matches cases where proxy and backend master fail simultaneously
// within the same cluster (BkCloudID:ClusterID).
// A backend master must satisfy both MachineType == backend and InstanceRole == MySQLStorageMaster.
// It returns the failure instances of all matched clusters, or nil if the number of matched
// clusters is below the threshold.
func MatchProxyBackendSimultaneous(instances []FailureInstanceInfo, threshold int) []FailureInstanceInfo {
	// sub-group by BkCloudID:ClusterID, reusing switchcore.GenerateClusterKey
	clusterGroups := make(map[switchcore.ClusterKey][]FailureInstanceInfo)
	for _, inst := range instances {
		key := switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID)
		clusterGroups[key] = append(clusterGroups[key], inst)
	}

	var matched []FailureInstanceInfo
	var clusterCount int
	for _, group := range clusterGroups {
		hasProxy := false
		hasBackendMaster := false
		for _, inst := range group {
			if inst.ClusterType != haprobe.DbmMetadataClusterTypeTendbha {
				continue
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeProxy {
				hasProxy = true
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeBackend &&
				inst.InstanceRole == haprobe.MySQLStorageMaster {
				hasBackendMaster = true
			}
			if hasProxy && hasBackendMaster {
				break
			}
		}
		if hasProxy && hasBackendMaster {
			clusterCount++
			matched = append(matched, group...)
		}
	}

	if clusterCount < threshold {
		return nil
	}
	return matched
}

// MatchSpiderRemoteMasterSimultaneous matches cases where spider and remote master fail simultaneously
// within the same cluster (BkCloudID:ClusterID).
// A remote master must satisfy both MachineType == remote and InstanceRole == TenDBClusterStorageMaster.
// It returns the failure instances of all matched clusters, or nil if the number of matched
// clusters is below the threshold.
func MatchSpiderRemoteMasterSimultaneous(instances []FailureInstanceInfo, threshold int) []FailureInstanceInfo {
	// sub-group by BkCloudID:ClusterID, reusing switchcore.GenerateClusterKey
	clusterGroups := make(map[switchcore.ClusterKey][]FailureInstanceInfo)
	for _, inst := range instances {
		key := switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID)
		clusterGroups[key] = append(clusterGroups[key], inst)
	}

	var matched []FailureInstanceInfo
	var clusterCount int
	for _, group := range clusterGroups {
		hasSpider := false
		hasRemoteMaster := false
		for _, inst := range group {
			if inst.ClusterType != haprobe.DbmMetadataClusterTypeTendbCluster {
				continue
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeSpider {
				hasSpider = true
			}
			if inst.MachineType == haprobe.DbmMetadataMachineTypeRemote &&
				inst.InstanceRole == haprobe.TenDBClusterStorageMaster {
				hasRemoteMaster = true
			}
			if hasSpider && hasRemoteMaster {
				break
			}
		}
		if hasSpider && hasRemoteMaster {
			clusterCount++
			matched = append(matched, group...)
		}
	}

	if clusterCount < threshold {
		return nil
	}
	return matched
}

// FilterInstancesByEventAndCount returns the instances whose event name matches the given event
// name and whose trigger count reaches the threshold.
func FilterInstancesByEventAndCount(instances []FailureInstanceInfo, eventName haprobe.DbEventName, threshold int) []FailureInstanceInfo {
	out := make([]FailureInstanceInfo, 0, len(instances))
	for _, inst := range instances {
		if inst.EventName == eventName && inst.Count >= threshold {
			out = append(out, inst)
		}
	}
	return out
}

// SortCandidates sorts the candidate strategy list by priority.
// Sorting rules (compared from high to low):
//  1. Biz-level strategies (BkBizID != 0) take priority over global strategies (BkBizID == 0)
//  2. Lower Priority value means higher priority
//  3. When priority is equal, switch action takes priority over notify action
//
// The sort is stable: strategies that are equal on all tiers keep their original (query) order,
// which makes the match order deterministic for strategies with identical priority.
func SortCandidates(candidates []*hamodel.DbSwitchingStrategy) {
	sort.SliceStable(candidates, func(i, j int) bool {
		// tier 1: biz-level strategy > global strategy
		iBiz := candidates[i].BkBizID != 0
		jBiz := candidates[j].BkBizID != 0
		if iBiz != jBiz {
			return iBiz
		}

		// tier 2: lower priority value first
		if candidates[i].Priority != candidates[j].Priority {
			return candidates[i].Priority < candidates[j].Priority
		}

		// tier 3: switch action > notify action when priority is equal
		iSwitch := candidates[i].Action == hamodel.ActionTypeSwitch
		jSwitch := candidates[j].Action == hamodel.ActionTypeSwitch
		return iSwitch && !jSwitch
	})
}

// FormatInstanceNotifySummary formats instance details (cluster, ip:port, event, reason)
// for notification content, so the notify alarm can be located to specific instances.
func FormatInstanceNotifySummary(instances []FailureInstanceInfo) string {
	parts := make([]string, 0, len(instances))
	for _, inst := range instances {
		parts = append(parts, fmt.Sprintf(
			"cluster:%s(%d),inst:%s:%d,event:%s,reason:%s",
			inst.Cluster, inst.ClusterID, inst.IP, inst.Port,
			inst.EventName.String(), inst.EventNameReason.Str().String(),
		))
	}
	return strings.Join(parts, " | ")
}
