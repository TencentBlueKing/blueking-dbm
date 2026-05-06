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
	"sync/atomic"
	"testing"
	"time"
)

// ============================================================================
// etcd reconnection tests
// Note: These tests require manually restarting etcd service to verify auto-reconnection
// ============================================================================

// TestRegistryReconnectAfterEtcdRestart tests Registry auto-reconnection after etcd restart
// Usage:
//  1. Run test: go test -tags=integration -run TestRegistryReconnectAfterEtcdRestart -v
//  2. During test execution (within 60 seconds), manually restart etcd service
//  3. Observe test output to confirm reconnection success
func TestRegistryReconnectAfterEtcdRestart(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	testKey := "/reconnect/registry/test"
	testValue := "registry-reconnect-value"

	t.Log("========================================")
	t.Log("Registry Reconnect Test Started")
	t.Log("Please restart etcd within 60 seconds to test reconnection")
	t.Log("========================================")

	var successCount, errorCount int64
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			err := reg.Set(ctx, testKey, fmt.Sprintf("%s-%d", testValue, time.Now().Unix()))
			if err != nil {
				atomic.AddInt64(&errorCount, 1)
				t.Logf("[%s] Registry Set failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else {
				atomic.AddInt64(&successCount, 1)
				t.Logf("[%s] Registry Set success", time.Now().Format("15:04:05"))
			}
		case <-ctx.Done():
			t.Log("Context cancelled")
			return
		}
	}

	t.Log("========================================")
	t.Logf("Registry Reconnect Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Log("========================================")

	if errorCount > 0 && successCount == 0 {
		t.Errorf("All operations failed, reconnection may not be working")
	}
}

// TestDiscoveryReconnectAfterEtcdRestart tests Discovery auto-reconnection after etcd restart
// Usage:
//  1. Run test: go test -tags=integration -run TestDiscoveryReconnectAfterEtcdRestart -v
//  2. During test execution (within 60 seconds), manually restart etcd service
//  3. Observe test output to confirm reconnection success
func TestDiscoveryReconnectAfterEtcdRestart(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	testKey := "/reconnect/discovery/test"
	testValue := "discovery-reconnect-value"

	// Put initial value first
	_, err := etcdClient.Put(ctx, testKey, testValue)
	if err != nil {
		t.Fatalf("failed to put initial value, errmsg: %v", err)
	}
	defer etcdClient.Delete(ctx, testKey)

	t.Log("========================================")
	t.Log("Discovery Reconnect Test Started")
	t.Log("Please restart etcd within 60 seconds to test reconnection")
	t.Log("========================================")

	var successCount, errorCount int64
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			_, err := dis.Get(ctx, testKey)
			if err != nil {
				atomic.AddInt64(&errorCount, 1)
				t.Logf("[%s] Discovery Get failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else {
				atomic.AddInt64(&successCount, 1)
				t.Logf("[%s] Discovery Get success", time.Now().Format("15:04:05"))
			}
		case <-ctx.Done():
			t.Log("Context cancelled")
			return
		}
	}

	t.Log("========================================")
	t.Logf("Discovery Reconnect Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Log("========================================")

	if errorCount > 0 && successCount == 0 {
		t.Errorf("All operations failed, reconnection may not be working")
	}
}

// TestWatchReconnectAfterEtcdRestart tests Watch behavior after etcd restart
// Usage:
//  1. Run test: go test -tags=integration -run TestWatchReconnectAfterEtcdRestart -v
//  2. During test execution (within 60 seconds), manually restart etcd service
//  3. Observe test output to confirm watch continues working
func TestWatchReconnectAfterEtcdRestart(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	testKey := "/reconnect/watch/test"

	watchChan, err := dis.Watch(ctx, testKey)
	if err != nil {
		t.Fatalf("failed to start watch, errmsg: %v", err)
	}

	t.Log("========================================")
	t.Log("Watch Reconnect Test Started")
	t.Log("Please restart etcd within 60 seconds to test watch behavior")
	t.Log("========================================")

	var receivedCount int64
	var watchClosed bool

	// Goroutine for receiving events
	go func() {
		for event := range watchChan {
			atomic.AddInt64(&receivedCount, 1)
			t.Logf("[%s] Watch received event: type=%d, key=%s",
				time.Now().Format("15:04:05"), event.EventType, event.Key)
		}
		watchClosed = true
		t.Log("Watch channel closed")
	}()

	// Periodically write data
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	var writeCount int64
	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			_, err := etcdClient.Put(ctx, testKey, fmt.Sprintf("value-%d", time.Now().Unix()))
			if err != nil {
				t.Logf("[%s] Put failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else {
				atomic.AddInt64(&writeCount, 1)
				t.Logf("[%s] Put success", time.Now().Format("15:04:05"))
			}
		case <-ctx.Done():
			t.Log("Context cancelled")
			return
		}
	}

	time.Sleep(3 * time.Second) // Wait for last events

	t.Log("========================================")
	t.Logf("Watch Reconnect Test Completed")
	t.Logf("Writes: %d, Received: %d, Watch Closed: %v", writeCount, receivedCount, watchClosed)
	t.Log("========================================")

	// cleanup
	etcdClient.Delete(ctx, testKey)
}

// TestKeepAliveAfterEtcdRestart tests KeepAlive behavior after etcd restart
// Usage:
//  1. Run test: go test -tags=integration -run TestKeepAliveAfterEtcdRestart -v
//  2. During test execution, manually restart etcd service
//  3. Observe whether lease can auto-recover
func TestKeepAliveAfterEtcdRestart(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	t.Log("========================================")
	t.Log("KeepAlive Reconnect Test Started")
	t.Log("Please restart etcd within 60 seconds to test keepalive behavior")
	t.Log("========================================")

	// Use SetService to trigger keepalive
	testValue := "keepalive-test-value"

	var successCount, errorCount int64
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			err := reg.SetService(ctx, fmt.Sprintf("%s-%d", testValue, time.Now().Unix()))
			if err != nil {
				atomic.AddInt64(&errorCount, 1)
				t.Logf("[%s] SetService failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else {
				atomic.AddInt64(&successCount, 1)
				t.Logf("[%s] SetService success", time.Now().Format("15:04:05"))
			}

			// Check if key exists
			resp, err := etcdClient.Get(ctx, reg.GetRootKey())
			if err != nil {
				t.Logf("[%s] Check key failed, errmsg: %v", time.Now().Format("15:04:05"), err)
			} else if len(resp.Kvs) == 0 {
				t.Logf("[%s] Key not found (lease may have expired)", time.Now().Format("15:04:05"))
			} else {
				t.Logf("[%s] Key exists, lease_id=%d", time.Now().Format("15:04:05"), resp.Kvs[0].Lease)
			}
		case <-ctx.Done():
			t.Log("Context cancelled")
			return
		}
	}

	t.Log("========================================")
	t.Logf("KeepAlive Reconnect Test Completed")
	t.Logf("Success: %d, Errors: %d", successCount, errorCount)
	t.Log("========================================")
}

// TestConcurrentOperationsDuringReconnect tests concurrent operations during reconnection
func TestConcurrentOperationsDuringReconnect(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	prefix := "/reconnect/concurrent"

	t.Log("========================================")
	t.Log("Concurrent Operations During Reconnect Test Started")
	t.Log("Please restart etcd within 60 seconds")
	t.Log("========================================")

	var readSuccess, readError int64
	var writeSuccess, writeError int64

	// Concurrent read/write
	done := make(chan struct{})

	// Write goroutine
	go func() {
		counter := 0
		for {
			select {
			case <-done:
				return
			default:
				key := fmt.Sprintf("%s/key-%d", prefix, counter%100)
				err := reg.Set(ctx, key, fmt.Sprintf("value-%d", counter))
				if err != nil {
					atomic.AddInt64(&writeError, 1)
				} else {
					atomic.AddInt64(&writeSuccess, 1)
				}
				counter++
				time.Sleep(100 * time.Millisecond)
			}
		}
	}()

	// Read goroutine
	go func() {
		counter := 0
		for {
			select {
			case <-done:
				return
			default:
				key := fmt.Sprintf("%s/key-%d", prefix, counter%100)
				_, err := dis.Get(ctx, key)
				if err != nil {
					atomic.AddInt64(&readError, 1)
				} else {
					atomic.AddInt64(&readSuccess, 1)
				}
				counter++
				time.Sleep(100 * time.Millisecond)
			}
		}
	}()

	// Periodically output status
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	testDuration := 60 * time.Second
	endTime := time.Now().Add(testDuration)

	for time.Now().Before(endTime) {
		select {
		case <-ticker.C:
			t.Logf("[%s] Read: success=%d, error=%d | Write: success=%d, error=%d",
				time.Now().Format("15:04:05"),
				atomic.LoadInt64(&readSuccess), atomic.LoadInt64(&readError),
				atomic.LoadInt64(&writeSuccess), atomic.LoadInt64(&writeError))
		case <-ctx.Done():
			break
		}
	}

	close(done)
	time.Sleep(1 * time.Second)

	t.Log("========================================")
	t.Logf("Concurrent Operations Test Completed")
	t.Logf("Read:  success=%d, error=%d", readSuccess, readError)
	t.Logf("Write: success=%d, error=%d", writeSuccess, writeError)
	t.Log("========================================")

	// cleanup
	etcdClient.Delete(ctx, prefix)
}
