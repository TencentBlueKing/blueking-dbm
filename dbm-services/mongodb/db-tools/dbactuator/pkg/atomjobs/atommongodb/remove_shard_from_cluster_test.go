package atommongodb

import (
	"testing"
)

func TestParseRemoveShardResultCompleted(t *testing.T) {
	stdout := `{"ok":1,"msg":"removeshard completed successfully","state":"completed","shard":"demo-s3"}`
	result, err := parseRemoveShardResult(stdout)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if result.State != "completed" {
		t.Fatalf("want completed, got %s", result.State)
	}
}

func TestParseRemoveShardResultOngoing(t *testing.T) {
	stdout := `{"ok" : 1, "msg" : "draining ongoing...", "state" : "ongoing", "shard" : "demo-s3", "remaining" : { "chunks" : 12, "dbs" : 0 }}`
	result, err := parseRemoveShardResult(stdout)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if result.State != "ongoing" {
		t.Fatalf("want ongoing, got %s", result.State)
	}
	if result.Remaining == nil || result.Remaining.Chunks != 12 {
		t.Fatalf("want remaining.chunks=12, got %+v", result.Remaining)
	}
}

func TestParseShardCount(t *testing.T) {
	tests := []struct {
		name    string
		stdout  string
		want    int
		wantErr bool
	}{
		{name: "absent", stdout: "0\n", want: 0},
		{name: "exists", stdout: "1\n", want: 1},
		{name: "last non-empty line", stdout: "warning\n\n0\n", want: 0},
		{name: "invalid", stdout: "not-a-count\n", wantErr: true},
		{name: "empty", stdout: "\n", wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseShardCount(tt.stdout)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("want error, got count %d", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected err: %v", err)
			}
			if got != tt.want {
				t.Fatalf("want %d, got %d", tt.want, got)
			}
		})
	}
}
