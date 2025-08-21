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

// Registry  service registry
type Registry struct {
	serviceID        string
	rootKey          string
	ttl              int64
	quit             chan struct{}
	wg               sync.WaitGroup
	cliMu            sync.RWMutex
	client           *clientv3.Client
	leaseID          clientv3.LeaseID
	keepAliveChan    <-chan *clientv3.LeaseKeepAliveResponse
	createEtcdClient func() (*clientv3.Client, error)
}

func (r *Registry) grant(ctx context.Context) error {
	cli, err := r.createEtcdClient()
	if err != nil {
		return err
	}

	logger.Debug("registry grant close the etcd client: %p", r.client)

	r.cliMu.Lock()
	r.client = cli
	r.cliMu.Unlock()

	logger.Debug("registry grant, ttl: %d", r.ttl)

	leaseResp, err := r.client.Grant(ctx, r.ttl)
	if err != nil {
		return gerrors.New(gerrors.OperationFailure, err.Error())
	}
	r.leaseID = leaseResp.ID

	logger.Debug("registry start keepalive, leaseID: %d", r.leaseID)

	keepAliveResp, err := r.client.KeepAlive(ctx, r.leaseID)
	if err != nil {
		r.client.Close()
		return gerrors.New(gerrors.OperationFailure, err.Error())
	}
	r.keepAliveChan = keepAliveResp

	if r.quit == nil {
		r.quit = make(chan struct{})
	}

	logger.Debug("registry start keepalive monitor, leaseID: %d", r.leaseID)

	r.monitorKeepalive(ctx)

	return nil
}

func (r *Registry) monitorKeepalive(ctx context.Context) {
	r.wg.Add(1)
	go func() {
		defer r.wg.Done()

		for {
			select {
			case <-r.quit:
				return

			case <-ctx.Done():
				return

			case respd := <-r.keepAliveChan:
				if respd != nil {
					r.client.TimeToLive(ctx, r.leaseID)
					continue
				}

				logger.Debug("keepalive respond:%v", respd)
				r.client.Close()

				if err := r.grant(context.Background()); err != nil {
					logger.Error("failed to recover lease, ermsg: %v", err)
				}

				logger.Warn("registry keepalive response failure, recovered")
				return
			}
		}
	}()
}

// SetService Create or set the registry root key.
func (r *Registry) SetService(ctx context.Context, value string) error {
	value = strings.TrimSpace(value)

	r.cliMu.RLock()
	if r.client == nil || r.leaseID == 0 {
		r.cliMu.RUnlock()
		logger.Debug("registry set service trigger to recover.")
		if err := r.grant(context.Background()); err != nil {
			return err
		}

		r.cliMu.RLock()
	}

	logger.Debug("registry set service entrance")

	defer func() {
		logger.Debug("registry set service exited")
		r.cliMu.RUnlock()
	}()

	_, err := r.client.Put(ctx, r.rootKey, value, clientv3.WithLease(r.leaseID))
	if err != nil {
		logger.Warn("registry set service put failed, lease-id: %v errmsg: %v", r.leaseID, err)
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

	r.cliMu.RLock()
	if r.leaseID == 0 || r.client == nil {
		r.cliMu.RUnlock()
		logger.Debug("registry set trigger to recover.")
		if err := r.grant(ctx); err != nil {
			return err
		}
		r.cliMu.RLock()
	}

	logger.Debug("registry set entrance")

	defer func() {
		logger.Debug("registry set exited")
		r.cliMu.RUnlock()
	}()

	_, err := r.client.Put(ctx, key, value)
	if err != nil {
		return gerrors.New(gerrors.OperationFailure, err.Error())
	}

	return nil
}

// Close Registry instance
func (r *Registry) Close() {
	logger.Debug("registry closed")
	close(r.quit)
	r.wg.Wait()
	r.quit = nil
}

// GetRootKey returns the root key of the registry
func (r *Registry) GetRootKey() string {
	return r.rootKey
}
