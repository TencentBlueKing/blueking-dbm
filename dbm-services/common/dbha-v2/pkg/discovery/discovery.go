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

// Package discovery to find service
package discovery

import (
	"context"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"fmt"
	"strings"
	"sync"

	clientv3 "go.etcd.io/etcd/client/v3"
)

type WatchedEventType int

const (
	WatchedEventPut WatchedEventType = iota
	WatchedEventDelete
)

// WatchEvent This event will be generated
// when the watch method detects that event has occured.
type WatchEvent struct {
	EventType WatchedEventType
	Key       string
	Value     []byte
}

// Discovery service discovery
type Discovery struct {
	quit   chan struct{}
	client *clientv3.Client
	wg     sync.WaitGroup
}

// Watch Subscribe to target key events and receive data from the watch channel.
func (d *Discovery) Watch(ctx context.Context, key string) (chan *WatchEvent, error) {

	key = strings.TrimSpace(key)
	if key == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "the watched key is required")
	}

	if d.quit == nil {
		d.quit = make(chan struct{})
	}
	
	// set watcher
	watchChan := d.client.Watch(ctx, key, clientv3.WithPrefix())
	watchEventChan := make(chan *WatchEvent, defaultChannelBuffMaxSize)

	d.wg.Add(1)

	go func() {
		
		defer d.wg.Done()
		defer close(watchEventChan)

		for {
			select {
			case <-d.quit:
				logger.Info("exit watcher. key:%s", key)
				return

			case <-ctx.Done():
				logger.Info("exit watcher. key:%s", key)
				return

			case watchResp := <-watchChan:
				for _, event := range watchResp.Events {
					switch event.Type {
					case clientv3.EventTypePut:
						event := &WatchEvent{
							EventType: WatchedEventPut,
							Key:       string(event.Kv.Key),
							Value:     []byte(event.Kv.Value),
						}
						watchEventChan <- event

					case clientv3.EventTypeDelete:
						event := &WatchEvent{
							EventType: WatchedEventDelete,
							Key:       string(event.Kv.Key),
							Value:     []byte(event.Kv.Value),
						}
						watchEventChan <- event

					}
				}

			}
		}
	}()

	return watchEventChan, nil
}

// WatchWithPrefix Subscribe to target key events with preifix and receive data from the watch channel.
func (d *Discovery) WatchWithPrefix(ctx context.Context, key string) (chan *WatchEvent, error) {

	key = strings.TrimSpace(key)
	if key == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "the watched key is required")
	}

	if d.quit == nil {
		d.quit = make(chan struct{})
	}

	// set watcher
	watchChan := d.client.Watch(ctx, key, clientv3.WithPrefix())
	watchEventChan := make(chan *WatchEvent, defaultChannelBuffMaxSize)

	d.wg.Add(1)

	go func() {
		
		defer d.wg.Done()
		defer close(watchEventChan)

		for {
			select {
			case <-d.quit:
				logger.Info("exit watcher. key prefix:%s", key)
				return

			case <-ctx.Done():
				logger.Info("exit watcher. key prefix:%s", key)
				return

			case watchResp := <-watchChan:
				for _, event := range watchResp.Events {
					switch event.Type {
					case clientv3.EventTypePut:
						event := &WatchEvent{
							EventType: WatchedEventPut,
							Key:       string(event.Kv.Key),
							Value:     []byte(event.Kv.Value),
						}
						watchEventChan <- event

					case clientv3.EventTypeDelete:
						event := &WatchEvent{
							EventType: WatchedEventDelete,
							Key:       string(event.Kv.Key),
							Value:     []byte(event.Kv.Value),
						}
						watchEventChan <- event

					}
				}
			}
		}
	}()

	return watchEventChan, nil
}

// Get Only get the value of the key.
func (d *Discovery) Get(ctx context.Context, key string) ([]byte, error) {

	key = strings.TrimSpace(key)

	resp, err := d.client.Get(ctx, key)
	if err != nil {
		return nil, gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	if len(resp.Kvs) == 0 {
		errmsg := fmt.Sprintf("the key not exists, key:%s", key)
		return nil, gerrors.New(gerrors.NotExists, errmsg)
	}

	var value []byte
	for _, kv := range resp.Kvs {
		value = []byte(kv.Value)
	}

	return value, nil
}

// GetWithPrefix Get all values that start with the specified key preifix.
func (d *Discovery) GetWithPrefix(ctx context.Context, key string) (map[string][]byte, error) {

	key = strings.TrimSpace(key)

	resp, err := d.client.Get(ctx, key, clientv3.WithPrefix())

	if err != nil {
		return nil, gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	kvs := map[string][]byte{}
	for _, kv := range resp.Kvs {
		kvs[string(kv.Key)] = []byte(kv.Value)
	}

	return kvs, nil
}

// Close Discovery instance
func (d *Discovery) Close() {
	close(d.quit) // NOTE: Notify all goroutines by closing this channel.
	d.wg.Wait()
	d.quit = nil
}
