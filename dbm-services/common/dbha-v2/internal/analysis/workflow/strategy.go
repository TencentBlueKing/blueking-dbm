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

	"dbm-services/common/dbha-v2/internal/analysis/failure"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// SpecialMatchFunc is the function signature for special strategy matching.
// It takes all instances in a group and returns the count of matched special conditions.
type SpecialMatchFunc = failure.SpecialMatchFunc

// GetSpecialMatchFunc returns the special strategy match function for the given event name.
func GetSpecialMatchFunc(eventName haprobe.DbEventName) SpecialMatchFunc {
	return failure.SpecialMatchOf(eventName)
}

// CountInstancesByEventName counts the number of instances matching the specified event name.
func CountInstancesByEventName(instances []FailureInstanceInfo, eventName haprobe.DbEventName) int {
	count := 0
	for _, inst := range instances {
		if inst.EventName == eventName {
			count++
		}
	}
	return count
}

// SortCandidates sorts the candidate strategy list by priority.
// Sorting rules (compared from high to low):
//  1. Biz-level strategies (BkBizID != 0) take priority over global strategies (BkBizID == 0)
//  2. Lower Priority value means higher priority
func SortCandidates(candidates []*hamodel.DbSwitchingStrategy) {
	sort.Slice(candidates, func(i, j int) bool {
		// tier 1: biz-level strategy > global strategy
		iBiz := candidates[i].BkBizID != 0
		jBiz := candidates[j].BkBizID != 0
		if iBiz != jBiz {
			return iBiz
		}

		// tier 2: lower priority value first
		return candidates[i].Priority < candidates[j].Priority
	})
}

// FormatInstanceEventSummary summarizes event names and their counts for all instances in a group, used for logging.
func FormatInstanceEventSummary(instances []FailureInstanceInfo) string {
	eventCounts := make(map[haprobe.DbEventName]int)
	for _, inst := range instances {
		eventCounts[inst.EventName]++
	}

	summary := ""
	for name, count := range eventCounts {
		if summary != "" {
			summary += ", "
		}
		summary += fmt.Sprintf("%s:%d", name, count)
	}
	return summary
}
