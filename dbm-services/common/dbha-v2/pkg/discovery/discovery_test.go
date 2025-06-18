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
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"testing"

	clientv3 "go.etcd.io/etcd/client/v3"
)

func TestGet(t *testing.T) {
	ctx := context.Background()
	testKey := "/test/discovery/get/key"
	testValue := "discovery-test-value"

	_, err := client.Put(ctx, testKey, testValue)
	if err != nil {
		t.Errorf("failed to put. errmsg: %v", err)
	}

	value, err := dis.Get(ctx, testKey)
	if err != nil {
		t.Errorf("failed to get value. errmsg: %v", err)
	}
	if string(value) != testValue {
		t.Errorf("expected value is discovery-test-value, actual value is %v", value)
	}

	_, err = dis.Get(ctx, "discovery-null-value")
	if err == nil {
		t.Errorf("expected return error when get null key")
	}
	if err.(*gerrors.Error).Code() != gerrors.NotExists {
		t.Errorf("expected err code is NotExists, actual code is %v", err.(*gerrors.Error).Code())
	}

	_, err = client.Delete(ctx, testKey)
	if err != nil {
		t.Errorf("failed to clear test key. errmsg: %v", err)
	}
}

func TestGetWithPrefix(t *testing.T) {
	ctx := context.Background()

	prefix := "/test/discovery/get/prefix"
	testKey1 := prefix + "/key1"
	testKey2 := prefix + "/key2"
	testValue1 := "value1"
	testValue2 := "value2"

	_, err := client.Put(ctx, testKey1, testValue1)
	if err != nil {
		t.Errorf("failed to put key1. errmsg: %v", err)
	}

	_, err = client.Put(ctx, testKey2, testValue2)
	if err != nil {
		t.Errorf("failed to put key2. errmsg: %v", err)
	}

	kvs, err := dis.GetWithPrefix(ctx, prefix)
	if err != nil {
		t.Errorf("failed to get prefix value. errmsg: %v", err)
	}
	if len(kvs) != 2 {
		t.Errorf("expected to get 2 values, but got: %d", len(kvs))
	}
	if string(kvs[testKey1]) != testValue1 {
		t.Errorf("expected value for key1 is %s, but got: %s", testValue1, string(kvs[testKey1]))
	}
	if string(kvs[testKey2]) != testValue2 {
		t.Errorf("expected value for key2 is %s, but got: %s", testValue2, string(kvs[testKey2]))
	}

	_, err = client.Delete(ctx, prefix, clientv3.WithPrefix())
	if err != nil {
		t.Errorf("failed to clear test data. errmsg: %v", err)
	}
}

func TestInvalidParametes(t *testing.T) {
	ctx := context.Background()

	_, err := dis.Watch(ctx, "")
	if err == nil {
		t.Errorf("expected watch error for empty key watch")
	}
	if err.(*gerrors.Error).Code() != gerrors.InvalidParameter {
		t.Errorf("expected watch error code: InvalidParameter, actual: %v", err.(*gerrors.Error).Code())
	}

	_, err = dis.WatchWithPrefix(ctx, "")
	if err == nil {
		t.Errorf("expected watchWithPrefix error for empty key watch")
	}
	if err.(*gerrors.Error).Code() != gerrors.InvalidParameter {
		t.Errorf("expected watchWithPrefix error code: InvalidParameter, actual: %v", err.(*gerrors.Error).Code())
	}
}

func TestWatch(t *testing.T) {

	ctx := context.Background()
	testKey := "/test/discovery/watch/key"
	testValue := "discovery-test-value"

	_, err := client.Put(ctx, testKey, testValue)
	if err != nil {
		t.Errorf("failed to put initial value. errmsg: %v", err)
	}

	watchChan, err := dis.Watch(ctx, testKey)
	if err != nil {
		t.Errorf("failed to start watch. errmsg: %v", err)
	}

	newValue := "discovery-new-value"
	_, err = client.Put(ctx, testKey, newValue)
	if err != nil {
		t.Errorf("failed to change test value. errmsg: %v", err)
	}

	select {
	case event := <-watchChan:
		if event.EventType != discovery.WatchedEventPut {
			t.Errorf("expected event type to be WatchEventPut(%d), but got: %d", discovery.WatchedEventPut, event.EventType)
		}
		if string(event.Value) != newValue {
			t.Errorf("expected event value is %s, but got: %v", newValue, string(event.Value))
		}
	case <-ctx.Done():
		t.Errorf("wait for watch put timeout")
	}

	_, err = client.Delete(ctx, testKey)
	if err != nil {
		t.Errorf("failed to delete value. errmsg: %v", err)
	}

	select {
	case event := <-watchChan:
		if event.EventType != discovery.WatchedEventDelete {
			t.Errorf("expected event type to be WatchEventDelete(%d), but got: %d", discovery.WatchedEventDelete, event.EventType)
		}
	case <-ctx.Done():
		t.Errorf("wait for watch delete timeout")
	}
}

func TestWatchWithPrefix(t *testing.T) {
	ctx := context.Background()
	prefix := "/discovery/test/watch/prefix"
	testKey1 := prefix + "/key1"
	testKey2 := prefix + "/key2"
	testValue1 := "value1"
	testValue2 := "value2"

	_, err := client.Put(ctx, testKey1, testValue1)
	if err != nil {
		t.Errorf("failed to put initial Key2 value. errmsg: %v", err)
	}

	_, err = client.Put(ctx, testKey2, testValue2)
	if err != nil {
		t.Errorf("failed to put initial Key2 value. errmsg: %v", err)
	}

	watchChan, err := dis.WatchWithPrefix(ctx, prefix)
	if err != nil {
		t.Errorf("failed to start watch: %v", err)
	}

	newValue1 := "new-value-1"
	_, err = client.Put(ctx, testKey1, newValue1)
	if err != nil {
		t.Errorf("failed to change value1. errmsg: %v", err)
	}

	select {
	case event := <-watchChan:
		if event.EventType != discovery.WatchedEventPut {
			t.Errorf("expected event type to be WatchEventPut(%d), but got: %d", discovery.WatchedEventPut, event.EventType)
		}
		if string(event.Value) != newValue1 {
			t.Errorf("expected event value is %s, but got: %v", newValue1, string(event.Value))
		}
	case <-ctx.Done():
		t.Errorf("wait for watch delete timeout")
	}

	_, err = client.Delete(ctx, testKey1, clientv3.WithPrefix())
	if err != nil {
		t.Errorf("failed to delete test data. errmsg: %v", err)
	}
	select {
	case event := <-watchChan:
		if event.EventType != discovery.WatchedEventDelete {
			t.Errorf("expected event type to be WatchEventDelete(%d), but got: %d", discovery.WatchedEventDelete, event.EventType)
		}
	case <-ctx.Done():
		t.Errorf("wait for watch delete timeout")
	}
}

func TestClose(t *testing.T) {

	newdis, err := discovery.NewDiscovery(client)
	if err != nil {
		t.Errorf("failed to create discovery instance. errmsg: %v", err)
	}

	ctx := context.Background()
	testKey := "/discovery/test/close/key"

	watchChan, err := newdis.Watch(ctx, testKey)
	if err != nil {
		t.Errorf("failed to start watch. errmsg: %v", err)
	}

	newdis.Close()

	_, err = client.Put(ctx, testKey, "test-close-value")
	if err != nil {
		t.Errorf("failed to set key. errmsg: %v", err)
	}

	select {
	case _, ok := <-watchChan:
		if ok {
			t.Errorf("expected watch channel closed")
		}
	case <-ctx.Done():
		t.Errorf("wait for watch channel close timeout")
	}
}
