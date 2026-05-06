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
	"testing"
	"time"
)

func TestHighPerformanceTTLCache_SetGet(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Test basic set and get
	cache.Set("key1", "value1", time.Minute)

	value, exists := cache.Get("key1")
	if !exists {
		t.Error("Expected key1 to exist")
	}
	if value != "value1" {
		t.Errorf("Expected value1, got %v", value)
	}

	// Test non-existent key
	value, exists = cache.Get("nonexistent")
	if exists {
		t.Error("Expected nonexistent key to not exist")
	}
	if value != "" {
		t.Errorf("Expected empty value, got %v", value)
	}
}

func TestHighPerformanceTTLCache_Delete(t *testing.T) {
	cache := NewHighPerformanceTTLCache[int]()
	defer cache.Close()

	cache.Set("key1", 100, time.Minute)
	cache.Set("key2", 200, time.Minute)

	// Verify keys exist
	if value, exists := cache.Get("key1"); !exists || value != 100 {
		t.Error("Key1 should exist before deletion")
	}

	// Delete key1
	cache.Delete("key1")

	// Verify key1 is deleted
	if _, exists := cache.Get("key1"); exists {
		t.Error("Key1 should not exist after deletion")
	}

	// Verify key2 still exists
	if value, exists := cache.Get("key2"); !exists || value != 200 {
		t.Error("Key2 should still exist")
	}
}

func TestHighPerformanceTTLCache_TTLExpiration(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Set item with short TTL
	cache.Set("short", "value", 100*time.Millisecond)

	// Should exist immediately
	if _, exists := cache.Get("short"); !exists {
		t.Error("Item should exist immediately after setting")
	}

	// Wait for expiration
	time.Sleep(200 * time.Millisecond)

	// Should be expired
	if _, exists := cache.Get("short"); exists {
		t.Error("Item should be expired after TTL")
	}
}

func TestHighPerformanceTTLCache_ZeroTTL(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Set item with zero TTL (never expires)
	cache.Set("permanent", "value", 0)

	// Should exist immediately
	if _, exists := cache.Get("permanent"); !exists {
		t.Error("Item with zero TTL should exist")
	}

	// Wait and check again
	time.Sleep(100 * time.Millisecond)
	if _, exists := cache.Get("permanent"); !exists {
		t.Error("Item with zero TTL should still exist after wait")
	}
}

func TestHighPerformanceTTLCache_Size(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Initial size should be 0
	if size := cache.Size(); size != 0 {
		t.Errorf("Expected size 0, got %d", size)
	}

	// Add items
	cache.Set("key1", "value1", time.Minute)
	cache.Set("key2", "value2", time.Minute)

	// Size should be 2
	if size := cache.Size(); size != 2 {
		t.Errorf("Expected size 2, got %d", size)
	}

	// Delete one item
	cache.Delete("key1")

	// Size should be 1
	if size := cache.Size(); size != 1 {
		t.Errorf("Expected size 1, got %d", size)
	}
}

func TestHighPerformanceTTLCache_Clear(t *testing.T) {
	cache := NewHighPerformanceTTLCache[int]()
	defer cache.Close()

	// Add multiple items
	cache.Set("key1", 1, time.Minute)
	cache.Set("key2", 2, time.Minute)
	cache.Set("key3", 3, time.Minute)

	// Verify items exist
	if size := cache.Size(); size != 3 {
		t.Errorf("Expected size 3 before clear, got %d", size)
	}

	// Clear cache
	cache.Clear()

	// Verify cache is empty
	if size := cache.Size(); size != 0 {
		t.Errorf("Expected size 0 after clear, got %d", size)
	}

	// Verify individual keys don't exist
	if _, exists := cache.Get("key1"); exists {
		t.Error("Key1 should not exist after clear")
	}
	if _, exists := cache.Get("key2"); exists {
		t.Error("Key2 should not exist after clear")
	}
	if _, exists := cache.Get("key3"); exists {
		t.Error("Key3 should not exist after clear")
	}
}

func TestHighPerformanceTTLCache_UpdateExistingKey(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Set initial value
	cache.Set("key", "value1", time.Minute)

	// Update value
	cache.Set("key", "value2", time.Minute)

	// Should get updated value
	value, exists := cache.Get("key")
	if !exists {
		t.Error("Key should exist after update")
	}
	if value != "value2" {
		t.Errorf("Expected value2, got %v", value)
	}

	// Size should still be 1
	if size := cache.Size(); size != 1 {
		t.Errorf("Expected size 1 after update, got %d", size)
	}
}

func TestHighPerformanceTTLCache_ConcurrentAccess(t *testing.T) {
	cache := NewHighPerformanceTTLCache[int]()
	defer cache.Close()

	// Number of goroutines
	numGoroutines := 10
	done := make(chan bool, numGoroutines)

	// Concurrent writes
	for i := 0; i < numGoroutines; i++ {
		go func(index int) {
			key := string(rune('a' + index))
			cache.Set(key, index, time.Minute)
			done <- true
		}(i)
	}

	// Wait for all writes to complete
	for i := 0; i < numGoroutines; i++ {
		<-done
	}

	// Verify all values were written correctly
	for i := 0; i < numGoroutines; i++ {
		key := string(rune('a' + i))
		value, exists := cache.Get(key)
		if !exists {
			t.Errorf("Key %s should exist", key)
		}
		if value != i {
			t.Errorf("Expected value %d for key %s, got %v", i, key, value)
		}
	}

	// Verify size
	if size := cache.Size(); size != numGoroutines {
		t.Errorf("Expected size %d, got %d", numGoroutines, size)
	}
}

func TestHighPerformanceTTLCache_StructValues(t *testing.T) {
	type TestStruct struct {
		Name  string
		Value int
	}

	// TestStruct now implements CacheValueConstraint by being a struct type
	cache := NewHighPerformanceTTLCache[TestStruct]()
	defer cache.Close()

	testValue := TestStruct{Name: "test", Value: 42}
	cache.Set("struct", testValue, time.Minute)

	value, exists := cache.Get("struct")
	if !exists {
		t.Error("Struct value should exist")
	}
	if value.Name != "test" || value.Value != 42 {
		t.Errorf("Expected struct {test 42}, got %+v", value)
	}
}

func TestHighPerformanceTTLCache_MultipleTypes(t *testing.T) {
	// Test with string type
	stringCache := NewHighPerformanceTTLCache[string]()
	defer stringCache.Close()
	stringCache.Set("test", "string value", time.Minute)

	if value, exists := stringCache.Get("test"); !exists || value != "string value" {
		t.Error("String cache test failed")
	}

	// Test with int type
	intCache := NewHighPerformanceTTLCache[int]()
	defer intCache.Close()
	intCache.Set("test", 123, time.Minute)

	if value, exists := intCache.Get("test"); !exists || value != 123 {
		t.Error("Int cache test failed")
	}

	// Test with bool type
	boolCache := NewHighPerformanceTTLCache[bool]()
	defer boolCache.Close()
	boolCache.Set("test", true, time.Minute)

	if value, exists := boolCache.Get("test"); !exists || value != true {
		t.Error("Bool cache test failed")
	}
}

func TestHighPerformanceTTLCache_Close(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()

	// Add some items
	cache.Set("key1", "value1", time.Second)
	cache.Set("key2", "value2", time.Second)

	// Verify items exist before close
	if size := cache.Size(); size != 2 {
		t.Errorf("Expected size 2 before close, got %d", size)
	}

	// Close the cache
	cache.Close()

	// Try to use cache after close (should not panic)
	func() {
		defer func() {
			if r := recover(); r != nil {
				t.Errorf("Cache operations should not panic after close: %v", r)
			}
		}()

		// These operations should not panic but may not work correctly
		cache.Set("key3", "value3", time.Second)
		_, _ = cache.Get("key1")
		cache.Delete("key1")
	}()
}

func TestHighPerformanceTTLCache_CleanupWorker(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Set items with very short TTL
	cache.Set("short1", "value1", 50*time.Millisecond)
	cache.Set("short2", "value2", 50*time.Millisecond)
	cache.Set("long", "value3", time.Minute) // Long TTL item

	// Verify items exist immediately
	if size := cache.Size(); size != 3 {
		t.Errorf("Expected size 3 immediately, got %d", size)
	}

	// Wait for short TTL items to expire
	time.Sleep(200 * time.Millisecond)

	// Verify short TTL items are cleaned up
	if size := cache.Size(); size != 1 {
		t.Errorf("Expected size 1 after cleanup, got %d", size)
	}

	// Verify specific items
	if _, exists := cache.Get("short1"); exists {
		t.Error("short1 should be expired and cleaned up")
	}
	if _, exists := cache.Get("short2"); exists {
		t.Error("short2 should be expired and cleaned up")
	}
	if value, exists := cache.Get("long"); !exists || value != "value3" {
		t.Error("long TTL item should still exist")
	}
}

func TestHighPerformanceTTLCache_NegativeTTL(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Test negative TTL (should behave like zero TTL)
	cache.Set("negative", "value", -time.Second)

	// Should exist immediately
	value, exists := cache.Get("negative")
	if !exists {
		t.Error("Item with negative TTL should exist")
	}
	if value != "value" {
		t.Errorf("Expected 'value', got %v", value)
	}

	// Wait and check again (should still exist)
	time.Sleep(100 * time.Millisecond)
	if _, exists := cache.Get("negative"); !exists {
		t.Error("Item with negative TTL should still exist after wait")
	}
}

func TestHighPerformanceTTLCache_EmptyKey(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Test empty key
	cache.Set("", "empty value", time.Minute)

	value, exists := cache.Get("")
	if !exists {
		t.Error("Empty key should be allowed and exist")
	}
	if value != "empty value" {
		t.Errorf("Expected 'empty value', got %v", value)
	}

	// Test delete empty key
	cache.Delete("")
	if _, exists := cache.Get(""); exists {
		t.Error("Empty key should be deleted")
	}
}

func TestHighPerformanceTTLCache_Performance(t *testing.T) {
	cache := NewHighPerformanceTTLCache[int]()
	defer cache.Close()

	numItems := 1000
	start := time.Now()

	// Benchmark set operations
	for i := 0; i < numItems; i++ {
		key := string(rune('a' + i%26))
		cache.Set(key, i, time.Minute)
	}

	setTime := time.Since(start)
	t.Logf("Set %d items in %v", numItems, setTime)

	// Benchmark get operations
	start = time.Now()
	for i := 0; i < numItems; i++ {
		key := string(rune('a' + i%26))
		_, _ = cache.Get(key)
	}

	getTime := time.Since(start)
	t.Logf("Get %d items in %v", numItems, getTime)

	// Verify performance expectations
	if setTime > 100*time.Millisecond {
		t.Logf("Set operations took longer than expected: %v", setTime)
	}
	if getTime > 50*time.Millisecond {
		t.Logf("Get operations took longer than expected: %v", getTime)
	}
}

func TestHighPerformanceTTLCache_MemoryEfficiency(t *testing.T) {
	cache := NewHighPerformanceTTLCache[string]()
	defer cache.Close()

	// Add many items
	for i := 0; i < 10000; i++ {
		key := string(rune('a' + i%26))
		cache.Set(key, "value", time.Minute)
	}

	// Size should be limited to 26 (unique keys)
	expectedSize := 26
	if size := cache.Size(); size != expectedSize {
		t.Errorf("Expected size %d (unique keys), got %d", expectedSize, size)
	}

	// Clear and verify memory is released
	cache.Clear()
	if size := cache.Size(); size != 0 {
		t.Errorf("Expected size 0 after clear, got %d", size)
	}
}

func TestHighPerformanceTTLCache_ConcurrentStress(t *testing.T) {
	cache := NewHighPerformanceTTLCache[int]()
	defer cache.Close()

	numGoroutines := 100
	operationsPerGoroutine := 100
	done := make(chan bool, numGoroutines)

	// Concurrent stress test
	for i := 0; i < numGoroutines; i++ {
		go func(goroutineID int) {
			for j := 0; j < operationsPerGoroutine; j++ {
				key := string(rune('a' + j%26))

				// Mix of operations
				switch j % 3 {
				case 0:
					cache.Set(key, goroutineID*1000+j, time.Minute)
				case 1:
					_, _ = cache.Get(key)
				case 2:
					cache.Delete(key)
				}
			}
			done <- true
		}(i)
	}

	// Wait for all goroutines to complete
	for i := 0; i < numGoroutines; i++ {
		<-done
	}

	// Verify cache is still functional
	cache.Set("final", 999, time.Minute)
	if value, exists := cache.Get("final"); !exists || value != 999 {
		t.Error("Cache should still be functional after concurrent stress test")
	}
}

func TestHighPerformanceTTLCache_ComplexTypes(t *testing.T) {
	type ComplexStruct struct {
		ID      int
		Name    string
		Tags    []string
		Details map[string]interface{}
	}

	// ComplexStruct is a struct type, so it satisfies CacheValueConstraint
	cache := NewHighPerformanceTTLCache[ComplexStruct]()
	defer cache.Close()

	complexValue := ComplexStruct{
		ID:   1,
		Name: "test",
		Tags: []string{"tag1", "tag2"},
		Details: map[string]interface{}{
			"field1": "value1",
			"field2": 42,
		},
	}

	cache.Set("complex", complexValue, time.Minute)

	value, exists := cache.Get("complex")
	if !exists {
		t.Error("Complex struct should exist")
	}
	if value.ID != 1 || value.Name != "test" || len(value.Tags) != 2 {
		t.Errorf("Complex struct values mismatch: %+v", value)
	}
}

func TestHighPerformanceTTLCache_BatchOperations(t *testing.T) {
	cache := NewHighPerformanceTTLCache[int]()
	defer cache.Close()

	// Batch set operations
	for i := 0; i < 100; i++ {
		key := string(rune('a' + i))
		cache.Set(key, i, time.Minute)
	}

	// Verify batch operations
	if size := cache.Size(); size != 100 {
		t.Errorf("Expected size 100 after batch set, got %d", size)
	}

	// Batch get operations
	for i := 0; i < 100; i++ {
		key := string(rune('a' + i))
		value, exists := cache.Get(key)
		if !exists || value != i {
			t.Errorf("Batch get failed for key %s: exists=%v, value=%d", key, exists, value)
		}
	}

	// Batch delete operations
	for i := 0; i < 50; i++ {
		key := string(rune('a' + i))
		cache.Delete(key)
	}

	// Verify batch delete
	if size := cache.Size(); size != 50 {
		t.Errorf("Expected size 50 after batch delete, got %d", size)
	}
}
