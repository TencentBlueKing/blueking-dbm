package middleware_test

import (
	"testing"

	_ "dbm-services/common/db-resource/internal/controller/apply"
	_ "dbm-services/common/db-resource/internal/controller/manage"
	"dbm-services/common/db-resource/internal/middleware"
)

func hasPath(list []string, path string) bool {
	for _, item := range list {
		if item == path {
			return true
		}
	}
	return false
}

func TestImportResponseIsNotSkipped(t *testing.T) {
	if !hasPath(middleware.RequestBodyLoggerFilter.WhitelistUri, "/resource/import") {
		t.Fatal("import must insert a request log row")
	}
	if hasPath(middleware.ResponseSkipLoggerFilter.WhitelistUri, "/resource/import") {
		t.Fatal("import must write its own response")
	}
	for _, path := range []string{"/resource/list", "/resource/list/all", "/ping", "/metrics"} {
		if !hasPath(middleware.ResponseSkipLoggerFilter.WhitelistUri, path) {
			t.Fatalf("%s must skip response log", path)
		}
	}
}
