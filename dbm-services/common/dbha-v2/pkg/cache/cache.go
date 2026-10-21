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

// Package cache provides an in-process TTL cache with optional LRU eviction.
package cache

import (
	"container/heap"
	"container/list"
	"sync"
	"time"
)

const (
	cleanupInterval    = 100 * time.Millisecond
	maxExpiredPerCycle = 256
)

// CacheValueConstraint cache value constraint
type CacheValueConstraint interface {
	any
}

type cacheItem[T any] struct {
	key        string
	value      T
	expiration int64
	// index is the expiry-heap index. -1 means the item is not in the heap
	// (zero/negative TTL, i.e. never expires).
	index int
	elem  *list.Element
}

// a min-heap that's ordered by expiration time
type expiryHeap[T any] []*cacheItem[T]

func (h expiryHeap[T]) Len() int           { return len(h) }
func (h expiryHeap[T]) Less(i, j int) bool { return h[i].expiration < h[j].expiration }
func (h expiryHeap[T]) Swap(i, j int) {
	h[i], h[j] = h[j], h[i]
	h[i].index = i
	h[j].index = j
}

func (h *expiryHeap[T]) Push(x any) {
	n := len(*h)
	item := x.(*cacheItem[T])
	item.index = n
	*h = append(*h, item)
}

func (h *expiryHeap[T]) Pop() any {
	old := *h
	n := len(old)
	item := old[n-1]
	item.index = -1 // deleted
	*h = old[0 : n-1]
	return item
}

// HighPerformanceTTLCache is an in-process TTL cache.
// Get promotes the key to the most-recently-used position. When maxEntries > 0
// and the cache is full, the least-recently-used item is evicted.
type HighPerformanceTTLCache[T CacheValueConstraint] struct {
	items      map[string]*cacheItem[T]
	expiry     expiryHeap[T]
	lru        *list.List
	maxEntries int
	mu         sync.Mutex
	stop       chan struct{}
	closeOnce  sync.Once
	wg         sync.WaitGroup
}

// NewHighPerformanceTTLCache creates an unbounded TTL cache.
func NewHighPerformanceTTLCache[T CacheValueConstraint]() *HighPerformanceTTLCache[T] {
	return NewHighPerformanceTTLCacheWithSize[T](0)
}

// NewHighPerformanceTTLCacheWithSize creates a TTL cache that evicts the
// least-recently-used item when size exceeds maxEntries.
// maxEntries <= 0 means unbounded (same as NewHighPerformanceTTLCache).
func NewHighPerformanceTTLCacheWithSize[T CacheValueConstraint](maxEntries int) *HighPerformanceTTLCache[T] {
	if maxEntries < 0 {
		maxEntries = 0
	}
	cache := &HighPerformanceTTLCache[T]{
		items:      make(map[string]*cacheItem[T]),
		expiry:     make(expiryHeap[T], 0),
		lru:        list.New(),
		maxEntries: maxEntries,
		stop:       make(chan struct{}),
	}

	cache.wg.Add(1)
	go cache.cleanupWorker()

	return cache
}

// Set sets cache. ttl <= 0 means the item never expires (it can still be
// evicted by LRU when the cache has a size limit). Set reclaims timed-out
// entries only when the cache is over its size limit; otherwise stale entries
// are left to the background cleaner, Get or Size.
func (c *HighPerformanceTTLCache[T]) Set(key string, value T, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()

	expiration := int64(0)
	if ttl > 0 {
		expiration = time.Now().Add(ttl).UnixNano()
	}

	if old, exists := c.items[key]; exists {
		c.removeItemLocked(old)
	}

	item := &cacheItem[T]{
		key:        key,
		value:      value,
		expiration: expiration,
		index:      -1,
	}
	c.items[key] = item
	item.elem = c.lru.PushFront(item)
	if expiration > 0 {
		heap.Push(&c.expiry, item)
	}

	c.evictIfNeededLocked()
}

// Get get cache by a key. A hit moves the key to the most-recently-used position
// but does not extend the deadline: entries expire after write, not after access,
// so a frequently read key still refreshes from its source once the TTL elapses.
// The returned value is a copy of the stored T; if T holds a reference
// (slice, map, pointer), the caller shares that reference with the cache.
func (c *HighPerformanceTTLCache[T]) Get(key string) (T, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	item, exists := c.items[key]
	if !exists {
		return *new(T), false
	}

	if item.expiration > 0 && time.Now().UnixNano() > item.expiration {
		c.removeItemLocked(item)
		return *new(T), false
	}

	if item.elem != nil {
		c.lru.MoveToFront(item.elem)
	}
	return item.value, true
}

// Delete delete cache by a key
func (c *HighPerformanceTTLCache[T]) Delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if item, exists := c.items[key]; exists {
		c.removeItemLocked(item)
	}
}

// Size returns the number of entries that have not expired. Timed-out entries
// are reclaimed before counting, so the result never depends on how far the
// background cleaner has progressed. Each entry is reclaimed at most once, so
// the amortized cost stays the same as letting the cleaner do it.
func (c *HighPerformanceTTLCache[T]) Size() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.purgeExpiredLocked(time.Now().UnixNano(), 0)
	return len(c.items)
}

// Clear clear cache
func (c *HighPerformanceTTLCache[T]) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	for _, item := range c.items {
		item.index = -1
		item.elem = nil
	}
	c.items = make(map[string]*cacheItem[T])
	c.expiry = make(expiryHeap[T], 0)
	c.lru.Init()
}

// Close stops the background cleanup worker. It is safe to call more than once.
// Get/Set/Delete/Size remain usable after Close: expired keys are still
// reclaimed lazily by Get, by Size, and by eviction once the cache is full.
func (c *HighPerformanceTTLCache[T]) Close() {
	c.closeOnce.Do(func() {
		close(c.stop)
		c.wg.Wait()
	})
}

func (c *HighPerformanceTTLCache[T]) removeFromHeapLocked(item *cacheItem[T]) {
	if item.index >= 0 {
		heap.Remove(&c.expiry, item.index)
		item.index = -1
	}
}

func (c *HighPerformanceTTLCache[T]) removeItemLocked(item *cacheItem[T]) {
	c.removeFromHeapLocked(item)
	if item.elem != nil {
		c.lru.Remove(item.elem)
		item.elem = nil
	}
	delete(c.items, item.key)
}

// evictIfNeededLocked brings the cache back under maxEntries. It reclaims a
// timed-out entry in preference to a live one, so a cold but valid key is never
// dropped while an expired entry still holds a slot. Only as many entries as
// the overflow requires are touched, which keeps Set off the full-purge path.
func (c *HighPerformanceTTLCache[T]) evictIfNeededLocked() {
	if c.maxEntries <= 0 {
		return
	}
	now := time.Now().UnixNano()
	for len(c.items) > c.maxEntries {
		// The heap head is the earliest deadline, so whenever any entry is
		// expired this one is too, including the LRU tail.
		if c.expiry.Len() > 0 && c.expiry[0].expiration <= now {
			c.removeItemLocked(c.expiry[0])
			continue
		}
		back := c.lru.Back()
		if back == nil {
			return
		}
		item, ok := back.Value.(*cacheItem[T])
		if !ok {
			return
		}
		c.removeItemLocked(item)
	}
}

func (c *HighPerformanceTTLCache[T]) cleanupWorker() {
	defer c.wg.Done()

	ticker := time.NewTicker(cleanupInterval)
	defer ticker.Stop()

	for {
		select {
		case <-c.stop:
			return
		case <-ticker.C:
			c.cleanupExpired(maxExpiredPerCycle)
		}
	}
}

func (c *HighPerformanceTTLCache[T]) cleanupExpired(limit int) {
	if limit <= 0 {
		return
	}

	c.mu.Lock()
	defer c.mu.Unlock()
	c.purgeExpiredLocked(time.Now().UnixNano(), limit)
}

// purgeExpiredLocked removes timed-out entries from the heap head.
// limit <= 0 means purge every expired entry; limit > 0 caps the batch
// so the background worker does not hold the mutex for too long.
func (c *HighPerformanceTTLCache[T]) purgeExpiredLocked(now int64, limit int) {
	n := 0
	for c.expiry.Len() > 0 {
		if limit > 0 && n >= limit {
			return
		}
		item := c.expiry[0]
		if item.expiration > now {
			return
		}
		c.removeItemLocked(item)
		n++
	}
}
