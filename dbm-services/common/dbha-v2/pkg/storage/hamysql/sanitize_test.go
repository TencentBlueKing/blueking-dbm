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

package hamysql_test

import (
	"errors"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

func TestSanitizeConnectionError_nil(t *testing.T) {
	if got := hamysql.SanitizeConnectionError(nil); got != "" {
		t.Fatalf("got %q, want empty", got)
	}
}

func TestSanitizeConnectionError_dsnCredential(t *testing.T) {
	err := errors.New("dial tcp: probe:SecretPass@tcp(1.2.3.4:3306)/: connect: connection refused")
	got := hamysql.SanitizeConnectionError(err)
	if strings.Contains(got, "SecretPass") {
		t.Fatalf("password leaked in %q", got)
	}
	if !strings.Contains(got, sanitizedSecretOrRedacted(got)) {
		t.Fatalf("expected redaction marker in %q", got)
	}
}

func TestSanitizeConnectionError_mysqlAccessDenied(t *testing.T) {
	err := errors.New("Error 1045: Access denied for user 'u'@'h' (using password: YES)")
	got := hamysql.SanitizeConnectionError(err)
	if got != err.Error() {
		t.Fatalf("got %q, want unchanged access denied message", got)
	}
}

func TestSanitizeConnectionError_sensitiveQueryParam(t *testing.T) {
	err := errors.New("invalid config password=SuperSecret&charset=utf8")
	got := hamysql.SanitizeConnectionError(err)
	if strings.Contains(got, "SuperSecret") {
		t.Fatalf("password leaked in %q", got)
	}
	if !strings.Contains(got, "<secret>") {
		t.Fatalf("expected <secret> in %q", got)
	}
}

func TestSanitizeConnectionError_truncatesLongMessage(t *testing.T) {
	long := strings.Repeat("a", 300)
	err := errors.New(long)
	got := hamysql.SanitizeConnectionError(err)
	if len(got) != 256 {
		t.Fatalf("len(got)=%d, want 256", len(got))
	}
}

func sanitizedSecretOrRedacted(msg string) string {
	if strings.Contains(msg, "<secret>") {
		return "<secret>"
	}
	return "<redacted-dsn>"
}
