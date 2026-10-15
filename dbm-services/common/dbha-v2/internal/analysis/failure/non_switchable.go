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

package failure

import (
	"fmt"
	"sort"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// NonSwitchableMatcher tells whether an instance of a database type never triggers a switch.
// Such instances still trigger detection and alarming, but never reach strategy matching.
type NonSwitchableMatcher func(inst *Instance) bool

var (
	nonSwitchableMu       sync.RWMutex
	nonSwitchableByDbType = map[haprobe.DbType]NonSwitchableMatcher{}
)

// RegisterNonSwitchableMatcher registers a matcher that marks the instances of a database type
// which never trigger a switch; those instances still trigger detection and alarming.
// It panics on an invalid DbType, a nil matcher, or a duplicate registration.
func RegisterNonSwitchableMatcher(dbType haprobe.DbType, matcher NonSwitchableMatcher) {
	if dbType == haprobe.DbTypeNone || dbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("failure: refuse to register non-switchable matcher for invalid DbType: %q", dbType))
	}
	if matcher == nil {
		panic(fmt.Sprintf("failure: refuse to register nil non-switchable matcher for DbType: %s", dbType))
	}

	nonSwitchableMu.Lock()
	defer nonSwitchableMu.Unlock()

	if _, exists := nonSwitchableByDbType[dbType]; exists {
		panic(fmt.Sprintf("failure: duplicate non-switchable registration for DbType: %s", dbType))
	}
	nonSwitchableByDbType[dbType] = matcher
}

// NonSwitchableOf tells whether the instance never triggers a switch.
// It returns false when the instance is nil or its database type has no matcher registered.
func NonSwitchableOf(inst *Instance) bool {
	if inst == nil {
		return false
	}

	nonSwitchableMu.RLock()
	matcher, ok := nonSwitchableByDbType[inst.DbType]
	nonSwitchableMu.RUnlock()

	if !ok {
		return false
	}
	return matcher(inst)
}

// RegisteredNonSwitchableDbTypes returns the registered database types in sorted order,
// used by the analysis startup self-check log.
func RegisteredNonSwitchableDbTypes() []haprobe.DbType {
	nonSwitchableMu.RLock()
	defer nonSwitchableMu.RUnlock()

	out := make([]haprobe.DbType, 0, len(nonSwitchableByDbType))
	for dbType := range nonSwitchableByDbType {
		out = append(out, dbType)
	}
	sort.Slice(out, func(i, j int) bool {
		return string(out[i]) < string(out[j])
	})
	return out
}
