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
	"container/heap"
	"sync"
	"time"
)

// CacheValueConstraint cache value constraint
type CacheValueConstraint interface {
	any
}

type cacheItem[T any] struct {
	key        string
	value      T
	expiration int64
	index      int
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

// HighPerformanceTTLCache high-performance TTL cache
type HighPerformanceTTLCache[T CacheValueConstraint] struct {
	items  map[string]*cacheItem[T]
	expiry expiryHeap[T]
	mu     sync.RWMutex
	stop   chan struct{}
	wg     sync.WaitGroup
}

// NewHighPerformanceTTLCache creates high-performance TTL cache
func NewHighPerformanceTTLCache[T CacheValueConstraint]() *HighPerformanceTTLCache[T] {
	cache := &HighPerformanceTTLCache[T]{
		items:  make(map[string]*cacheItem[T]),
		expiry: make(expiryHeap[T], 0),
		stop:   make(chan struct{}),
	}

	// start cleanup worker
	cache.wg.Add(1)
	go cache.cleanupWorker()

	return cache
}

// Set sets cache
func (c *HighPerformanceTTLCache[T]) Set(key string, value T, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()

	expiration := int64(0)
	if ttl > 0 {
		expiration = time.Now().Add(ttl).UnixNano()
	}

	// if key already exists, remove it from heap
	if item, exists := c.items[key]; exists {
		heap.Remove(&c.expiry, item.index)
	}

	// create new cache item
	item := &cacheItem[T]{
		key:        key,
		value:      value,
		expiration: expiration,
	}

	c.items[key] = item
	if expiration > 0 {
		heap.Push(&c.expiry, item)
	}
}

// Get get cache by a key
func (c *HighPerformanceTTLCache[T]) Get(key string) (T, bool) {
	c.mu.RLock()
	item, exists := c.items[key]
	c.mu.RUnlock()

	if !exists {
		return *new(T), false
	}

	// check if expired
	if item.expiration > 0 && time.Now().UnixNano() > item.expiration {
		c.Delete(key)
		return *new(T), false
	}

	return item.value, true
}

// Delete delete cache by a key
func (c *HighPerformanceTTLCache[T]) Delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if item, exists := c.items[key]; exists {
		if item.index >= 0 {
			heap.Remove(&c.expiry, item.index)
		}
		delete(c.items, key)
	}
}

// Size get the cache size
func (c *HighPerformanceTTLCache[T]) Size() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.items)
}

// Clear clear cache
func (c *HighPerformanceTTLCache[T]) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.items = make(map[string]*cacheItem[T])
	c.expiry = make(expiryHeap[T], 0)
}

// 关闭缓存
func (c *HighPerformanceTTLCache[T]) Close() {
	close(c.stop)
	c.wg.Wait()
}

// cleanupWorker cleanup worker goroutine
func (c *HighPerformanceTTLCache[T]) cleanupWorker() {
	defer c.wg.Done()

	for {
		select {
		case <-c.stop:
			return

		default:
			c.cleanupExpired()
			// check every 100ms
			time.Sleep(100 * time.Millisecond)
		}
	}
}

func (c *HighPerformanceTTLCache[T]) cleanupExpired() {
	now := time.Now().UnixNano()

	c.mu.Lock()
	defer c.mu.Unlock()

	for c.expiry.Len() > 0 {
		item := c.expiry[0]
		if item.expiration > now {
			break
		}

		heap.Pop(&c.expiry)
		delete(c.items, item.key)
	}
}
