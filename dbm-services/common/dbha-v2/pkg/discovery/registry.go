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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"fmt"
	"math"
	"strings"
	"sync"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
)

type RegistryEventType int

const (
	RegistryEventRecover RegistryEventType = iota
)

// RegistryEvent registry event
type RegistryEvent struct {
	EventType RegistryEventType
	Key       string
}

// Registry  service registry
type Registry struct {
	serviceId     string
	rootKey       string
	ttl           int64
	quit          chan struct{}
	eventChan     chan *RegistryEvent
	wg            sync.WaitGroup
	mutex         sync.Mutex
	client        *clientv3.Client
	leaseId       clientv3.LeaseID
	keepAliveChan <-chan *clientv3.LeaseKeepAliveResponse
}

func (r *Registry) grant(ctx context.Context) error {

	leaseResp, err := r.client.Grant(ctx, r.ttl)
	if err != nil {
		return gerrors.New(gerrors.OperationFailure, err.Error())
	}
	r.leaseId = leaseResp.ID

	keepAliveResp, err := r.client.KeepAlive(ctx, r.leaseId)
	if err != nil {
		return gerrors.New(gerrors.OperationFailure, err.Error())
	}
	r.keepAliveChan = keepAliveResp

	if r.quit == nil {
		r.quit = make(chan struct{})
	}

	r.wg.Add(2)
	go r.monitorKeepalive(ctx)
	go r.checkLeaseTTL(ctx)

	return nil
}

func (r *Registry) monitorKeepalive(ctx context.Context) {

	defer func() {
		r.wg.Done()
		logger.Info("exit registry monitor keepalive")
	}()

	for {
		select {
		case <-r.quit:
			return

		case <-ctx.Done():
			return

		case _, ok := <-r.keepAliveChan:
			if !ok {
				r.wg.Add(1)
				go func(ctx context.Context) {
					defer r.wg.Done()
					r.recoverLease(ctx)
				}(ctx)
				return
			}
		}
	}
}

func (r *Registry) checkLeaseTTL(ctx context.Context) {

	defer r.wg.Done()

	ttl := time.Duration(math.Floor(float64(r.ttl) / 2))
	ticker := time.NewTicker(ttl * time.Second)

	defer func() {
		ticker.Stop()
		logger.Info("exit registry check lease ttl")
	}()

	for {
		select {
		case <-r.quit:
			return

		case <-ctx.Done():
			return

		case <-ticker.C:
			ttlResp, err := r.client.Lease.TimeToLive(ctx, r.leaseId)
			if err != nil || ttlResp.TTL <= 0 {
				r.wg.Add(1)
				go func(ctx context.Context) {
					r.wg.Done()
					r.recoverLease(ctx)
				}(ctx)
				return
			}
		}
	}
}

func (r *Registry) recoverLease(ctx context.Context) error {

	r.mutex.Lock()
	defer r.mutex.Unlock()

	ttlResp, err := r.client.Lease.TimeToLive(ctx, r.leaseId)
	if err == nil && ttlResp.TTL > 0 {
		return r.grant(ctx)
	}

	return r.grant(ctx)
}

// Events Return the channel which will be triggered when a registry event occurs.
func (r *Registry) Events() chan *RegistryEvent {
	return r.eventChan
}

// SetService Create or set the registry root key.
func (r *Registry) SetService(ctx context.Context, value string) error {

	value = strings.TrimSpace(value)

	if r.leaseId == 0 {
		if err := r.grant(ctx); err != nil {
			return err
		}
	}

	_, err := r.client.Put(ctx, r.rootKey, value, clientv3.WithLease(r.leaseId))
	if err != nil {
		return gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	return nil
}

// Set Create or set the child node with this registry root key.
// If the key has the root key prefix, the key will be applied
// and then it will be appended to the registry root key.
func (r *Registry) Set(ctx context.Context, key, value string) error {

	key = strings.TrimSpace(key)
	if key == "" {
		return gerrors.New(gerrors.InvalidParameter, "key is required")
	}

	if !strings.HasPrefix(key, r.rootKey) {
		key = fmt.Sprintf("%s/%s", r.rootKey, key)
	}

	if r.leaseId == 0 {
		if err := r.grant(ctx); err != nil {
			return err
		}
	}

	_, err := r.client.Put(ctx, key, value)
	if err != nil {
		return gerrors.New(gerrors.OperationFailure, err.Error())
	}

	return nil
}

func (r *Registry) Close() {
	close(r.quit)
	r.quit = nil
	r.wg.Wait()
}
