package atommongodb

import "testing"

func TestShouldSkipEnsureStart(t *testing.T) {
	t.Parallel()
	if !shouldSkipEnsureStart(true) {
		t.Fatal("running instance must skip ensure_start")
	}
	if shouldSkipEnsureStart(false) {
		t.Fatal("not running instance must not skip ensure_start")
	}
}

func TestRetryEnsureStart(t *testing.T) {
	t.Parallel()
	job := &instOpJob{ConfParams: &instOpParams{Op: "ensure_start"}}
	if got := job.Retry(); got != 3 {
		t.Fatalf("ensure_start Retry() = %d, want 3", got)
	}
}
