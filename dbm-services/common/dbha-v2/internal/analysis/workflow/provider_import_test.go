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

package workflow_test

import (
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/failure"
	"dbm-services/common/dbha-v2/internal/analysis/parser"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	_ "dbm-services/common/dbha-v2/internal/provider/allanalysis"
)

func TestAnalysisProvidersRegisterMySQLSwitcher(t *testing.T) {
	built := switcher.Build()
	sw, ok := built[haprobe.DbTypeMySql]
	if !ok || sw == nil {
		t.Fatal("expected MySQL switcher registered via allanalysis")
	}
	if sw.DbTypeName() != haprobe.DbTypeMySql {
		t.Errorf("DbTypeName = %s, want mysql", sw.DbTypeName())
	}

	if got := dbtype.SwitchSuccessEventName(haprobe.DbTypeMySql); got != haprobe.DbEventNameMysqlSwitchSuccessV1 {
		t.Errorf("success event = %s, want %s", got, haprobe.DbEventNameMysqlSwitchSuccessV1)
	}
	if got := dbtype.SwitchFailureEventName(haprobe.DbTypeMySql); got != haprobe.DbEventNameMysqlSwitchFailureV1 {
		t.Errorf("failure event = %s, want %s", got, haprobe.DbEventNameMysqlSwitchFailureV1)
	}
}

func TestAnalysisProvidersRegisterMySQLParser(t *testing.T) {
	p, ok := parser.Lookup(haprobe.DbTypeMySql)
	if !ok || p == nil {
		t.Fatal("expected MySQL processer registered via allanalysis")
	}
}

func TestAnalysisProvidersRegisterSpecialMatchAndDnsGuard(t *testing.T) {
	events := failure.RegisteredSpecialMatchEvents()
	wantEvents := map[haprobe.DbEventName]bool{
		haprobe.DbEventNameTendbhaProxyBackendFailure:      false,
		haprobe.DbEventNameTendbclusterSpiderRemoteFailure: false,
	}
	for _, e := range events {
		if _, ok := wantEvents[e]; ok {
			wantEvents[e] = true
		}
	}
	for e, ok := range wantEvents {
		if !ok {
			t.Errorf("expected special match event %s registered", e)
		}
	}

	if !dbtype.HasDnsSingleAddressGuard(haprobe.DbmMetadataMachineTypeProxy) {
		t.Error("expected proxy machine type in DNS single-address guard")
	}
	if !dbtype.HasDnsSingleAddressGuard(haprobe.DbmMetadataMachineTypeSpider) {
		t.Error("expected spider machine type in DNS single-address guard")
	}
}

func TestAnalysisProvidersRegisterDbMetrics(t *testing.T) {
	types := apm.MetricRegisteredDbTypes()
	wantTypes := map[haprobe.DbType]bool{
		haprobe.DbTypeMySql: false,
		haprobe.DbTypeRedis: false,
	}
	for _, dt := range types {
		if _, ok := wantTypes[dt]; ok {
			wantTypes[dt] = true
		}
	}
	for dt, ok := range wantTypes {
		if !ok {
			t.Errorf("expected metric DbType %s registered", dt)
		}
	}

	fw := map[string]struct{}{}
	for _, name := range apm.FrameworkMetricNames() {
		fw[name] = struct{}{}
	}
	for _, m := range apm.DbMetrics() {
		getter, ok := m.(haapm.MetricGetter)
		if !ok {
			t.Fatalf("expected MetricGetter, got %T", m)
		}
		name := getter.ToMetric().Name
		if _, collides := fw[name]; collides {
			t.Errorf("provider metric %q collides with framework metric", name)
		}
	}
}
