//go:build integration

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

package discovery_test

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/discovery"

	clientv3 "go.etcd.io/etcd/client/v3"
)

// ============================================================================
// Watch capability tests
// ============================================================================

// TestWatchSingleKey tests single key watch capability
func TestWatchSingleKey(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	testKey := "/benchmark/watch/single/key"
	eventCount := 100

	watchChan, err := dis.Watch(ctx, testKey)
	if err != nil {
		t.Fatalf("failed to start watch, errmsg: %v", err)
	}

	var received int32
	done := make(chan struct{})

	go func() {
		for event := range watchChan {
			if event.EventType == discovery.WatchedEventPut {
				atomic.AddInt32(&received, 1)
				if atomic.LoadInt32(&received) >= int32(eventCount) {
					close(done)
					return
				}
			}
		}
	}()

	// Send events
	for i := 0; i < eventCount; i++ {
		_, err := etcdClient.Put(ctx, testKey, fmt.Sprintf("value-%d", i))
		if err != nil {
			t.Errorf("failed to put value, i: %d, errmsg: %v", i, err)
		}
	}

	select {
	case <-done:
		t.Logf("Watch single key: sent %d events, received %d events", eventCount, atomic.LoadInt32(&received))
	case <-time.After(10 * time.Second):
		t.Errorf("Watch single key timeout, sent: %d, received: %d", eventCount, atomic.LoadInt32(&received))
	}

	// cleanup
	etcdClient.Delete(ctx, testKey)
}

// TestWatchWithPrefixMultipleKeys tests prefix watch with multiple keys
func TestWatchWithPrefixMultipleKeys(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	prefix := "/benchmark/watch/prefix"
	keyCount := 10
	eventPerKey := 20
	totalEvents := keyCount * eventPerKey

	watchChan, err := dis.WatchWithPrefix(ctx, prefix)
	if err != nil {
		t.Fatalf("failed to start watch with prefix, errmsg: %v", err)
	}

	var received int32
	done := make(chan struct{})

	go func() {
		for range watchChan {
			if atomic.AddInt32(&received, 1) >= int32(totalEvents) {
				close(done)
				return
			}
		}
	}()

	// Concurrent write to multiple keys
	var wg sync.WaitGroup
	for i := 0; i < keyCount; i++ {
		wg.Add(1)
		go func(keyIdx int) {
			defer wg.Done()
			key := fmt.Sprintf("%s/key-%d", prefix, keyIdx)
			for j := 0; j < eventPerKey; j++ {
				_, err := etcdClient.Put(ctx, key, fmt.Sprintf("value-%d-%d", keyIdx, j))
				if err != nil {
					t.Errorf("failed to put, key: %s, errmsg: %v", key, err)
				}
			}
		}(i)
	}
	wg.Wait()

	select {
	case <-done:
		t.Logf("Watch with prefix: sent %d events, received %d events", totalEvents, atomic.LoadInt32(&received))
	case <-time.After(15 * time.Second):
		t.Errorf("Watch with prefix timeout, sent: %d, received: %d", totalEvents, atomic.LoadInt32(&received))
	}

	// cleanup
	etcdClient.Delete(ctx, prefix, clientv3.WithPrefix())
}

// TestMultipleWatchers tests multiple watchers concurrent capability
func TestMultipleWatchers(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	testKey := "/benchmark/watch/multi-watcher/key"
	watcherCount := 50
	eventCount := 100

	var watchers []<-chan *discovery.WatchEvent
	var receivedCounts []int32 = make([]int32, watcherCount)

	// Create multiple watchers
	for i := 0; i < watcherCount; i++ {
		newDis, err := client.CreateDiscovery()
		if err != nil {
			t.Fatalf("failed to create discovery, i: %d, errmsg: %v", i, err)
		}
		defer newDis.Close()

		watchChan, err := newDis.Watch(ctx, testKey)
		if err != nil {
			t.Fatalf("failed to start watch, i: %d, errmsg: %v", i, err)
		}
		watchers = append(watchers, watchChan)
	}

	// Start receiving goroutines
	var wg sync.WaitGroup
	for i := 0; i < watcherCount; i++ {
		wg.Add(1)
		go func(idx int, ch <-chan *discovery.WatchEvent) {
			defer wg.Done()
			for range ch {
				atomic.AddInt32(&receivedCounts[idx], 1)
			}
		}(i, watchers[i])
	}

	// Send events
	for i := 0; i < eventCount; i++ {
		_, err := etcdClient.Put(ctx, testKey, fmt.Sprintf("value-%d", i))
		if err != nil {
			t.Errorf("failed to put, i: %d, errmsg: %v", i, err)
		}
		time.Sleep(10 * time.Millisecond) // Avoid too fast
	}

	time.Sleep(3 * time.Second) // Wait for all events to be received

	// Statistics
	var totalReceived int32
	var minReceived, maxReceived int32 = int32(eventCount), 0
	for i := 0; i < watcherCount; i++ {
		count := atomic.LoadInt32(&receivedCounts[i])
		totalReceived += count
		if count < minReceived {
			minReceived = count
		}
		if count > maxReceived {
			maxReceived = count
		}
	}

	avgReceived := float64(totalReceived) / float64(watcherCount)
	t.Logf("Multiple watchers test: watchers=%d, events=%d, avg_received=%.2f, min=%d, max=%d",
		watcherCount, eventCount, avgReceived, minReceived, maxReceived)

	if minReceived < int32(eventCount*80/100) {
		t.Errorf("Some watchers missed too many events, min_received: %d, expected: %d", minReceived, eventCount)
	}

	// cleanup
	etcdClient.Delete(ctx, testKey)
}

// TestWatchEventOrder tests watch event order
func TestWatchEventOrder(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	testKey := "/benchmark/watch/order/key"
	eventCount := 100

	watchChan, err := dis.Watch(ctx, testKey)
	if err != nil {
		t.Fatalf("failed to start watch, errmsg: %v", err)
	}

	receivedValues := make([]string, 0, eventCount)
	done := make(chan struct{})

	go func() {
		for event := range watchChan {
			if event.EventType == discovery.WatchedEventPut {
				receivedValues = append(receivedValues, string(event.Value))
				if len(receivedValues) >= eventCount {
					close(done)
					return
				}
			}
		}
	}()

	// Sequential send
	for i := 0; i < eventCount; i++ {
		_, err := etcdClient.Put(ctx, testKey, fmt.Sprintf("%d", i))
		if err != nil {
			t.Errorf("failed to put, i: %d, errmsg: %v", i, err)
		}
	}

	select {
	case <-done:
		// Check order
		outOfOrder := 0
		for i := 1; i < len(receivedValues); i++ {
			var prev, curr int
			fmt.Sscanf(receivedValues[i-1], "%d", &prev)
			fmt.Sscanf(receivedValues[i], "%d", &curr)
			if curr < prev {
				outOfOrder++
			}
		}
		t.Logf("Watch event order: total=%d, out_of_order=%d", len(receivedValues), outOfOrder)
		if outOfOrder > 0 {
			t.Errorf("Events received out of order: %d", outOfOrder)
		}
	case <-time.After(10 * time.Second):
		t.Errorf("Watch event order test timeout, received: %d", len(receivedValues))
	}

	// cleanup
	etcdClient.Delete(ctx, testKey)
}

// TestWatchDeleteEvents tests delete events
func TestWatchDeleteEvents(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	prefix := "/benchmark/watch/delete"
	keyCount := 20

	// Create keys first
	for i := 0; i < keyCount; i++ {
		key := fmt.Sprintf("%s/key-%d", prefix, i)
		_, err := etcdClient.Put(ctx, key, fmt.Sprintf("value-%d", i))
		if err != nil {
			t.Fatalf("failed to put initial value, errmsg: %v", err)
		}
	}

	watchChan, err := dis.WatchWithPrefix(ctx, prefix)
	if err != nil {
		t.Fatalf("failed to start watch, errmsg: %v", err)
	}

	var putCount, deleteCount int32
	done := make(chan struct{})

	go func() {
		for event := range watchChan {
			switch event.EventType {
			case discovery.WatchedEventPut:
				atomic.AddInt32(&putCount, 1)
			case discovery.WatchedEventDelete:
				if atomic.AddInt32(&deleteCount, 1) >= int32(keyCount) {
					close(done)
					return
				}
			}
		}
	}()

	// Delete all keys
	for i := 0; i < keyCount; i++ {
		key := fmt.Sprintf("%s/key-%d", prefix, i)
		_, err := etcdClient.Delete(ctx, key)
		if err != nil {
			t.Errorf("failed to delete, key: %s, errmsg: %v", key, err)
		}
	}

	select {
	case <-done:
		t.Logf("Watch delete events: put=%d, delete=%d", atomic.LoadInt32(&putCount), atomic.LoadInt32(&deleteCount))
	case <-time.After(10 * time.Second):
		t.Errorf("Watch delete events timeout, delete_received: %d, expected: %d",
			atomic.LoadInt32(&deleteCount), keyCount)
	}
}

// ============================================================================
// Read/Write QPS tests
// ============================================================================

// TestReadQPS tests read QPS
func TestReadQPS(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	testKey := "/benchmark/qps/read/key"
	testValue := "benchmark-read-value"

	// Prepare data
	_, err := etcdClient.Put(ctx, testKey, testValue)
	if err != nil {
		t.Fatalf("failed to prepare test data, errmsg: %v", err)
	}
	defer etcdClient.Delete(ctx, testKey)

	// Warm up: initialize discovery client through Watch
	watchChan, err := dis.Watch(ctx, testKey)
	if err != nil {
		t.Fatalf("failed to warm up discovery, errmsg: %v", err)
	}
	// Consume watch channel to avoid blocking
	go func() {
		for range watchChan {
		}
	}()

	concurrency := []int{1, 10, 50, 100}
	duration := 5 * time.Second

	for _, c := range concurrency {
		var ops int64
		var errors int64
		start := time.Now()
		done := make(chan struct{})

		var wg sync.WaitGroup
		for i := 0; i < c; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				for {
					select {
					case <-done:
						return
					default:
						_, err := dis.Get(ctx, testKey)
						if err != nil {
							atomic.AddInt64(&errors, 1)
						} else {
							atomic.AddInt64(&ops, 1)
						}
					}
				}
			}()
		}

		time.Sleep(duration)
		close(done)
		wg.Wait()

		elapsed := time.Since(start)
		qps := float64(ops) / elapsed.Seconds()
		t.Logf("Read QPS: concurrency=%d, ops=%d, errors=%d, duration=%v, QPS=%.2f",
			c, ops, errors, elapsed, qps)
	}
}

// TestWriteQPS tests write QPS
func TestWriteQPS(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	prefix := "/benchmark/qps/write"
	defer etcdClient.Delete(ctx, prefix, clientv3.WithPrefix())

	concurrency := []int{1, 10, 50, 100}
	duration := 5 * time.Second

	for _, c := range concurrency {
		var ops int64
		var errors int64
		start := time.Now()
		done := make(chan struct{})

		var wg sync.WaitGroup
		for i := 0; i < c; i++ {
			wg.Add(1)
			go func(workerID int) {
				defer wg.Done()
				counter := 0
				for {
					select {
					case <-done:
						return
					default:
						key := fmt.Sprintf("%s/worker-%d/key-%d", prefix, workerID, counter)
						err := reg.Set(ctx, key, fmt.Sprintf("value-%d", counter))
						if err != nil {
							atomic.AddInt64(&errors, 1)
						} else {
							atomic.AddInt64(&ops, 1)
						}
						counter++
					}
				}
			}(i)
		}

		time.Sleep(duration)
		close(done)
		wg.Wait()

		elapsed := time.Since(start)
		qps := float64(ops) / elapsed.Seconds()
		t.Logf("Write QPS: concurrency=%d, ops=%d, errors=%d, duration=%v, QPS=%.2f",
			c, ops, errors, elapsed, qps)
	}
}

// TestMixedReadWriteQPS tests mixed read/write QPS
func TestMixedReadWriteQPS(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	prefix := "/benchmark/qps/mixed"
	keyCount := 100

	// Prepare data
	for i := 0; i < keyCount; i++ {
		key := fmt.Sprintf("%s/key-%d", prefix, i)
		_, err := etcdClient.Put(ctx, key, fmt.Sprintf("value-%d", i))
		if err != nil {
			t.Fatalf("failed to prepare test data, errmsg: %v", err)
		}
	}
	defer etcdClient.Delete(ctx, prefix, clientv3.WithPrefix())

	concurrency := 50
	duration := 10 * time.Second
	readRatio := 0.8 // 80% read, 20% write

	var readOps, writeOps int64
	var readErrors, writeErrors int64
	start := time.Now()
	done := make(chan struct{})

	var wg sync.WaitGroup
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			counter := 0
			for {
				select {
				case <-done:
					return
				default:
					if float64(counter%100)/100 < readRatio {
						// Read operation
						key := fmt.Sprintf("%s/key-%d", prefix, counter%keyCount)
						_, err := dis.Get(ctx, key)
						if err != nil {
							atomic.AddInt64(&readErrors, 1)
						} else {
							atomic.AddInt64(&readOps, 1)
						}
					} else {
						// Write operation
						key := fmt.Sprintf("%s/key-%d", prefix, counter%keyCount)
						err := reg.Set(ctx, key, fmt.Sprintf("updated-%d-%d", workerID, counter))
						if err != nil {
							atomic.AddInt64(&writeErrors, 1)
						} else {
							atomic.AddInt64(&writeOps, 1)
						}
					}
					counter++
				}
			}
		}(i)
	}

	time.Sleep(duration)
	close(done)
	wg.Wait()

	elapsed := time.Since(start)
	totalOps := readOps + writeOps
	totalQPS := float64(totalOps) / elapsed.Seconds()
	readQPS := float64(readOps) / elapsed.Seconds()
	writeQPS := float64(writeOps) / elapsed.Seconds()

	t.Logf("Mixed QPS: concurrency=%d, duration=%v", concurrency, elapsed)
	t.Logf("  Read:  ops=%d, errors=%d, QPS=%.2f", readOps, readErrors, readQPS)
	t.Logf("  Write: ops=%d, errors=%d, QPS=%.2f", writeOps, writeErrors, writeQPS)
	t.Logf("  Total: ops=%d, QPS=%.2f", totalOps, totalQPS)
}

// ============================================================================
// Watch limit tests
// ============================================================================

// TestWatchChannelBufferLimit tests watch channel buffer limit
func TestWatchChannelBufferLimit(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	testKey := "/benchmark/watch/buffer/key"
	burstCount := 1000 // Burst write count

	watchChan, err := dis.Watch(ctx, testKey)
	if err != nil {
		t.Fatalf("failed to start watch, errmsg: %v", err)
	}

	// Fast burst write without consuming
	for i := 0; i < burstCount; i++ {
		_, err := etcdClient.Put(ctx, testKey, fmt.Sprintf("burst-value-%d", i))
		if err != nil {
			t.Errorf("failed to put burst value, i: %d, errmsg: %v", i, err)
			break
		}
	}

	// Wait before consuming
	time.Sleep(2 * time.Second)

	// Consume all events
	var received int32
	timeout := time.After(10 * time.Second)

consumeLoop:
	for {
		select {
		case _, ok := <-watchChan:
			if !ok {
				break consumeLoop
			}
			atomic.AddInt32(&received, 1)
		case <-timeout:
			break consumeLoop
		}
	}

	t.Logf("Watch buffer limit: burst=%d, received=%d, loss_rate=%.2f%%",
		burstCount, received, float64(burstCount-int(received))/float64(burstCount)*100)

	// cleanup
	etcdClient.Delete(ctx, testKey)
}

// TestMaxWatchersPerKey tests maximum watcher count per key
func TestMaxWatchersPerKey(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	testKey := "/benchmark/watch/max-watchers/key"
	maxWatchers := 200

	var discoveries []*discovery.Discovery
	var watchChans []<-chan *discovery.WatchEvent
	var createErrors int

	// Create large number of watchers
	for i := 0; i < maxWatchers; i++ {
		newDis, err := client.CreateDiscovery()
		if err != nil {
			createErrors++
			t.Logf("failed to create discovery at %d, errmsg: %v", i, err)
			break
		}
		discoveries = append(discoveries, newDis)

		watchChan, err := newDis.Watch(ctx, testKey)
		if err != nil {
			createErrors++
			t.Logf("failed to create watch at %d, errmsg: %v", i, err)
			break
		}
		watchChans = append(watchChans, watchChan)
	}

	t.Logf("Max watchers test: requested=%d, created=%d, errors=%d",
		maxWatchers, len(watchChans), createErrors)

	// Send one event to verify all watchers can receive
	_, err := etcdClient.Put(ctx, testKey, "test-value")
	if err != nil {
		t.Errorf("failed to put test value, errmsg: %v", err)
	}

	time.Sleep(3 * time.Second)

	var receivedCount int
	for _, ch := range watchChans {
		select {
		case <-ch:
			receivedCount++
		default:
		}
	}

	t.Logf("Max watchers receive test: watchers=%d, received=%d", len(watchChans), receivedCount)

	// cleanup
	for _, d := range discoveries {
		d.Close()
	}
	etcdClient.Delete(ctx, testKey)
}
