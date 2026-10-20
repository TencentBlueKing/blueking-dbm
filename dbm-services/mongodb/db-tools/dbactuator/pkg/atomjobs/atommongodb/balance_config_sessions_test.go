package atommongodb

import (
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"
)

func TestSessionsSplitUUID(t *testing.T) {
	cases := []struct {
		i    int
		uuid string
	}{
		{i: 1, uuid: "00400000-0000-0000-0000-000000000000"},
		{i: 2, uuid: "00800000-0000-0000-0000-000000000000"},
		{i: 512, uuid: "80000000-0000-0000-0000-000000000000"},
		{i: 1023, uuid: "ffc00000-0000-0000-0000-000000000000"},
	}
	for _, tc := range cases {
		if got := sessionsSplitUUID(tc.i); got != tc.uuid {
			t.Fatalf("sessionsSplitUUID(%d)=%s, want %s", tc.i, got, tc.uuid)
		}
	}
}

func TestSessionsBalanceConfig(t *testing.T) {
	cfg := sessionsBalanceConfig()
	for _, absent := range []string{`"waitMs"`, `"pollMs"`} {
		if strings.Contains(cfg, absent) {
			t.Fatalf("config still contains %s", absent)
		}
	}
	for _, want := range []string{
		`"ns":"config.system.sessions"`,
		`"targetChunks":1024`,
		`"splitRetries":3`,
		`"retryMs":2000`,
		`"sessionsWaitTimeoutMs":360000`,
		`"sessionsWaitIntervalMs":5000`,
		"00400000-0000-0000-0000-000000000000",
		"ffc00000-0000-0000-0000-000000000000",
	} {
		if !strings.Contains(cfg, want) {
			t.Fatalf("config missing %s", want)
		}
	}
}

func TestSessionsBalanceScriptRetriesAndReportsSplitFailures(t *testing.T) {
	for _, want := range []string{
		"function splitPointExists(uuid)",
		"function sessionsCollectionReady()",
		"function notShardedYet(res)",
		"Number(res.code) === 118",
		"function retryableSplitError(res)",
		"attempt <= cfg.splitRetries",
		"try {\n        last = db.adminCommand({split: ns, middle: {_id: {id: UUID(splitPoint)}}});\n      } catch (e) {\n        last = {ok: 0, code: e.code, errmsg: e.message || String(e)};",
		`print("split failed point=" + splitPoint + " attempt=" + attempt + " " + jstr(last));`,
		`fail("split failed points=" + jstr(splitFailures));`,
		`print("stop balancer before split/move");`,
		"sh.stopBalancer();",
		"waiting for \" + ns + \" to be created by config server",
		"cfg.sessionsWaitTimeoutMs",
		"cfg.sessionsWaitIntervalMs",
		`fail(ns + " was not created with an initial chunk within " + cfg.sessionsWaitTimeoutMs + "ms");`,
		"waiting for \" + ns + \" to become sharded, point=\" + splitPoint",
		`fail(ns + " is not sharded within " + cfg.sessionsWaitTimeoutMs + "ms");`,
		"attempt--;",
		"try {\n      last = db.adminCommand({moveChunk: ns, bounds: [chunks[c].min, chunks[c].max], to: dest});\n    } catch (e) {\n      last = {ok: 0, code: e.code, errmsg: e.message || String(e)};",
	} {
		if !strings.Contains(sessionsBalanceScript, want) {
			t.Fatalf("sessions balance script missing %s", want)
		}
	}
	for _, absent := range []string{
		"startBalancer(",
		"cfg.waitMs",
		"cfg.pollMs",
		"refreshLogicalSessionCacheNow",
	} {
		if strings.Contains(sessionsBalanceScript, absent) {
			t.Fatalf("sessions balance script still contains %s", absent)
		}
	}
}

func TestRetryStopBalancer(t *testing.T) {
	if err := retryStopBalancer(0, time.Second, func(time.Duration) {}, func() error { return nil }); err == nil {
		t.Fatal("expected error for non-positive attempts")
	}

	var sleeps []time.Duration
	calls := 0
	err := retryStopBalancer(3, 5*time.Second, func(d time.Duration) {
		sleeps = append(sleeps, d)
	}, func() error {
		calls++
		return errors.New("still running")
	})
	if err == nil {
		t.Fatal("expected error")
	}
	if calls != 3 {
		t.Fatalf("calls=%d, want 3", calls)
	}
	if len(sleeps) != 2 || sleeps[0] != 5*time.Second || sleeps[1] != 5*time.Second {
		t.Fatalf("sleeps=%v", sleeps)
	}

	sleeps = nil
	calls = 0
	err = retryStopBalancer(3, 5*time.Second, func(d time.Duration) {
		sleeps = append(sleeps, d)
	}, func() error {
		calls++
		if calls < 2 {
			return fmt.Errorf("transient")
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if calls != 2 {
		t.Fatalf("calls=%d, want 2", calls)
	}
	if len(sleeps) != 1 || sleeps[0] != 5*time.Second {
		t.Fatalf("sleeps=%v", sleeps)
	}
}

func TestMongodbMajorVersion(t *testing.T) {
	cases := []struct {
		version string
		major   int
		ok      bool
	}{
		{version: "6.0.4", major: 6, ok: true},
		{version: "6.0", major: 6, ok: true},
		{version: "mongodb-7.0.28", major: 7, ok: true},
		{version: "MongoDB-5.0.14", major: 5, ok: true},
		{version: "4.4.29", major: 4, ok: true},
		{version: "", ok: false},
		{version: "not-a-version", ok: false},
	}
	for _, tc := range cases {
		major, err := mongodbMajorVersion(tc.version)
		if tc.ok != (err == nil) {
			t.Fatalf("mongodbMajorVersion(%q) err=%v, want ok=%t", tc.version, err, tc.ok)
		}
		if tc.ok && major != tc.major {
			t.Fatalf("mongodbMajorVersion(%q)=%d, want %d", tc.version, major, tc.major)
		}
	}
}
