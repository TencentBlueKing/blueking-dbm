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

package workflow

import (
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	testBkBizID     = 100
	testBkCloudID   = 1
	testIP          = "127.0.0.1"
	testPort        = 3306
	testReportedTTL = 10 * time.Minute
	testEventA      = haprobe.DbEventNameDetectFailure
	testEventB      = haprobe.DbEventNameSshAuthFailure
	testMysqlDbType = haprobe.DbTypeMySql
	testRedisDbType = haprobe.DbTypeRedis
)

func newReportedTestInstance(event haprobe.DbEventName, port int) FailureInstanceInfo {
	return FailureInstanceInfo{
		BkBizID:   testBkBizID,
		BkCloudID: testBkCloudID,
		IP:        testIP,
		Port:      port,
		DbType:    testMysqlDbType,
		EventName: event,
	}
}

func reportedTestKey(port int, dbType haprobe.DbType) string {
	return reportCacheKey(testBkBizID, testBkCloudID, testIP, port, dbType)
}

func TestReportCacheKeyDimensions(t *testing.T) {
	base := reportedTestKey(testPort, testMysqlDbType)
	if got := reportCacheKey(testBkBizID, testBkCloudID, testIP, testPort, testMysqlDbType); got != base {
		t.Fatalf("same dimensions produced different keys: %s vs %s", got, base)
	}

	variants := map[string]string{
		"bkBizID":   reportCacheKey(testBkBizID+1, testBkCloudID, testIP, testPort, testMysqlDbType),
		"bkCloudID": reportCacheKey(testBkBizID, testBkCloudID+1, testIP, testPort, testMysqlDbType),
		"ip":        reportCacheKey(testBkBizID, testBkCloudID, "127.0.0.2", testPort, testMysqlDbType),
		"port":      reportCacheKey(testBkBizID, testBkCloudID, testIP, testPort+1, testMysqlDbType),
		"dbType":    reportedTestKey(testPort, testRedisDbType),
	}
	seen := map[string]bool{base: true}
	for name, key := range variants {
		if seen[key] {
			t.Errorf("%s produced a duplicate key: %s", name, key)
		}
		seen[key] = true
	}
	if len(seen) != len(variants)+1 {
		t.Fatalf("expected %d distinct keys, got %d", len(variants)+1, len(seen))
	}
}

func TestCheckRecentReportReasons(t *testing.T) {
	now := time.Now()
	key := reportedTestKey(testPort, testMysqlDbType)
	inst := newReportedTestInstance(testEventA, testPort)

	t.Run("no_key", func(t *testing.T) {
		cache := NewReportedInstanceCache()
		skip, info := cache.CheckRecentReport(&inst)
		if skip || info.Reason != reportReasonNoKey {
			t.Fatalf("skip=%v reason=%s, want false/%s", skip, info.Reason, reportReasonNoKey)
		}
		if info.Inst != key || info.Source != reportSourceCache {
			t.Fatalf("unexpected info: inst=%s source=%s", info.Inst, info.Source)
		}
	})

	t.Run("hit_does_not_refresh", func(t *testing.T) {
		cache := NewReportedInstanceCache()
		cache.MarkReported(map[string]ReportCacheEntry{
			key: {EventName: testEventA, SetAt: now, ExpireAt: now.Add(testReportedTTL)},
		}, now)
		skip, info := cache.CheckRecentReport(&inst)
		if !skip || info.Reason != reportReasonHit || info.Remaining <= 0 {
			t.Fatalf("skip=%v reason=%s remaining=%s, want true/%s/>0",
				skip, info.Reason, info.Remaining, reportReasonHit)
		}
		if !info.SetAt.Equal(now) || !info.ExpireAt.Equal(now.Add(testReportedTTL)) {
			t.Fatalf("unexpected window: setAt=%s expireAt=%s", info.SetAt, info.ExpireAt)
		}
		_, second := cache.CheckRecentReport(&inst)
		if !second.SetAt.Equal(info.SetAt) || !second.ExpireAt.Equal(info.ExpireAt) {
			t.Fatal("a hit must not refresh the cached entry")
		}
	})

	t.Run("expired_removes_entry", func(t *testing.T) {
		cache := NewReportedInstanceCache()
		cache.entries[key] = ReportCacheEntry{
			EventName: testEventA,
			SetAt:     now.Add(-2 * testReportedTTL),
			ExpireAt:  now.Add(-time.Second),
		}
		skip, info := cache.CheckRecentReport(&inst)
		if skip || info.Reason != reportReasonExpired {
			t.Fatalf("skip=%v reason=%s, want false/%s", skip, info.Reason, reportReasonExpired)
		}
		if _, ok := cache.entries[key]; ok {
			t.Fatal("expired entry was not removed lazily")
		}
	})

	t.Run("event_changed", func(t *testing.T) {
		cache := NewReportedInstanceCache()
		cache.MarkReported(map[string]ReportCacheEntry{
			key: {EventName: testEventA, SetAt: now, ExpireAt: now.Add(testReportedTTL)},
		}, now)
		changed := newReportedTestInstance(testEventB, testPort)
		skip, info := cache.CheckRecentReport(&changed)
		if skip || info.Reason != reportReasonEventChanged || info.CachedEvent != testEventA {
			t.Fatalf("skip=%v reason=%s cachedEvent=%s, want false/%s/%s",
				skip, info.Reason, info.CachedEvent, reportReasonEventChanged, testEventA)
		}
	})
}

func TestMarkReportedRemovesExpiredEntries(t *testing.T) {
	now := time.Now()
	expiredKey := reportedTestKey(testPort, testMysqlDbType)
	liveKey := reportedTestKey(testPort+1, testMysqlDbType)
	newKey := reportedTestKey(testPort+2, testMysqlDbType)
	cache := NewReportedInstanceCache()

	cache.entries[expiredKey] = ReportCacheEntry{
		EventName: testEventA,
		SetAt:     now.Add(-2 * testReportedTTL),
		ExpireAt:  now.Add(-time.Second),
	}
	cache.entries[liveKey] = ReportCacheEntry{
		EventName: testEventA,
		SetAt:     now,
		ExpireAt:  now.Add(testReportedTTL),
	}

	cache.MarkReported(map[string]ReportCacheEntry{
		newKey: {EventName: testEventB, SetAt: now, ExpireAt: now.Add(testReportedTTL)},
	}, now)

	if _, ok := cache.entries[expiredKey]; ok {
		t.Fatal("expired entry was not removed by MarkReported")
	}
	if _, ok := cache.entries[liveKey]; !ok {
		t.Fatal("live entry must be kept")
	}
	if cache.entries[newKey].EventName != testEventB {
		t.Fatal("new entry was not stored")
	}
	if len(cache.entries) != 2 {
		t.Fatalf("expected 2 entries after cleanup, got %d", len(cache.entries))
	}
}

func TestMarkReportedEntries(t *testing.T) {
	now := time.Now()
	keyA := reportedTestKey(testPort, testMysqlDbType)
	keyB := reportedTestKey(testPort+1, testMysqlDbType)
	setA := now.Add(-time.Minute)
	setB := now.Add(-2 * time.Minute)
	cache := NewReportedInstanceCache()

	cache.MarkReported(map[string]ReportCacheEntry{
		keyA: {EventName: testEventA, SetAt: setA, ExpireAt: setA.Add(testReportedTTL)},
		keyB: {EventName: testEventB, SetAt: setB, ExpireAt: setB.Add(testReportedTTL)},
	}, now)
	if len(cache.entries) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(cache.entries))
	}
	if cache.entries[keyA].EventName != testEventA || !cache.entries[keyA].SetAt.Equal(setA) {
		t.Fatal("entry A was not stored as provided")
	}
	if cache.entries[keyB].EventName != testEventB || !cache.entries[keyB].ExpireAt.Equal(setB.Add(testReportedTTL)) {
		t.Fatal("entry B was not stored as provided")
	}

	cache.MarkReported(map[string]ReportCacheEntry{
		keyA: {EventName: testEventB, SetAt: now, ExpireAt: now.Add(testReportedTTL)},
	}, now)
	if cache.entries[keyA].EventName != testEventB || !cache.entries[keyA].SetAt.Equal(now) {
		t.Fatal("MarkReported must overwrite an existing entry")
	}
	if !cache.entries[keyB].SetAt.Equal(setB) {
		t.Fatal("MarkReported must not touch unrelated entries")
	}
}

func TestMatchReportedEvent(t *testing.T) {
	cases := []struct {
		name   string
		record haprobe.DbEventName
		event  haprobe.DbEventName
		want   bool
	}{
		{"both_empty", "", "", true},
		{"empty_vs_failure", "", testEventA, false},
		{"failure_vs_empty", testEventA, "", false},
		{"same_failure", testEventA, testEventA, true},
		{"different_failure", testEventA, testEventB, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := matchReportedEvent(reportedSnapshotInstance{EventName: tc.record}, tc.event)
			if got != tc.want {
				t.Fatalf("matchReportedEvent(%q, %q) = %v, want %v", tc.record, tc.event, got, tc.want)
			}
		})
	}
}

func TestBuildReportEventsForInstances(t *testing.T) {
	instances := []FailureInstanceInfo{
		newReportedTestInstance(testEventA, testPort),
		newReportedTestInstance(testEventB, testPort+1),
	}
	events := buildReportEventsForInstances(testBkBizID, testMysqlDbType, instances)
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}
	if events[reportedTestKey(testPort, testMysqlDbType)] != testEventA ||
		events[reportedTestKey(testPort+1, testMysqlDbType)] != testEventB {
		t.Fatalf("unexpected events: %v", events)
	}
	if _, ok := events[reportedTestKey(testPort, testRedisDbType)]; ok {
		t.Fatal("a different dbType must not collide with the mysql key")
	}
}

func TestBuildReportEventsForMetas(t *testing.T) {
	group := &FailureGroup{Instances: []FailureInstanceInfo{
		newReportedTestInstance(testEventA, testPort),
		newReportedTestInstance(testEventB, testPort+1),
	}}
	metas := []*dbm.DbInstMetadata{
		{BkBizID: testBkBizID, BkCloudID: testBkCloudID, IP: testIP, Port: testPort},
		{BkBizID: testBkBizID, BkCloudID: testBkCloudID, IP: testIP, Port: testPort + 1},
		{BkBizID: testBkBizID, BkCloudID: testBkCloudID, IP: testIP, Port: testPort + 2},
	}
	events := buildReportEventsForMetas(testBkBizID, testMysqlDbType, group, metas)
	if len(events) != 3 {
		t.Fatalf("expected 3 events, got %d", len(events))
	}
	if events[reportedTestKey(testPort, testMysqlDbType)] != testEventA ||
		events[reportedTestKey(testPort+1, testMysqlDbType)] != testEventB {
		t.Fatalf("failure group events were not mapped: %v", events)
	}
	if got := events[reportedTestKey(testPort+2, testMysqlDbType)]; got != "" {
		t.Fatalf("linked instance without its own failure must keep an empty event, got %q", got)
	}
}

func TestBuildReportEntries(t *testing.T) {
	now := time.Now()
	start := now.Add(-3 * time.Minute)
	ttl := reportedInstanceTTL()
	keyMatch := reportedTestKey(testPort, testMysqlDbType)
	keyChanged := reportedTestKey(testPort+1, testMysqlDbType)
	keyNew := reportedTestKey(testPort+2, testMysqlDbType)

	reported := map[string]reportedSnapshotInstance{
		keyMatch:   {EventName: testEventA, StartTime: start, TTL: ttl},
		keyChanged: {EventName: testEventA, StartTime: start, TTL: ttl},
	}
	reportEvents := map[string]haprobe.DbEventName{
		keyMatch:   testEventA,
		keyChanged: testEventB,
		keyNew:     testEventA,
	}
	entries := buildReportEntries(reportEvents, reported, now)
	if len(entries) != 3 {
		t.Fatalf("expected 3 entries, got %d", len(entries))
	}
	if !entries[keyMatch].SetAt.Equal(start) || !entries[keyMatch].ExpireAt.Equal(start.Add(ttl)) {
		t.Fatal("a matching event must inherit the snapshot log window")
	}
	for _, key := range []string{keyChanged, keyNew} {
		if !entries[key].SetAt.Equal(now) || !entries[key].ExpireAt.Equal(now.Add(ttl)) {
			t.Fatalf("entry %s must start a fresh window from now", key)
		}
	}
}

func TestExcludeAlreadyReportedForInstances(t *testing.T) {
	now := time.Now()
	keyMatch := reportedTestKey(testPort, testMysqlDbType)
	keyChanged := reportedTestKey(testPort+1, testMysqlDbType)
	keyNew := reportedTestKey(testPort+2, testMysqlDbType)
	instances := []FailureInstanceInfo{
		newReportedTestInstance(testEventA, testPort),
		newReportedTestInstance(testEventB, testPort+1),
		newReportedTestInstance(testEventA, testPort+2),
	}
	reported := map[string]reportedSnapshotInstance{
		keyMatch:   {EventName: testEventA, StartTime: now, TTL: testReportedTTL},
		keyChanged: {EventName: testEventA, StartTime: now, TTL: testReportedTTL},
	}
	reportEvents := map[string]haprobe.DbEventName{
		keyMatch:   testEventA,
		keyChanged: testEventB,
		keyNew:     testEventA,
	}

	got := excludeAlreadyReportedForInstances(
		testBkBizID, testMysqlDbType, instances, reported, reportEvents)
	if len(got) != 2 {
		t.Fatalf("expected 2 instances to report, got %d", len(got))
	}
	if got[0].Port != testPort+1 || got[1].Port != testPort+2 {
		t.Fatalf("changed and never-reported instances must be kept, got ports %d/%d",
			got[0].Port, got[1].Port)
	}
}

func TestExcludeAlreadyReportedForMetas(t *testing.T) {
	now := time.Now()
	keyMatch := reportedTestKey(testPort, testMysqlDbType)
	keyChanged := reportedTestKey(testPort+1, testMysqlDbType)
	keyNew := reportedTestKey(testPort+2, testMysqlDbType)
	metas := []*dbm.DbInstMetadata{
		{BkBizID: testBkBizID, BkCloudID: testBkCloudID, IP: testIP, Port: testPort},
		{BkBizID: testBkBizID, BkCloudID: testBkCloudID, IP: testIP, Port: testPort + 1},
		{BkBizID: testBkBizID, BkCloudID: testBkCloudID, IP: testIP, Port: testPort + 2},
	}
	reported := map[string]reportedSnapshotInstance{
		keyMatch:   {EventName: testEventA, StartTime: now, TTL: testReportedTTL},
		keyChanged: {EventName: testEventA, StartTime: now, TTL: testReportedTTL},
	}
	reportEvents := map[string]haprobe.DbEventName{
		keyMatch:   testEventA,
		keyChanged: testEventB,
		keyNew:     testEventA,
	}

	got := excludeAlreadyReportedForMetas(
		testBkBizID, testMysqlDbType, metas, reported, reportEvents)
	if len(got) != 2 {
		t.Fatalf("expected 2 metas to report, got %d", len(got))
	}
	if got[0].Port != testPort+1 || got[1].Port != testPort+2 {
		t.Fatalf("changed and never-reported metas must be kept, got ports %d/%d",
			got[0].Port, got[1].Port)
	}
}
