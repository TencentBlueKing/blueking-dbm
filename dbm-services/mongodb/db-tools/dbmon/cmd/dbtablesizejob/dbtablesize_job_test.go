package dbtablesizejob

import "testing"

func TestShouldSkipCollection(t *testing.T) {
	cases := []struct {
		name     string
		db       string
		coll     string
		dataSize int64
		wantSkip bool
	}{
		{name: "heartbeat_small", db: "test", coll: "dbmon_heartbeat", dataSize: 100, wantSkip: true},
		{name: "heartbeat_just_under_1m", db: "test", coll: "dbmon_heartbeat", dataSize: skipHeartbeatMaxBytes - 1, wantSkip: true},
		{name: "heartbeat_exact_1m", db: "test", coll: "dbmon_heartbeat", dataSize: skipHeartbeatMaxBytes, wantSkip: false},
		{name: "heartbeat_large", db: "test", coll: "dbmon_heartbeat", dataSize: skipHeartbeatMaxBytes + 1, wantSkip: false},
		{name: "other_coll", db: "test", coll: "other", dataSize: 100, wantSkip: false},
		{name: "other_db", db: "admin", coll: "dbmon_heartbeat", dataSize: 100, wantSkip: false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := shouldSkipCollection(c.db, c.coll, c.dataSize)
			if got != c.wantSkip {
				t.Fatalf("shouldSkipCollection(%q,%q,%d)=%v, want %v",
					c.db, c.coll, c.dataSize, got, c.wantSkip)
			}
		})
	}
}
