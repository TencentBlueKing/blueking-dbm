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
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestRegisterDnsSingleAddressGuard_Idempotent(t *testing.T) {
	mt := haprobe.DbmMetadataMachineType("test_dns_guard_idempotent")
	RegisterDnsSingleAddressGuard(mt)
	RegisterDnsSingleAddressGuard(mt)
	if !HasDnsSingleAddressGuard(mt) {
		t.Fatalf("expected machine type %s to be guarded", mt)
	}
}

func TestHasDnsSingleAddressGuard_Unregistered(t *testing.T) {
	mt := haprobe.DbmMetadataMachineType("test_dns_guard_missing")
	if HasDnsSingleAddressGuard(mt) {
		t.Fatalf("expected machine type %s not to be guarded", mt)
	}
}

func TestDnsSingleAddressGuardMachineTypes_Sorted(t *testing.T) {
	a := haprobe.DbmMetadataMachineType("test_dns_guard_sort_a")
	b := haprobe.DbmMetadataMachineType("test_dns_guard_sort_b")
	RegisterDnsSingleAddressGuard(b, a)
	types := DnsSingleAddressGuardMachineTypes()
	var idxA, idxB = -1, -1
	for i, mt := range types {
		if mt == a {
			idxA = i
		}
		if mt == b {
			idxB = i
		}
	}
	if idxA < 0 || idxB < 0 {
		t.Fatalf("expected both machine types in list, got %v", types)
	}
	if idxA > idxB {
		t.Fatalf("expected sorted order, got %v", types)
	}
}
