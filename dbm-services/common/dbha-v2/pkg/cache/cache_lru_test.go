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

package cache

import (
	"fmt"
	"sync"
	"testing"
	"time"
)

func TestNewWithSize_NegativeTreatedAsUnbounded(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](-1)
	defer cache.Close()

	for i := 0; i < 20; i++ {
		cache.Set(fmt.Sprintf("k%d", i), "v", time.Minute)
	}
	if size := cache.Size(); size != 20 {
		t.Fatalf("negative maxEntries should be unbounded, got size %d", size)
	}
}

func TestNewWithSize_ZeroSameAsUnbounded(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](0)
	defer cache.Close()

	for i := 0; i < 20; i++ {
		cache.Set(fmt.Sprintf("k%d", i), "v", time.Minute)
	}
	if size := cache.Size(); size != 20 {
		t.Fatalf("maxEntries=0 should be unbounded, got size %d", size)
	}
}

func TestLRU_EvictsLeastRecentlyUsed(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "va", time.Minute)
	cache.Set("b", "vb", time.Minute)
	cache.Set("c", "vc", time.Minute)

	if cache.Size() != 2 {
		t.Fatalf("expected size 2, got %d", cache.Size())
	}
	if _, exists := cache.Get("a"); exists {
		t.Fatal("a should have been evicted")
	}
	if v, exists := cache.Get("b"); !exists || v != "vb" {
		t.Fatal("b should remain")
	}
	if v, exists := cache.Get("c"); !exists || v != "vc" {
		t.Fatal("c should remain")
	}
}

func TestLRU_GetProtectsHotKey(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "va", time.Minute)
	cache.Set("b", "vb", time.Minute)
	if _, exists := cache.Get("a"); !exists {
		t.Fatal("a should exist before eviction")
	}

	cache.Set("c", "vc", time.Minute)

	if _, exists := cache.Get("b"); exists {
		t.Fatal("b should have been evicted after a was touched")
	}
	if v, exists := cache.Get("a"); !exists || v != "va" {
		t.Fatal("a should remain as the hot key")
	}
	if v, exists := cache.Get("c"); !exists || v != "vc" {
		t.Fatal("c should remain")
	}
}

func TestLRU_UpdateExistingDoesNotEvictOthers(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "va", time.Minute)
	cache.Set("b", "vb", time.Minute)
	cache.Set("a", "va2", time.Minute)

	if cache.Size() != 2 {
		t.Fatalf("expected size 2 after update, got %d", cache.Size())
	}
	if v, exists := cache.Get("a"); !exists || v != "va2" {
		t.Fatal("updated value of a is missing")
	}
	if v, exists := cache.Get("b"); !exists || v != "vb" {
		t.Fatal("b should not be evicted when a is updated")
	}
}

func TestLRU_UpdateMovesKeyToFront(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "va", time.Minute)
	cache.Set("b", "vb", time.Minute)
	cache.Set("a", "va2", time.Minute)
	cache.Set("c", "vc", time.Minute)

	if _, exists := cache.Get("b"); exists {
		t.Fatal("b should be evicted after a was updated (moved to front)")
	}
	if v, exists := cache.Get("a"); !exists || v != "va2" {
		t.Fatal("a should remain")
	}
	if v, exists := cache.Get("c"); !exists || v != "vc" {
		t.Fatal("c should remain")
	}
}

func TestLRU_MaxEntriesOne(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[int](1)
	defer cache.Close()

	cache.Set("a", 1, time.Minute)
	cache.Set("b", 2, time.Minute)

	if cache.Size() != 1 {
		t.Fatalf("expected size 1, got %d", cache.Size())
	}
	if _, exists := cache.Get("a"); exists {
		t.Fatal("a should have been evicted")
	}
	if v, exists := cache.Get("b"); !exists || v != 2 {
		t.Fatal("b should be the only remaining key")
	}
}

func TestLRU_DeleteThenFill(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "va", time.Minute)
	cache.Set("b", "vb", time.Minute)
	cache.Delete("a")
	cache.Set("c", "vc", time.Minute)

	if cache.Size() != 2 {
		t.Fatalf("expected size 2, got %d", cache.Size())
	}
	if _, exists := cache.Get("a"); exists {
		t.Fatal("deleted key a should stay gone")
	}
	if _, exists := cache.Get("b"); !exists {
		t.Fatal("b should remain")
	}
	if _, exists := cache.Get("c"); !exists {
		t.Fatal("c should remain")
	}
}

func TestLRU_ClearResetsOrder(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "va", time.Minute)
	cache.Set("b", "vb", time.Minute)
	cache.Clear()
	cache.Set("c", "vc", time.Minute)
	cache.Set("d", "vd", time.Minute)
	cache.Set("e", "ve", time.Minute)

	if cache.Size() != 2 {
		t.Fatalf("expected size 2 after refill, got %d", cache.Size())
	}
	if _, exists := cache.Get("c"); exists {
		t.Fatal("c should have been evicted after clear+refill")
	}
	if _, exists := cache.Get("a"); exists {
		t.Fatal("a should not survive Clear")
	}
}

func TestLRU_NeverExpireStillEvicted(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](1)
	defer cache.Close()

	cache.Set("perm", "keep", 0)
	cache.Set("next", "n", time.Minute)

	if _, exists := cache.Get("perm"); exists {
		t.Fatal("never-expire item must still be evicted by LRU")
	}
	if v, exists := cache.Get("next"); !exists || v != "n" {
		t.Fatal("next should remain")
	}
}

func TestUpdateZeroTTL_DoesNotCorruptHeap(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	cache.Set("perm", "v1", 0)
	cache.Set("timed", "t1", time.Minute)
	// Updating a never-expire key used to heap.Remove at index 0 and drop the wrong item.
	cache.Set("perm", "v2", 0)

	if v, exists := cache.Get("perm"); !exists || v != "v2" {
		t.Fatal("updated never-expire key is missing")
	}
	if v, exists := cache.Get("timed"); !exists || v != "t1" {
		t.Fatal("timed key was corrupted when updating a never-expire key")
	}

	cache.Set("perm", "v3", 50*time.Millisecond)
	if v, exists := cache.Get("perm"); !exists || v != "v3" {
		t.Fatal("switching never-expire to a timed TTL failed")
	}
	time.Sleep(150 * time.Millisecond)
	if _, exists := cache.Get("perm"); exists {
		t.Fatal("key should expire after switching to a short TTL")
	}
	if _, exists := cache.Get("timed"); !exists {
		t.Fatal("timed key should still exist")
	}
}

func TestUpdateTimedToNeverExpire(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	cache.Set("k", "v1", 80*time.Millisecond)
	cache.Set("k", "v2", 0)
	time.Sleep(200 * time.Millisecond)
	if v, exists := cache.Get("k"); !exists || v != "v2" {
		t.Fatal("key should no longer expire after switching to zero TTL")
	}
}

func TestGetExpiredReturnsFalseAndRemoves(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	cache.Set("k", "", 30*time.Millisecond)
	time.Sleep(80 * time.Millisecond)

	v, exists := cache.Get("k")
	if exists {
		t.Fatal("expired key should miss")
	}
	if v != "" {
		t.Fatalf("expired miss should return zero value, got %q", v)
	}
	if cache.Size() != 0 {
		t.Fatalf("expired key should be removed, size=%d", cache.Size())
	}
}

func TestDeleteNeverExpireKey(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	cache.Set("perm", "v", 0)
	cache.Set("timed", "t", time.Minute)
	cache.Delete("perm")

	if _, exists := cache.Get("perm"); exists {
		t.Fatal("deleted never-expire key still present")
	}
	if _, exists := cache.Get("timed"); !exists {
		t.Fatal("unrelated timed key was removed")
	}
}

func TestCleanupWorker_BoundedBatch(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	cache.Close()

	const n = 300
	for i := 0; i < n; i++ {
		cache.Set(fmt.Sprintf("k%d", i), "v", 20*time.Millisecond)
	}
	cache.Set("keep", "ok", time.Minute)

	time.Sleep(50 * time.Millisecond)
	cache.cleanupExpired(maxExpiredPerCycle)
	raw := rawItemCount(cache)
	wantRaw := n + 1 - maxExpiredPerCycle
	if raw != wantRaw {
		t.Fatalf("one bounded cleanup should leave %d raw items, got %d", wantRaw, raw)
	}

	if _, exists := cache.Get("keep"); !exists {
		t.Fatal("long-lived key should survive batch expiry")
	}
	if size := cache.Size(); size != 1 {
		t.Fatalf("Size must count only live keys, size=%d", size)
	}
}

func TestLRU_ExpiredGetDoesNotCountAsUse(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("old", "v", 30*time.Millisecond)
	cache.Set("hot", "h", time.Minute)
	time.Sleep(80 * time.Millisecond)

	if _, exists := cache.Get("old"); exists {
		t.Fatal("old should already be expired")
	}
	cache.Set("new", "n", time.Minute)

	if cache.Size() != 2 {
		t.Fatalf("expected size 2, got %d", cache.Size())
	}
	if _, exists := cache.Get("hot"); !exists {
		t.Fatal("hot should remain")
	}
	if _, exists := cache.Get("new"); !exists {
		t.Fatal("new should remain")
	}
}

func TestLRU_ConcurrentWithSizeLimit(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[int](32)
	defer cache.Close()

	const goroutines = 20
	const ops = 80
	var wg sync.WaitGroup
	wg.Add(goroutines)
	for i := 0; i < goroutines; i++ {
		go func(id int) {
			defer wg.Done()
			for j := 0; j < ops; j++ {
				key := fmt.Sprintf("%d-%d", id, j%40)
				switch j % 3 {
				case 0:
					cache.Set(key, id+j, time.Minute)
				case 1:
					_, _ = cache.Get(key)
				default:
					cache.Delete(key)
				}
			}
		}(i)
	}
	wg.Wait()

	if size := cache.Size(); size > 32 {
		t.Fatalf("size %d exceeded maxEntries 32", size)
	}
	cache.Set("final", 1, time.Minute)
	if v, exists := cache.Get("final"); !exists || v != 1 {
		t.Fatal("cache should still work after concurrent LRU traffic")
	}
}

func TestCloseIdempotentAndStillReadable(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	cache.Set("k", "v", time.Minute)
	cache.Close()
	cache.Close()

	if v, exists := cache.Get("k"); !exists || v != "v" {
		t.Fatal("Get after Close should still return live keys")
	}
	cache.Set("k2", "v2", 20*time.Millisecond)
	if _, exists := cache.Get("k2"); !exists {
		t.Fatal("Set after Close should still work")
	}
}

func TestUnboundedHoldsMoreThanSmallLRU(t *testing.T) {
	unbounded := NewHighPerformanceTTLCache[string]()
	defer unbounded.Close()
	limited := NewHighPerformanceTTLCacheWithSize[string](8)
	defer limited.Close()

	for i := 0; i < 40; i++ {
		key := fmt.Sprintf("k%d", i)
		unbounded.Set(key, "v", time.Minute)
		limited.Set(key, "v", time.Minute)
	}
	if unbounded.Size() != 40 {
		t.Fatalf("unbounded size=%d", unbounded.Size())
	}
	if limited.Size() != 8 {
		t.Fatalf("limited size=%d", limited.Size())
	}
	if _, exists := limited.Get("k0"); exists {
		t.Fatal("oldest keys should be gone from the limited cache")
	}
	if _, exists := unbounded.Get("k0"); !exists {
		t.Fatal("unbounded cache should keep the oldest key")
	}
}
