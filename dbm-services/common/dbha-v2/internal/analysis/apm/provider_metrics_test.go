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

// snapshotDbMetricsState restores the package-level registration state so a test
// can exercise a successful RegisterDbMetrics call without leaking state.
func snapshotDbMetricsState(t *testing.T) {
	t.Helper()
	dbMetricsMu.Lock()
	names := make(map[string]struct{}, len(dbMetricsByName))
	for k := range dbMetricsByName {
		names[k] = struct{}{}
	}
	ordered := append([]interface{}(nil), dbMetricsOrdered...)
	dbTypes := make(map[haprobe.DbType]struct{}, len(dbMetricsDbTypes))
	for k := range dbMetricsDbTypes {
		dbTypes[k] = struct{}{}
	}
	dbMetricsMu.Unlock()

	t.Cleanup(func() {
		dbMetricsMu.Lock()
		defer dbMetricsMu.Unlock()
		dbMetricsByName = names
		dbMetricsOrdered = ordered
		dbMetricsDbTypes = dbTypes
	})
}

// TestRegisterDbMetrics_ProviderOwnedMetricExample documents the extension point:
// a provider may still register metrics it owns exclusively, with the same
// validation rules (framework collision and cross-provider duplicate names).
func TestRegisterDbMetrics_ProviderOwnedMetricExample(t *testing.T) {
	snapshotDbMetricsState(t)

	metric := haapm.NewHaCounter("tmp_provider_owned_total", "example of a provider-owned metric")
	RegisterDbMetrics(haprobe.DbTypeMongo, metric)

	got := DbMetrics()
	if len(got) != 1 || got[0] != metric {
		t.Fatalf("DbMetrics() = %v, want the registered metric", got)
	}
	types := MetricRegisteredDbTypes()
	if len(types) != 1 || types[0] != haprobe.DbTypeMongo {
		t.Fatalf("MetricRegisteredDbTypes() = %v, want [mongo]", types)
	}

	defer func() {
		if recover() == nil {
			t.Fatal("expected panic on duplicate metric name")
		}
	}()
	RegisterDbMetrics(haprobe.DbTypeRedis,
		haapm.NewHaCounter("tmp_provider_owned_total", "duplicate"))
}

func TestDbMetrics_ReturnsCopy(t *testing.T) {
	snapshotDbMetricsState(t)
	RegisterDbMetrics(haprobe.DbTypeMongo,
		haapm.NewHaCounter("tmp_copy_check_total", "copy check"))

	a := DbMetrics()
	b := DbMetrics()
	if len(a) != 1 || len(b) != 1 {
		t.Fatalf("expected one metric, got %d and %d", len(a), len(b))
	}
	a[0] = nil
	if b[0] == nil {
		t.Fatal("DbMetrics should return a copy")
	}
}
