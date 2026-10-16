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

package mysqlparse

import (
	"encoding/json"
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/internal/analysis/parser"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Verifies this package's own init registration; the allanalysis aggregation
// path is covered by workflow.TestAnalysisProvidersRegisterMySQLParser.
func TestMySQLProcesserRegistered(t *testing.T) {
	p, ok := parser.Lookup(haprobe.DbTypeMySql)
	if !ok || p == nil {
		t.Fatal("mysql processer not registered via mysqlparse init")
	}
}

func TestStatusProcessInvalidJSON(t *testing.T) {
	var s Status
	_, err := s.Process(json.RawMessage(`{not-json`))
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
	if !errors.Is(err, errInvalidMySqlStatus) || err.Error() != errInvalidMySqlStatus.Error() {
		t.Fatalf("unexpected errmsg: %s", err)
	}
}

func TestStatusProcessValidJSON(t *testing.T) {
	var s Status
	event, err := s.Process(json.RawMessage(`{}`))
	if err != nil {
		t.Fatalf("unexpected errmsg: %s", err)
	}
	if event != nil {
		t.Fatalf("expected nil event for stub Process, got: %#v", event)
	}
}
