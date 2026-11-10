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

// Package discovery provides etcd-backed service discovery primitives, including
// key watch/get helpers and lifecycle management for discovery clients.
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

	// ErrDiscoveryClosed is returned by Get, GetWithPrefix, Watch and WatchWithPrefix after Close
	// has been called.
	ErrDiscoveryClosed = gerrors.New(gerrors.EtcdFailure, "discovery is closed")
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
	closed           bool
	createEtcdClient func() (*clientv3.Client, error)
	wg               sync.WaitGroup
}

// Watch Subscribe to target key events and receive data from the watch channel.
// It returns ErrDiscoveryClosed after Close; the returned channel is closed when Close is
// called or ctx is done.
func (d *Discovery) Watch(ctx context.Context, key string) (<-chan *WatchEvent, error) {
	key = strings.TrimSpace(key)
	if key == "" {
		return nil, ErrEmptyWatchedKey
	}

	return d.watchCommon(ctx, key)
}

// WatchWithPrefix Subscribe to prefix key events with prefix and receive data from the watch channel.
// It returns ErrDiscoveryClosed after Close; the returned channel is closed when Close is
// called or ctx is done.
func (d *Discovery) WatchWithPrefix(ctx context.Context, key string) (<-chan *WatchEvent, error) {
	key = strings.TrimSpace(key)
	if key == "" {
		return nil, ErrEmptyWatchedKey
	}

	return d.watchCommon(ctx, key, clientv3.WithPrefix())
}

// Get Only get the value of the key.
// The etcd client is created on first use, so Get works without a prior Watch.
// It returns ErrDiscoveryClosed after Close has been called.
func (d *Discovery) Get(ctx context.Context, key string) ([]byte, error) {
	key = strings.TrimSpace(key)

	var resp *clientv3.GetResponse
	err := d.withReadClient(func(cli *clientv3.Client) error {
		var getErr error
		if resp, getErr = cli.Get(ctx, key); getErr != nil {
			return gerrors.New(gerrors.EtcdFailure, getErr.Error())
		}
		return nil
	})
	if err != nil {
		return nil, err
	}

	if len(resp.Kvs) == 0 {
		errmsg := fmt.Sprintf("the key not exists, key:%s", key)
		return nil, gerrors.New(gerrors.NotExist, errmsg)
	}

	return resp.Kvs[0].Value, nil
}

// GetWithPrefix Get all values that start with the specified key prefix.
// The returned map is keyed by the full etcd key. The etcd client is created on first use,
// so GetWithPrefix works without a prior Watch. It returns ErrDiscoveryClosed after Close.
func (d *Discovery) GetWithPrefix(ctx context.Context, key string) (map[string][]byte, error) {
	key = strings.TrimSpace(key)

	var resp *clientv3.GetResponse
	err := d.withReadClient(func(cli *clientv3.Client) error {
		var getErr error
		if resp, getErr = cli.Get(ctx, key, clientv3.WithPrefix()); getErr != nil {
			return gerrors.New(gerrors.EtcdFailure, getErr.Error())
		}
		return nil
	})
	if err != nil {
		return nil, err
	}

	kvs := map[string][]byte{}
	for _, kv := range resp.Kvs {
		kvs[string(kv.Key)] = []byte(kv.Value)
	}

	return kvs, nil
}

// Close Discovery instance
func (d *Discovery) Close() {
	d.cliMu.Lock()
	d.closed = true
	quit := d.quit
	d.quit = nil
	d.cliMu.Unlock()

	// cliMu must not be held here: a watcher may need it in dropClient before exiting.
	if quit != nil {
		close(quit) // NOTE: Notify all goroutines by closing this channel.
	}
	d.wg.Wait()

	d.cliMu.Lock()
	defer d.cliMu.Unlock()
	if d.client != nil {
		d.client.Close()
		d.client = nil
	}
}

// withReadClient runs fn with the etcd client while cliMu is read-locked, creating the
// client on first use. It returns ErrDiscoveryClosed after Close. fn must only use cli and
// must not call any Discovery method: cliMu is held, so a nested lock can deadlock.
func (d *Discovery) withReadClient(fn func(cli *clientv3.Client) error) error {
	if !d.readClientReady() {
		if err := d.ensureReadClient(); err != nil {
			return err
		}
	}

	d.cliMu.RLock()
	defer d.cliMu.RUnlock()
	if d.closed || d.client == nil {
		return ErrDiscoveryClosed
	}

	return fn(d.client)
}

func (d *Discovery) readClientReady() bool {
	d.cliMu.RLock()
	defer d.cliMu.RUnlock()

	return !d.closed && d.client != nil
}

func (d *Discovery) ensureReadClient() error {
	d.cliMu.Lock()
	defer d.cliMu.Unlock()

	if d.closed {
		return ErrDiscoveryClosed
	}

	if d.client != nil {
		return nil
	}

	etcdCli, err := d.createEtcdClient()
	if err != nil {
		return err
	}
	d.client = etcdCli

	return nil
}

// acquireWatchClient returns the client and quit channel for a new watcher and registers it
// in wg. The caller must call wg.Done when the watcher exits.
func (d *Discovery) acquireWatchClient() (*clientv3.Client, chan struct{}, error) {
	d.cliMu.Lock()
	defer d.cliMu.Unlock()

	if d.closed {
		return nil, nil, ErrDiscoveryClosed
	}
	if d.client == nil {
		etcdCli, err := d.createEtcdClient()
		if err != nil {
			return nil, nil, err
		}
		d.client = etcdCli
	}
	if d.quit == nil {
		d.quit = make(chan struct{})
	}
	d.wg.Add(1)

	return d.client, d.quit, nil
}

// dropClient closes cli and clears it only if it is still the current client, so a watcher
// that failed on an old client never closes a newer one.
func (d *Discovery) dropClient(cli *clientv3.Client) {
	d.cliMu.Lock()
	defer d.cliMu.Unlock()

	if d.client == nil || d.client != cli {
		return
	}
	d.client.Close()
	d.client = nil
}

// toWatchEvent converts an etcd event, returning nil for types other than put and delete.
func toWatchEvent(event *clientv3.Event) *WatchEvent {
	var eventType WatchedEventType
	switch event.Type {
	case clientv3.EventTypePut:
		eventType = WatchedEventPut
	case clientv3.EventTypeDelete:
		eventType = WatchedEventDelete
	default:
		return nil
	}

	return &WatchEvent{
		EventType: eventType,
		Key:       string(event.Kv.Key),
		Value:     []byte(event.Kv.Value),
	}
}

func (d *Discovery) watchCommon(ctx context.Context, key string, opts ...clientv3.OpOption) (<-chan *WatchEvent, error) {
	cli, quit, err := d.acquireWatchClient()
	if err != nil {
		return nil, err
	}

	// cli.Watch blocks until the watch stream is up, so it runs outside cliMu and is
	// cancelled by Close through quit.
	watchCtx, cancel := context.WithCancel(ctx)
	go func() {
		select {
		case <-quit:
			cancel()
		case <-watchCtx.Done():
		}
	}()

	watchChan := cli.Watch(watchCtx, key, opts...)
	watchEventChan := make(chan *WatchEvent, defaultChannelBuffMaxSize)

	go func() {
		defer d.wg.Done()
		defer close(watchEventChan)
		defer cancel()

		for {
			select {
			case <-quit:
				logger.Info("exit watcher. key prefix:%s", key)
				return

			case <-ctx.Done():
				logger.Info("exit watcher. key prefix:%s", key)
				return

			case watchResp, ok := <-watchChan:
				if !ok {
					logger.Info("watch channel closed, key prefix: %s", key)
					return
				}

				if err := watchResp.Err(); err != nil {
					d.dropClient(cli)
					logger.Error("failed to read watch event, errmsg: %s", err)
					return
				}

				for _, event := range watchResp.Events {
					watchEvent := toWatchEvent(event)
					if watchEvent == nil {
						continue
					}

					select {
					case watchEventChan <- watchEvent:
					case <-quit:
						logger.Info("exit watcher while sending event, key prefix: %s", key)
						return
					case <-ctx.Done():
						logger.Info("exit watcher while sending event, key prefix: %s", key)
						return
					}
				}
			}
		}
	}()

	return watchEventChan, nil
}
