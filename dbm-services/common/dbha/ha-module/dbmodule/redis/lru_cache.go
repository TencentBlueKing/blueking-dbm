package redis

import (
	"container/list"
	"sync"
	"time"
)

// DEFAULT_LRU_CACHE_SIZE TODO
const DEFAULT_LRU_CACHE_SIZE int = 1024

// Cache the interface of cache
type Cache interface {
	Add(key, value interface{}, expiresTime time.Duration)
	Get(key interface{}) (interface{}, bool)
	GetWithTTL(key interface{}) (interface{}, time.Duration, bool)
	Remove(key interface{})
	CacheLen() int
}

type cache struct {
	size  int
	lru   *list.List
	items map[interface{}]*list.Element
}

// 每一个具体的item值
type entry struct {
	key       interface{}
	value     interface{}
	expiresAt time.Time
}

// NewUnlocked 创建一个非阻塞的cache,可以根据需求进行创建,size<=0,会强制设置为DEFAULT_LRU_CACHE_SIZE
func NewUnlocked(size int) Cache {

	// 读与
	if size <= 0 {
		size = DEFAULT_LRU_CACHE_SIZE
	}

	return &cache{
		size:  size,
		lru:   list.New(),
		items: make(map[interface{}]*list.Element),
	}
}

// Add 一般添加时间的比较少,都比较倾向于使用时间点
func (c *cache) Add(key, value interface{}, expireTime time.Duration) {

	expiresAt := time.Now().Add(expireTime)

	if ent, ok := c.items[key]; ok {
		// update existing entry
		c.lru.MoveToFront(ent)
		v := ent.Value.(*entry)
		v.value = value
		v.expiresAt = expiresAt
		return
	}

	// add new entry
	c.items[key] = c.lru.PushFront(&entry{
		key:       key,
		value:     value,
		expiresAt: expiresAt,
	})

	// remove oldest
	if c.lru.Len() > c.size {
		ent := c.lru.Back()
		if ent != nil {
			c.removeElement(ent)
		}
	}
}

// Get get value by key from cache
func (c *cache) Get(key interface{}) (interface{}, bool) {
	if ent, ok := c.items[key]; ok {
		v := ent.Value.(*entry)

		if v.expiresAt.After(time.Now()) {
			// found good entry
			c.lru.MoveToFront(ent)
			return v.value, true
		}

		// ttl expired
		c.removeElement(ent)
	}
	return nil, false
}

// GetWithTTL the get api and support ttl
func (c *cache) GetWithTTL(key interface{}) (interface{}, time.Duration, bool) {
	if ent, ok := c.items[key]; ok {
		v := ent.Value.(*entry)

		if v.expiresAt.After(time.Now()) {
			// found good entry
			c.lru.MoveToFront(ent)
			return v.value, time.Until(v.expiresAt), true
		}

		// ttl expired
		c.removeElement(ent)
	}
	return nil, 0, false
}

// Remove remove item from cache by key
func (c *cache) Remove(key interface{}) {
	if ent, ok := c.items[key]; ok {
		c.removeElement(ent)
	}
}

// CacheLen get the length of cache
func (c *cache) CacheLen() int {
	return c.lru.Len()
}

func (c *cache) removeElement(e *list.Element) {
	c.lru.Remove(e)
	kv := e.Value.(*entry)
	delete(c.items, kv.key)
}

type lockedCache struct {
	c cache
	m sync.Mutex
}

// NewLocked create new instance of lockedCache
func NewLocked(size int) Cache {

	if size <= 0 {
		size = DEFAULT_LRU_CACHE_SIZE
	}
	return &lockedCache{
		c: cache{
			size:  size,
			lru:   list.New(),
			items: make(map[interface{}]*list.Element),
		},
	}
}

// Add add kv to lockedCache
func (l *lockedCache) Add(key, value interface{}, expireTime time.Duration) {
	l.m.Lock()
	l.c.Add(key, value, expireTime)
	l.m.Unlock()
}

// Get get value from lockedCache by key
func (l *lockedCache) Get(key interface{}) (interface{}, bool) {
	l.m.Lock()
	v, f := l.c.Get(key)
	l.m.Unlock()
	return v, f
}

// GetWithTTL the get api support ttl
func (l *lockedCache) GetWithTTL(key interface{}) (interface{}, time.Duration, bool) {
	l.m.Lock()
	defer l.m.Unlock()
	return l.c.GetWithTTL(key)
}

// Remove remove item from lockedCache by key
func (l *lockedCache) Remove(key interface{}) {
	l.m.Lock()
	l.c.Remove(key)
	l.m.Unlock()
}

// CacheLen get the length of lockedCache
func (l *lockedCache) CacheLen() int {
	l.m.Lock()
	c := l.c.CacheLen()
	l.m.Unlock()
	return c
}
