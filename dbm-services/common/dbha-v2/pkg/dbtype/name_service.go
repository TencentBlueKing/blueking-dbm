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
	"sort"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	dnsGuardMu        sync.RWMutex
	dnsGuardByMachine = map[haprobe.DbmMetadataMachineType]struct{}{}
)

// RegisterDnsSingleAddressGuard marks machine types whose DNS entry must not be
// released when the domain has only one remaining address.
//
// Unlike RegisterSwitchAlarmEvents, re-registering the same machine type is
// idempotent rather than a panic: this is a set of guarded types, not a
// one-owner mapping, so two providers guarding the same machine type is a
// consistent statement rather than a conflict.
func RegisterDnsSingleAddressGuard(machineTypes ...haprobe.DbmMetadataMachineType) {
	dnsGuardMu.Lock()
	defer dnsGuardMu.Unlock()
	for _, mt := range machineTypes {
		dnsGuardByMachine[mt] = struct{}{}
	}
}

// HasDnsSingleAddressGuard reports whether the machine type is guarded.
func HasDnsSingleAddressGuard(mt haprobe.DbmMetadataMachineType) bool {
	dnsGuardMu.RLock()
	defer dnsGuardMu.RUnlock()
	_, ok := dnsGuardByMachine[mt]
	return ok
}

// DnsSingleAddressGuardMachineTypes returns guarded machine types in sorted order,
// used by the analysis startup self-check log.
func DnsSingleAddressGuardMachineTypes() []haprobe.DbmMetadataMachineType {
	dnsGuardMu.RLock()
	defer dnsGuardMu.RUnlock()

	out := make([]haprobe.DbmMetadataMachineType, 0, len(dnsGuardByMachine))
	for mt := range dnsGuardByMachine {
		out = append(out, mt)
	}
	sort.Slice(out, func(i, j int) bool {
		return string(out[i]) < string(out[j])
	})
	return out
}
