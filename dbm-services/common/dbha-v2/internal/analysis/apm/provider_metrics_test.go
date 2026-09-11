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

package apm

import (
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestFrameworkMetricNames_NonEmptyAndSorted(t *testing.T) {
	names := FrameworkMetricNames()
	if len(names) == 0 {
		t.Fatal("expected framework metric names")
	}
	for i := 1; i < len(names); i++ {
		if names[i-1] > names[i] {
			t.Fatalf("expected sorted names, got %v", names)
		}
	}
}

func TestRegisterDbMetrics_NilMetricPanicsWithReadableMessage(t *testing.T) {
	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected panic")
		}
		msg, ok := r.(string)
		if !ok {
			t.Fatalf("expected string panic, got %T", r)
		}
		if !strings.Contains(msg, "nil metric") {
			t.Fatalf("expected readable nil message, got %q", msg)
		}
	}()
	RegisterDbMetrics(haprobe.DbType("test_nil_metric"), (*haapm.HaCounter)(nil))
}

func TestRegisterDbMetrics_FrameworkCollisionPanics(t *testing.T) {
	before := len(DbMetrics())
	defer func() {
		r := recover()
		if r == nil {
			t.Fatal("expected panic")
		}
		if len(DbMetrics()) != before {
			t.Fatalf("expected no state change after panic, before=%d after=%d", before, len(DbMetrics()))
		}
	}()
	RegisterDbMetrics(haprobe.DbType("test_fw_collision"), ScanBusinessTotal)
}

func TestRegisterDbMetrics_InvalidDbTypePanics(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("expected panic")
		}
	}()
	RegisterDbMetrics(haprobe.DbTypeNone, haapm.NewHaCounter("tmp_invalid_dbtype_total", "tmp"))
}

func TestDbMetrics_ReturnsCopy(t *testing.T) {
	a := DbMetrics()
	b := DbMetrics()
	if len(a) != len(b) {
		t.Fatalf("length mismatch: %d vs %d", len(a), len(b))
	}
	if len(a) == 0 {
		return
	}
	a[0] = nil
	if b[0] == nil {
		t.Fatal("DbMetrics should return a copy")
	}
}
