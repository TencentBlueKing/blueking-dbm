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

	"dbm-services/common/dbha-v2/internal/analysis/failure"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// SpecialMatchFunc is the function signature for special strategy matching.
// It takes unbound instances and a trigger threshold, then returns matching failure instances.
type SpecialMatchFunc = failure.SpecialMatchFunc

// GetSpecialMatchFunc returns the provider-registered special matcher for the event name.
func GetSpecialMatchFunc(eventName haprobe.DbEventName) SpecialMatchFunc {
	return failure.SpecialMatchOf(eventName)
}

// FilterInstancesByEventAndCount returns instances matching eventName whose count reaches threshold.
func FilterInstancesByEventAndCount(
	instances []FailureInstanceInfo,
	eventName haprobe.DbEventName,
	threshold int,
) []FailureInstanceInfo {
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
// Equal candidates retain their original order.
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

// FormatInstanceNotifySummary formats instance details for notification content.
func FormatInstanceNotifySummary(instances []FailureInstanceInfo) string {
	parts := make([]string, 0, len(instances))
	for _, inst := range instances {
		parts = append(parts, fmt.Sprintf(
			"cluster:%s(%d),inst:%s:%d,event:%s,reason:%s",
			inst.Cluster,
			inst.ClusterID,
			inst.IP,
			inst.Port,
			inst.EventName.String(),
			inst.EventNameReason.Str().String(),
		))
	}
	return strings.Join(parts, " | ")
}
