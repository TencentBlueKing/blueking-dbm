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

	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/dbtype"
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
