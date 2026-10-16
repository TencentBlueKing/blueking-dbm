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

// SpecialMatchFunc returns instances matching a special strategy when the matched unit count reaches threshold.
type SpecialMatchFunc func(instances []Instance, threshold int) []Instance

var (
	specialMatchMu      sync.RWMutex
	specialMatchByEvent = map[haprobe.DbEventName]SpecialMatchFunc{}
)

// RegisterSpecialMatch registers a threshold-aware special strategy matcher for a trigger event name.
// It panics on an empty event name, a nil matcher, or duplicate registration.
func RegisterSpecialMatch(eventName haprobe.DbEventName, fn SpecialMatchFunc) {
	if eventName == "" {
		panic("failure: refuse to register special match for empty event name")
	}
	if fn == nil {
		panic(fmt.Sprintf("failure: refuse to register nil special match for event: %s", eventName))
	}

	specialMatchMu.Lock()
	defer specialMatchMu.Unlock()

	if _, exists := specialMatchByEvent[eventName]; exists {
		panic(fmt.Sprintf("failure: duplicate special match registration for event: %s", eventName))
	}
	specialMatchByEvent[eventName] = fn
}

// SpecialMatchOf returns the threshold-aware matcher for the event name, or nil when unregistered.
func SpecialMatchOf(eventName haprobe.DbEventName) SpecialMatchFunc {
	specialMatchMu.RLock()
	defer specialMatchMu.RUnlock()
	return specialMatchByEvent[eventName]
}

// RegisteredSpecialMatchEvents returns registered event names in sorted order,
// used by the analysis startup self-check log.
func RegisteredSpecialMatchEvents() []haprobe.DbEventName {
	specialMatchMu.RLock()
	defer specialMatchMu.RUnlock()

	out := make([]haprobe.DbEventName, 0, len(specialMatchByEvent))
	for name := range specialMatchByEvent {
		out = append(out, name)
	}
	sort.Slice(out, func(i, j int) bool {
		return string(out[i]) < string(out[j])
	})
	return out
}
