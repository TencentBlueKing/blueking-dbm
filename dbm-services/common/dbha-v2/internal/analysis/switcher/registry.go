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

package switcher

import (
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Constructor creates a Switcher instance.
type Constructor func() Switcher

var (
	switcherMu    sync.RWMutex
	switcherCtors = map[haprobe.DbType]Constructor{}
)

// Register registers a switcher constructor for a DbType. Panics on duplicate.
func Register(dbType haprobe.DbType, ctor Constructor) {
	if dbType == haprobe.DbTypeNone || dbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("switcher: refuse to register invalid DbType: %q", dbType))
	}
	if ctor == nil {
		panic(fmt.Sprintf("switcher: refuse to register nil constructor for DbType: %s", dbType))
	}

	switcherMu.Lock()
	defer switcherMu.Unlock()

	if _, exists := switcherCtors[dbType]; exists {
		panic(fmt.Sprintf("switcher: duplicate DbType registration: %s", dbType))
	}
	switcherCtors[dbType] = ctor
}

// Build constructs a map of all registered switchers (one instance per DbType).
func Build() map[haprobe.DbType]Switcher {
	switcherMu.RLock()
	ctors := make(map[haprobe.DbType]Constructor, len(switcherCtors))
	for dt, ctor := range switcherCtors {
		ctors[dt] = ctor
	}
	switcherMu.RUnlock()

	out := make(map[haprobe.DbType]Switcher, len(ctors))
	for dt, ctor := range ctors {
		out[dt] = ctor()
	}
	return out
}

// RegisteredDbTypes returns all registered switcher DbTypes (unordered).
func RegisteredDbTypes() []haprobe.DbType {
	switcherMu.RLock()
	defer switcherMu.RUnlock()
	out := make([]haprobe.DbType, 0, len(switcherCtors))
	for dt := range switcherCtors {
		out = append(out, dt)
	}
	return out
}

// Validate reports an error when any registered switcher DbType lacks switch alarm events.
func Validate() error {
	for _, dt := range RegisteredDbTypes() {
		if _, ok := dbtype.SwitchAlarmEventsOf(dt); !ok {
			return fmt.Errorf("switcher: DbType %s has no switch alarm events registered", dt)
		}
	}
	return nil
}
