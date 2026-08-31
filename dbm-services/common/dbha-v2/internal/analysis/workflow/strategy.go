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

// SpecialMatchResult is the result of a special strategy match.
// ClusterKeys is the list of matched cluster keys (BkCloudID:ClusterID) used for trigger-count
// comparison; Instances is the flattened list of failure instances of all matched clusters.
type SpecialMatchResult struct {
	ClusterKeys []switchcore.ClusterKey
	Instances   []FailureInstanceInfo
}

// SpecialMatchFunc is the function signature for special strategy matching.
// It takes the unbound instances and returns the matched cluster keys together with the
// failure instances of those clusters.
type SpecialMatchFunc func(instances []FailureInstanceInfo) SpecialMatchResult

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
// Returns the matched cluster keys and the failure instances of all matched clusters.
func MatchProxyBackendSimultaneous(instances []FailureInstanceInfo) SpecialMatchResult {
	// sub-group by BkCloudID:ClusterID, reusing switchcore.GenerateClusterKey
	clusterGroups := make(map[switchcore.ClusterKey][]FailureInstanceInfo)
	for _, inst := range instances {
		key := switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID)
		clusterGroups[key] = append(clusterGroups[key], inst)
	}

	result := SpecialMatchResult{
		ClusterKeys: make([]switchcore.ClusterKey, 0, len(clusterGroups)),
	}
	for key, group := range clusterGroups {
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
			result.ClusterKeys = append(result.ClusterKeys, key)
			result.Instances = append(result.Instances, group...)
		}
	}

	return result
}

// MatchSpiderRemoteMasterSimultaneous matches cases where spider and remote master fail simultaneously
// within the same cluster (BkCloudID:ClusterID).
// A remote master must satisfy both MachineType == remote and InstanceRole == TenDBClusterStorageMaster.
// Returns the matched cluster keys and the failure instances of all matched clusters.
func MatchSpiderRemoteMasterSimultaneous(instances []FailureInstanceInfo) SpecialMatchResult {
	// sub-group by BkCloudID:ClusterID, reusing switchcore.GenerateClusterKey
	clusterGroups := make(map[switchcore.ClusterKey][]FailureInstanceInfo)
	for _, inst := range instances {
		key := switchcore.GenerateClusterKey(inst.BkCloudID, inst.ClusterID)
		clusterGroups[key] = append(clusterGroups[key], inst)
	}

	result := SpecialMatchResult{
		ClusterKeys: make([]switchcore.ClusterKey, 0, len(clusterGroups)),
	}
	for key, group := range clusterGroups {
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
			result.ClusterKeys = append(result.ClusterKeys, key)
			result.Instances = append(result.Instances, group...)
		}
	}

	return result
}

// FilterInstancesByEventName returns the instances whose event name matches the given event name.
func FilterInstancesByEventName(instances []FailureInstanceInfo, eventName haprobe.DbEventName) []FailureInstanceInfo {
	out := make([]FailureInstanceInfo, 0, len(instances))
	for _, inst := range instances {
		if inst.EventName == eventName {
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
func SortCandidates(candidates []*hamodel.DbSwitchingStrategy) {
	sort.Slice(candidates, func(i, j int) bool {
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
