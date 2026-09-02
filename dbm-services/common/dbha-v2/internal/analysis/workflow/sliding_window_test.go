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
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func newFailureInstanceForWindow(ip string, port int, dbType haprobe.DbType) *FailureInstanceInfo {
	return &FailureInstanceInfo{
		BkCloudID: 1,
		IP:        ip,
		Port:      port,
		BkBizID:   100,
		DbType:    dbType,
	}
}

func newFailureEventForWindow(ip string, port int, dbType haprobe.DbType, event haprobe.DbEventName) *FailureInstanceInfo {
	inst := newFailureInstanceForWindow(ip, port, dbType)
	inst.EventName = event
	return inst
}

func TestBizWindowManager_PushMergeAndPop(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	inst := newFailureInstanceForWindow("127.0.0.1", 3306, haprobe.DbTypeMySql)
	base := time.Now()

	if !mgr.Push(100, inst, base) {
		t.Fatal("first push should be accepted")
	}
	if !mgr.Push(100, inst, base.Add(time.Second)) {
		t.Fatal("second push should be accepted and merged")
	}

	entries := mgr.Pop(100, base.Add(11*time.Second))
	if len(entries) != 1 {
		t.Fatalf("expected 1 merged entry, got %d", len(entries))
	}
	if entries[0].Count != 2 {
		t.Fatalf("expected merged count=2, got %d", entries[0].Count)
	}
}

func TestBizWindowManager_BizIsolation(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	inst := newFailureInstanceForWindow("127.0.0.2", 3306, haprobe.DbTypeMySql)
	base := time.Now()

	if !mgr.Push(100, inst, base) {
		t.Fatal("push for biz=100 should succeed")
	}
	if !mgr.Push(200, inst, base) {
		t.Fatal("push for biz=200 should succeed")
	}

	entries100 := mgr.Pop(100, base.Add(11*time.Second))
	if len(entries100) != 1 {
		t.Fatalf("expected 1 entry for biz=100, got %d", len(entries100))
	}

	entries200 := mgr.Pop(200, base.Add(11*time.Second))
	if len(entries200) != 1 {
		t.Fatalf("expected 1 entry for biz=200, got %d", len(entries200))
	}
}

func TestBizWindowManager_PopBoundary(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	inst := newFailureInstanceForWindow("127.0.0.3", 3306, haprobe.DbTypeMySql)
	base := time.Now()

	if !mgr.Push(100, inst, base) {
		t.Fatal("push should succeed")
	}

	entries := mgr.Pop(100, base.Add(10*time.Second))
	if len(entries) != 0 {
		t.Fatalf("expected no pop at exact boundary, got %d", len(entries))
	}

	entries = mgr.Pop(100, base.Add(10*time.Second+time.Nanosecond))
	if len(entries) != 1 {
		t.Fatalf("expected one pop after boundary, got %d", len(entries))
	}
}

func TestBizWindowManager_PopOrderByFirstAt(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	instA := newFailureInstanceForWindow("127.0.0.4", 3306, haprobe.DbTypeMySql)
	instB := newFailureInstanceForWindow("127.0.0.5", 3307, haprobe.DbTypeMySql)
	base := time.Now()

	if !mgr.Push(100, instB, base.Add(2*time.Second)) {
		t.Fatal("push for instB should succeed")
	}
	if !mgr.Push(100, instA, base) {
		t.Fatal("push for instA should succeed")
	}

	entries := mgr.Pop(100, base.Add(20*time.Second))
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(entries))
	}
	if !entries[0].FirstAt.Before(entries[1].FirstAt) {
		t.Fatalf("expected entries sorted by FirstAt asc")
	}
	if entries[0].IP != "127.0.0.4" {
		t.Fatalf("expected earliest entry ip=127.0.0.4, got %s", entries[0].IP)
	}
}

func TestBizWindowManager_PopAndMarkStartThenMarkDone(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	inst := newFailureInstanceForWindow("127.0.0.6", 3306, haprobe.DbTypeMySql)
	base := time.Now()

	if !mgr.Push(100, inst, base) {
		t.Fatal("push should succeed")
	}

	entries := mgr.PopAndMarkStart(100, base.Add(11*time.Second))
	if len(entries) != 1 {
		t.Fatalf("expected 1 popped entry, got %d", len(entries))
	}

	if mgr.Push(100, inst, base.Add(12*time.Second)) {
		t.Fatal("push should be blocked while inflight")
	}

	key := instanceWindowKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType)
	mgr.MarkDone(key)

	if !mgr.Push(100, inst, base.Add(13*time.Second)) {
		t.Fatal("push should be accepted after MarkDone")
	}
}

func TestBizWindowManager_InflightTTLExpiredAutoCleanup(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 100*time.Millisecond, "test-service")
	inst := newFailureInstanceForWindow("127.0.0.7", 3306, haprobe.DbTypeMySql)
	key := instanceWindowKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType)

	mgr.mu.Lock()
	mgr.inflight[key] = time.Now().Add(-time.Second)
	mgr.mu.Unlock()

	if !mgr.Push(100, inst, time.Now()) {
		t.Fatal("push should be accepted after expired inflight cleanup")
	}

	mgr.mu.RLock()
	_, exists := mgr.inflight[key]
	mgr.mu.RUnlock()
	if exists {
		t.Fatal("expired inflight key should be cleaned up")
	}
}

func TestBizWindowManager_ConcurrentPushSameInstance(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	inst := newFailureInstanceForWindow("127.0.0.8", 3306, haprobe.DbTypeMySql)
	base := time.Now()

	const total = 64
	var wg sync.WaitGroup
	var accepted atomic.Int64

	for i := 0; i < total; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if mgr.Push(100, inst, base) {
				accepted.Add(1)
			}
		}()
	}

	wg.Wait()

	if accepted.Load() != total {
		t.Fatalf("expected %d accepted pushes, got %d", total, accepted.Load())
	}

	entries := mgr.Pop(100, base.Add(11*time.Second))
	if len(entries) != 1 {
		t.Fatalf("expected 1 merged entry, got %d", len(entries))
	}
	if entries[0].Count != total {
		t.Fatalf("expected merged count=%d, got %d", total, entries[0].Count)
	}
}

func TestBizWindowManager_PushDedupByInstanceAndEvent(t *testing.T) {
	mgr := NewBizWindowManager(10*time.Second, 30*time.Second, "test-service")
	base := time.Now()

	// same instance reporting the same event is merged (count incremented)
	same := newFailureEventForWindow("127.0.0.9", 3306, haprobe.DbTypeMySql, haprobe.DbEventNameDetectFailure)
	if !mgr.Push(100, same, base) {
		t.Fatal("first push should be accepted")
	}
	if !mgr.Push(100, same, base.Add(time.Second)) {
		t.Fatal("second push with same event should be accepted and merged")
	}

	// same instance reporting a different event is kept as a separate entry
	other := newFailureEventForWindow("127.0.0.9", 3306, haprobe.DbTypeMySql, haprobe.DbEventNameProbeOffline)
	if !mgr.Push(100, other, base) {
		t.Fatal("push with different event should be accepted")
	}

	entries := mgr.Pop(100, base.Add(11*time.Second))
	if len(entries) != 2 {
		t.Fatalf("expected 2 entries (one per event), got %d", len(entries))
	}

	byEvent := make(map[haprobe.DbEventName]*FailureWindowEntry, len(entries))
	for _, e := range entries {
		byEvent[e.EventName] = e
	}

	detect, ok := byEvent[haprobe.DbEventNameDetectFailure]
	if !ok {
		t.Fatal("expected detect-failure entry")
	}
	if detect.Count != 2 {
		t.Fatalf("expected detect-failure count=2, got %d", detect.Count)
	}

	offline, ok := byEvent[haprobe.DbEventNameProbeOffline]
	if !ok {
		t.Fatal("expected probe-offline entry")
	}
	if offline.Count != 1 {
		t.Fatalf("expected probe-offline count=1, got %d", offline.Count)
	}
}
