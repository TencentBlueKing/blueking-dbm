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
