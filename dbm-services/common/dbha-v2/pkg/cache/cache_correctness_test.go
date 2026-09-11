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

func rawItemCount[T CacheValueConstraint](c *HighPerformanceTTLCache[T]) int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return len(c.items)
}

func assertConsistent[T CacheValueConstraint](t *testing.T, c *HighPerformanceTTLCache[T]) {
	t.Helper()
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.lru.Len() != len(c.items) {
		t.Fatalf("lru len %d != map len %d", c.lru.Len(), len(c.items))
	}

	timed := 0
	for key, item := range c.items {
		if item == nil {
			t.Fatalf("nil item for key %q", key)
		}
		if item.key != key {
			t.Fatalf("item key %q != map key %q", item.key, key)
		}
		if item.elem == nil {
			t.Fatalf("item %q missing LRU element", key)
		}
		elemItem, ok := item.elem.Value.(*cacheItem[T])
		if !ok || elemItem != item {
			t.Fatalf("item %q LRU element does not point back to itself", key)
		}
		if item.expiration > 0 {
			timed++
			if item.index < 0 || item.index >= c.expiry.Len() {
				t.Fatalf("timed item %q has invalid heap index %d", key, item.index)
			}
			if c.expiry[item.index] != item {
				t.Fatalf("heap slot %d does not hold item %q", item.index, key)
			}
		} else if item.index >= 0 {
			t.Fatalf("never-expire item %q must not be in the heap", key)
		}
	}

	if c.expiry.Len() != timed {
		t.Fatalf("heap len %d != timed items %d", c.expiry.Len(), timed)
	}
	for i, item := range c.expiry {
		if item.index != i {
			t.Fatalf("heap index mismatch at %d: item.index=%d", i, item.index)
		}
		if _, ok := c.items[item.key]; !ok {
			t.Fatalf("heap item %q is not in the map", item.key)
		}
	}
}

func TestSize_IgnoresExpiredWithoutWaitingForWorker(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	cache.Close()

	cache.Set("dead", "v", 20*time.Millisecond)
	cache.Set("live", "ok", time.Minute)
	time.Sleep(50 * time.Millisecond)

	if rawItemCount(cache) == 0 {
		t.Fatal("raw map should still hold the expired key before Size/Get")
	}
	if size := cache.Size(); size != 1 {
		t.Fatalf("Size should drop expired keys immediately, got %d", size)
	}
	if rawItemCount(cache) != 1 {
		t.Fatalf("Size must purge expired keys from the map, raw=%d", rawItemCount(cache))
	}
	if _, exists := cache.Get("dead"); exists {
		t.Fatal("expired key should miss after Size purge")
	}
	if v, exists := cache.Get("live"); !exists || v != "ok" {
		t.Fatal("live key should remain")
	}
	assertConsistent(t, cache)
}

func TestSize_ManyExpiredAreAllDiscarded(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	const n = 400
	for i := 0; i < n; i++ {
		cache.Set(fmt.Sprintf("e%d", i), "v", 15*time.Millisecond)
	}
	cache.Set("keep", "ok", time.Minute)
	time.Sleep(40 * time.Millisecond)

	if size := cache.Size(); size != 1 {
		t.Fatalf("expected 1 live key after discarding %d expired, got %d", n, size)
	}
	if rawItemCount(cache) != 1 {
		t.Fatalf("raw map should match live size, raw=%d", rawItemCount(cache))
	}
	assertConsistent(t, cache)
}

func TestLRU_ExpiredSlotDoesNotEvictLiveColdKey(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("cold", "live", time.Minute)
	cache.Set("hot-expired", "tmp", 25*time.Millisecond)
	time.Sleep(50 * time.Millisecond)

	// The expired key is still the most recently written one. Without a
	// purge-before-evict, inserting "new" would drop the live cold key.
	cache.Set("new", "n", time.Minute)

	if cache.Size() != 2 {
		t.Fatalf("expected size 2, got %d", cache.Size())
	}
	if _, exists := cache.Get("hot-expired"); exists {
		t.Fatal("expired key should be gone")
	}
	if v, exists := cache.Get("cold"); !exists || v != "live" {
		t.Fatal("live cold key must not be evicted to make room for an expired slot")
	}
	if v, exists := cache.Get("new"); !exists || v != "n" {
		t.Fatal("new key should remain")
	}
	assertConsistent(t, cache)
}

func TestLRU_SetAfterAllExpiredKeepsOnlyNew(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("a", "1", 20*time.Millisecond)
	cache.Set("b", "2", 20*time.Millisecond)
	time.Sleep(50 * time.Millisecond)
	cache.Set("c", "3", time.Minute)

	if size := cache.Size(); size != 1 {
		t.Fatalf("expected only the new key, size=%d", size)
	}
	if _, exists := cache.Get("a"); exists {
		t.Fatal("a should have expired")
	}
	if _, exists := cache.Get("b"); exists {
		t.Fatal("b should have expired")
	}
	if v, exists := cache.Get("c"); !exists || v != "3" {
		t.Fatal("c should be the only live key")
	}
	assertConsistent(t, cache)
}

func TestSet_UnboundedLeavesReclaimToCleanerAndSize(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	cache.Close()

	const n = 50
	for i := 0; i < n; i++ {
		cache.Set(fmt.Sprintf("e%d", i), "v", 15*time.Millisecond)
	}
	time.Sleep(40 * time.Millisecond)
	cache.Set("fresh", "ok", time.Minute)

	// Without a size limit Set stays off the purge path, so the stale entries
	// are still held; correctness is preserved because they are never visible.
	if raw := rawItemCount(cache); raw != n+1 {
		t.Fatalf("unbounded Set should not walk the expiry heap, raw=%d", raw)
	}
	if _, exists := cache.Get("e0"); exists {
		t.Fatal("expired key must not be visible")
	}
	if size := cache.Size(); size != 1 {
		t.Fatalf("Size should report only the live key, got %d", size)
	}
	if raw := rawItemCount(cache); raw != 1 {
		t.Fatalf("Size should have reclaimed the stale entries, raw=%d", raw)
	}
	if v, exists := cache.Get("fresh"); !exists || v != "ok" {
		t.Fatal("fresh key should remain")
	}
	assertConsistent(t, cache)
}

func TestEviction_ReclaimsOnlyWhatOverflowNeeds(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](5)
	cache.Close()

	for i := 0; i < 5; i++ {
		cache.Set(fmt.Sprintf("e%d", i), "v", 15*time.Millisecond)
	}
	time.Sleep(40 * time.Millisecond)
	cache.Set("fresh", "ok", time.Minute)

	// One slot over the limit means exactly one stale entry is reclaimed;
	// the rest wait for the cleaner instead of blocking this Set.
	if raw := rawItemCount(cache); raw != 5 {
		t.Fatalf("eviction should reclaim just one entry, raw=%d", raw)
	}
	if size := cache.Size(); size != 1 {
		t.Fatalf("only the fresh key is live, got %d", size)
	}
	assertConsistent(t, cache)
}

func TestEviction_PrefersExpiredOverLiveTail(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](3)
	cache.Close()

	cache.Set("cold", "live", time.Minute)
	cache.Set("stale1", "s1", 20*time.Millisecond)
	cache.Set("stale2", "s2", 20*time.Millisecond)
	time.Sleep(50 * time.Millisecond)

	cache.Set("n1", "1", time.Minute)
	cache.Set("n2", "2", time.Minute)

	if size := cache.Size(); size != 3 {
		t.Fatalf("expected 3 live keys, got %d", size)
	}
	if v, exists := cache.Get("cold"); !exists || v != "live" {
		t.Fatal("live cold key must outlive expired entries during eviction")
	}
	if _, exists := cache.Get("stale1"); exists {
		t.Fatal("stale1 should be gone")
	}
	if _, exists := cache.Get("stale2"); exists {
		t.Fatal("stale2 should be gone")
	}
	assertConsistent(t, cache)
}

func TestEviction_LiveOnlyStillFollowsLRU(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	cache.Close()

	cache.Set("a", "1", time.Minute)
	cache.Set("b", "2", time.Minute)
	if _, exists := cache.Get("a"); !exists {
		t.Fatal("a should exist")
	}
	cache.Set("c", "3", time.Minute)

	if _, exists := cache.Get("b"); exists {
		t.Fatal("coldest live key should be evicted when nothing has expired")
	}
	if _, exists := cache.Get("a"); !exists {
		t.Fatal("recently used key should survive")
	}
	assertConsistent(t, cache)
}

func TestInvariants_AfterMixedOps(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](8)
	defer cache.Close()

	for i := 0; i < 20; i++ {
		cache.Set(fmt.Sprintf("k%d", i), "v", time.Minute)
		assertConsistent(t, cache)
	}
	if _, exists := cache.Get("k19"); !exists {
		t.Fatal("latest key should exist")
	}
	assertConsistent(t, cache)

	cache.Set("perm", "p", 0)
	assertConsistent(t, cache)
	cache.Set("perm", "p2", 0)
	assertConsistent(t, cache)
	cache.Set("perm", "p3", time.Minute)
	assertConsistent(t, cache)
	cache.Delete("k18")
	assertConsistent(t, cache)
	cache.Clear()
	assertConsistent(t, cache)
	if cache.Size() != 0 {
		t.Fatal("Clear should leave an empty live set")
	}
}

func TestClear_DetachesOldItems(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	cache.Set("a", "1", time.Minute)
	cache.Set("b", "2", 0)
	var oldA, oldB *cacheItem[string]
	cache.mu.Lock()
	oldA = cache.items["a"]
	oldB = cache.items["b"]
	cache.mu.Unlock()

	cache.Clear()
	if oldA.index != -1 || oldA.elem != nil {
		t.Fatal("cleared timed item should be detached")
	}
	if oldB.index != -1 || oldB.elem != nil {
		t.Fatal("cleared never-expire item should be detached")
	}
	cache.Set("c", "3", time.Minute)
	assertConsistent(t, cache)
}

func TestSize_AfterCloseStillDropsExpired(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	cache.Set("dead", "v", 20*time.Millisecond)
	cache.Set("live", "ok", time.Minute)
	cache.Close()
	time.Sleep(50 * time.Millisecond)

	if size := cache.Size(); size != 1 {
		t.Fatalf("Size after Close should still discard expired keys, got %d", size)
	}
	if v, exists := cache.Get("live"); !exists || v != "ok" {
		t.Fatal("live key should remain after Close")
	}
}

func TestLRU_EvictsNeverExpireWhenOverCapacity(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](1)
	defer cache.Close()

	cache.Set("perm", "old", 0)
	cache.Set("next", "new", 0)
	if cache.Size() != 1 {
		t.Fatalf("expected size 1, got %d", cache.Size())
	}
	if _, exists := cache.Get("perm"); exists {
		t.Fatal("older never-expire key should be evicted")
	}
	if v, exists := cache.Get("next"); !exists || v != "new" {
		t.Fatal("newer never-expire key should remain")
	}
	assertConsistent(t, cache)
}

func TestConcurrent_SizeGetSetWhileExpiring(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[int](64)
	defer cache.Close()

	var wg sync.WaitGroup
	for i := 0; i < 12; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			for j := 0; j < 60; j++ {
				key := fmt.Sprintf("%d-%d", id, j%20)
				cache.Set(key, j, 30*time.Millisecond)
				_, _ = cache.Get(key)
				_ = cache.Size()
				if j%7 == 0 {
					cache.Delete(key)
				}
			}
		}(i)
	}
	wg.Wait()

	if size := cache.Size(); size > 64 {
		t.Fatalf("live size %d exceeded maxEntries", size)
	}
	assertConsistent(t, cache)
}

func TestGet_DoesNotPromoteExpiredKey(t *testing.T) {
	cache := NewHighPerformanceTTLCacheWithSize[string](2)
	defer cache.Close()

	cache.Set("keep", "k", time.Minute)
	cache.Set("dead", "d", 20*time.Millisecond)
	time.Sleep(50 * time.Millisecond)

	if _, exists := cache.Get("dead"); exists {
		t.Fatal("expired get must miss")
	}
	cache.Set("other", "o", time.Minute)

	if _, exists := cache.Get("keep"); !exists {
		t.Fatal("keep should still be present; expired get must not refresh LRU")
	}
	assertConsistent(t, cache)
}
