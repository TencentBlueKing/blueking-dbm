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

package dbtype

import (
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// SwitchAlarmEvents holds monitor event names for switch success/failure alarms.
type SwitchAlarmEvents struct {
	Success haprobe.DbEventName
	Failure haprobe.DbEventName
}

var (
	switchAlarmMu       sync.RWMutex
	switchAlarmByDbType = map[haprobe.DbType]SwitchAlarmEvents{}
)

// RegisterSwitchAlarmEvents registers switch alarm event names for a DbType.
// Panics on duplicate registration.
func RegisterSwitchAlarmEvents(dt haprobe.DbType, events SwitchAlarmEvents) {
	if dt == haprobe.DbTypeNone || dt == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("dbtype: refuse to register switch alarms for invalid DbType: %q", dt))
	}
	if events.Success == "" || events.Failure == "" {
		panic(fmt.Sprintf("dbtype: refuse to register empty switch alarm events for DbType: %s", dt))
	}

	switchAlarmMu.Lock()
	defer switchAlarmMu.Unlock()

	if _, exists := switchAlarmByDbType[dt]; exists {
		panic(fmt.Sprintf("dbtype: duplicate switch alarm registration for DbType: %s", dt))
	}
	switchAlarmByDbType[dt] = events
}

// SwitchAlarmEventsOf returns registered switch alarm events for a DbType.
func SwitchAlarmEventsOf(dt haprobe.DbType) (SwitchAlarmEvents, bool) {
	switchAlarmMu.RLock()
	defer switchAlarmMu.RUnlock()
	e, ok := switchAlarmByDbType[dt]
	return e, ok
}

// SwitchSuccessEventName returns the success alarm event for dt.
// Falls back to the historical MySQL event name for unregistered types.
// After startup Validate() this fallback is theoretically unreachable for
// registered switchers.
func SwitchSuccessEventName(dt haprobe.DbType) haprobe.DbEventName {
	if e, ok := SwitchAlarmEventsOf(dt); ok {
		return e.Success
	}
	return haprobe.DbEventNameMysqlSwitchSuccessV1
}

// SwitchFailureEventName returns the failure alarm event for dt.
// Falls back to the historical MySQL event name for unregistered types.
// After startup Validate() this fallback is theoretically unreachable for
// registered switchers.
func SwitchFailureEventName(dt haprobe.DbType) haprobe.DbEventName {
	if e, ok := SwitchAlarmEventsOf(dt); ok {
		return e.Failure
	}
	return haprobe.DbEventNameMysqlSwitchFailureV1
}
