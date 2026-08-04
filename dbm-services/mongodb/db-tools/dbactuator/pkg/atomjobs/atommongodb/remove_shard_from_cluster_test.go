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

func TestIsMongoVersionBelow44(t *testing.T) {
	tests := []struct {
		name    string
		version string
		want    bool
		wantErr bool
	}{
		{name: "4.2", version: "4.2.21", want: true},
		{name: "mongodb-4.2", version: "mongodb-4.2", want: true},
		{name: "4.4", version: "4.4.18", want: false},
		{name: "5.0", version: "5.0.0", want: false},
		{name: "empty", version: "", wantErr: true},
		{name: "invalid", version: "abc", wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := isMongoVersionBelow44(tt.version)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("want error")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected err: %v", err)
			}
			if got != tt.want {
				t.Fatalf("want %v, got %v", tt.want, got)
			}
		})
	}
}

func TestFilterPrimaryDBsOnShards(t *testing.T) {
	dbs := []databasePrimary{
		{ID: "app", Primary: "shard-a"},
		{ID: "log", Primary: "shard-b"},
		{ID: "tmp", Primary: "shard-a"},
	}
	got := filterPrimaryDBsOnShards(dbs, []string{"shard-a"})
	if len(got) != 2 {
		t.Fatalf("want 2 dbs, got %d", len(got))
	}
	if got[0].ID != "app" || got[1].ID != "tmp" {
		t.Fatalf("unexpected dbs: %+v", got)
	}
}

func TestRemainingShards(t *testing.T) {
	got, err := remainingShards([]string{"shard-a", "shard-b", "shard-c"}, []string{"shard-a", "shard-c"})
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(got) != 1 || got[0] != "shard-b" {
		t.Fatalf("want [shard-b], got %v", got)
	}
	_, err = remainingShards([]string{"shard-a"}, []string{"shard-a"})
	if err == nil {
		t.Fatalf("want error when no remaining shard")
	}
}

func TestPickTargetShard(t *testing.T) {
	all := []string{"shard-a", "shard-b", "shard-c", "shard-d"}
	remove := []string{"shard-d"}
	// remaining: a,b,c — round-robin for 4 picks → a,b,c,a
	want := []string{"shard-a", "shard-b", "shard-c", "shard-a"}
	for i, w := range want {
		got, err := pickTargetShard(all, remove, i)
		if err != nil {
			t.Fatalf("i=%d unexpected err: %v", i, err)
		}
		if got != w {
			t.Fatalf("i=%d want %s, got %s", i, w, got)
		}
	}
	_, err := pickTargetShard([]string{"shard-a"}, []string{"shard-a"}, 0)
	if err == nil {
		t.Fatalf("want error when no remaining shard")
	}
}

func TestParseDatabasePrimaries(t *testing.T) {
	stdout := `[{"_id":"app","primary":"shard-a"},{"_id":"log","primary":"shard-b"}]`
	got, err := parseDatabasePrimaries(stdout)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(got) != 2 || got[0].ID != "app" || got[0].Primary != "shard-a" {
		t.Fatalf("unexpected result: %+v", got)
	}
}

func TestParseShardNameList(t *testing.T) {
	got, err := parseShardNameList(`["s1","s2"]`)
	if err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if len(got) != 2 || got[0] != "s1" || got[1] != "s2" {
		t.Fatalf("unexpected: %+v", got)
	}
}

func TestCheckMovePrimaryOK(t *testing.T) {
	if err := checkMovePrimaryOK(`{"ok":1}`); err != nil {
		t.Fatalf("unexpected err: %v", err)
	}
	if err := checkMovePrimaryOK(`{"ok":0,"errmsg":"boom"}`); err == nil {
		t.Fatalf("want error")
	}
	// empty stdout treated as OK; callers must verify via getDatabasePrimary
	if err := checkMovePrimaryOK(""); err != nil {
		t.Fatalf("empty stdout should be OK (legacy shell), got %v", err)
	}
}

func TestBalancerShouldWaitForBalance(t *testing.T) {
	trueVal := true
	falseVal := false
	cases := []struct {
		name string
		wait *bool
		want bool
	}{
		{name: "nil defaults true", wait: nil, want: true},
		{name: "explicit true", wait: &trueVal, want: true},
		{name: "explicit false", wait: &falseVal, want: false},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			b := &Balancer{ConfParams: &BalancerConfParams{WaitForBalance: tt.wait}}
			if got := b.shouldWaitForBalance(); got != tt.want {
				t.Fatalf("want %v, got %v", tt.want, got)
			}
		})
	}
}
