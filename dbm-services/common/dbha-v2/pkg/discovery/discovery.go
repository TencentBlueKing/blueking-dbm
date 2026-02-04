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

package discovery

import (
	"context"
	"fmt"
	"strings"
	"sync"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	clientv3 "go.etcd.io/etcd/client/v3"
)

type WatchedEventType int

const (
	WatchedEventPut WatchedEventType = iota
	WatchedEventDelete
	WatchedEventUnknown
)

var (
	ErrEmptyWatchedKey = gerrors.New(gerrors.InvalidParameter, "watched key is required but got empty string")
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
	quit             chan struct{}
	cliMu            sync.RWMutex
	client           *clientv3.Client
	createEtcdClient func() (*clientv3.Client, error)
	wg               sync.WaitGroup
}

// Watch Subscribe to target key events and receive data from the watch channel.
func (d *Discovery) Watch(ctx context.Context, key string) (<-chan *WatchEvent, error) {
	key = strings.TrimSpace(key)
	if key == "" {
		return nil, ErrEmptyWatchedKey
	}

	return d.watchCommon(ctx, key)
}

// WatchWithPrefix Subscribe to prefix key events with prefix and receive data from the watch channel.
func (d *Discovery) WatchWithPrefix(ctx context.Context, key string) (<-chan *WatchEvent, error) {
	key = strings.TrimSpace(key)
	if key == "" {
		return nil, ErrEmptyWatchedKey
	}

	return d.watchCommon(ctx, key, clientv3.WithPrefix())
}

// Get Only get the value of the key.
func (d *Discovery) Get(ctx context.Context, key string) ([]byte, error) {
	key = strings.TrimSpace(key)
	d.cliMu.RLock()
	defer d.cliMu.RUnlock()

	resp, err := d.client.Get(ctx, key)
	if err != nil {
		return nil, gerrors.New(gerrors.EtcdFailure, err.Error())
	}

	if len(resp.Kvs) == 0 {
		errmsg := fmt.Sprintf("the key not exists, key:%s", key)
		return nil, gerrors.New(gerrors.NotExist, errmsg)
	}

	return resp.Kvs[0].Value, nil
}

// GetWithPrefix Get all values that start with the specified key prefix.
func (d *Discovery) GetWithPrefix(ctx context.Context, key string) (map[string][]byte, error) {
	key = strings.TrimSpace(key)
	d.cliMu.RLock()
	defer d.cliMu.RUnlock()

	resp, err := d.client.Get(ctx, key, clientv3.WithPrefix())

	if err != nil {
		return nil, gerrors.New(gerrors.EtcdFailure, err.Error())
	}

	kvs := map[string][]byte{}
	for _, kv := range resp.Kvs {
		kvs[string(kv.Key)] = []byte(kv.Value)
	}

	return kvs, nil
}

// Close Discovery instance
func (d *Discovery) Close() {
	if d.quit != nil {
		close(d.quit) // NOTE: Notify all goroutines by closing this channel.
	}

	d.wg.Wait()
	d.quit = nil

	d.cliMu.Lock()
	defer d.cliMu.Unlock()

	if d.client != nil {
		d.client.Close()
		d.client = nil
	}
}

func (d *Discovery) watchCommon(ctx context.Context, key string, opts ...clientv3.OpOption) (<-chan *WatchEvent, error) {
	if d.quit == nil {
		d.quit = make(chan struct{})
	}

	d.cliMu.Lock()
	if d.client == nil {
		etcdCli, err := d.createEtcdClient()
		if err != nil {
			d.cliMu.Unlock()
			return nil, err
		}
		d.client = etcdCli
	}

	// set watcher
	watchChan := d.client.Watch(ctx, key, opts...)
	watchEventChan := make(chan *WatchEvent, defaultChannelBuffMaxSize)

	d.cliMu.Unlock()

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
				if err := watchResp.Err(); err != nil {
					d.cliMu.Lock()
					d.client.Close()
					d.client = nil
					d.cliMu.Unlock()
					logger.Error("failed to read watch event, errmsg: %v", err)
					return
				}

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
