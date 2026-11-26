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

// Package detection provides the registry of DbTypes onboarded for failure
// detection in the analysis process.
package detection

import (
	"fmt"
	"sort"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Detectable is the capability marker a provider registers for one DbType.
// It declares that instances of this DbType may enter the business scan.
// Future per-DbType detection policies can extend this interface.
type Detectable interface {
	DbTypeName() haprobe.DbType
}

var (
	mu          sync.RWMutex
	detectables = map[haprobe.DbType]Detectable{}
)

// Register registers a detection capability for a DbType. Panics on invalid,
// duplicate, or nil registration.
func Register(dbType haprobe.DbType, d Detectable) {
	if dbType == haprobe.DbTypeNone || dbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("detection: refuse to register invalid DbType: %q", dbType))
	}
	if d == nil {
		panic(fmt.Sprintf("detection: refuse to register nil Detectable for DbType: %s", dbType))
	}

	mu.Lock()
	defer mu.Unlock()
	if _, exists := detectables[dbType]; exists {
		panic(fmt.Sprintf("detection: duplicate DbType registration: %s", dbType))
	}
	detectables[dbType] = d
}

// Lookup returns the registered Detectable for a DbType, if any.
func Lookup(dbType haprobe.DbType) (Detectable, bool) {
	mu.RLock()
	defer mu.RUnlock()
	d, ok := detectables[dbType]
	return d, ok
}

// RegisteredDbTypes returns all onboarded DbTypes, sorted, for startup self-check.
func RegisteredDbTypes() []haprobe.DbType {
	mu.RLock()
	defer mu.RUnlock()
	out := make([]haprobe.DbType, 0, len(detectables))
	for dt := range detectables {
		out = append(out, dt)
	}
	sort.Slice(out, func(i, j int) bool { return string(out[i]) < string(out[j]) })
	return out
}

// Validate reports an error when a registered Detectable does not match its key.
func Validate() error {
	mu.RLock()
	defer mu.RUnlock()
	for dt, d := range detectables {
		if d.DbTypeName() != dt {
			return fmt.Errorf("detection: DbType %s has mismatched Detectable %s", dt, d.DbTypeName())
		}
	}
	return nil
}
