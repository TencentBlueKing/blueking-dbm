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
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	clientv3 "go.etcd.io/etcd/client/v3"
)

// Registry  service registry
type Registry struct {
	serviceID        string
	rootKey          string
	ttl              int64
	wg               sync.WaitGroup
	cliMu            sync.RWMutex
	client           *clientv3.Client
	leaseID          clientv3.LeaseID
	keepAliveCancel  context.CancelFunc
	createEtcdClient func() (*clientv3.Client, error)
}

func (r *Registry) grant(ctx context.Context) error {
	r.cliMu.Lock()
	defer r.cliMu.Unlock()

	cli, err := r.createEtcdClient()
	if err != nil {
		return err
	}

	r.client = cli

	leaseResp, err := r.client.Grant(ctx, r.ttl)
	if err != nil {
		return gerrors.NewE(gerrors.EtcdFailure, err)
	}
	r.leaseID = leaseResp.ID

	logger.Debug("registry start keepalive, leaseID: %d", r.leaseID)

	_, err = r.client.Put(ctx, r.rootKey, "", clientv3.WithLease(r.leaseID))
	if err != nil {
		r.client.Close()
		return gerrors.NewE(gerrors.EtcdFailure, err)
	}

	return r.createKeepAlive()
}

func (r *Registry) handleKeepalive(keepAliveChan <-chan *clientv3.LeaseKeepAliveResponse) {
	for respd := range keepAliveChan {
		if respd == nil {
			logger.Warn("registry keepalive response failure.")

			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()

			if err := r.recoverConnection(ctx); err != nil {
				logger.Warn("registry keepalive response failure, failed to recover, errmsg: %s", err)
				return
			}

			logger.Warn("registry keepalive response failure, recovered")
			return
		}
	}
}

// SetService Create or set the registry root key.
func (r *Registry) SetService(ctx context.Context, value string) error {
	value = strings.TrimSpace(value)

	if r.isInvalidClient() {
		logger.Warn("registry set service trigger to recover.")
		if err := r.recoverConnection(ctx); err != nil {
			return err
		}
	}

	r.cliMu.RLock()
	defer r.cliMu.RUnlock()

	_, err := r.client.Put(ctx, r.rootKey, value, clientv3.WithLease(r.leaseID))
	if err != nil {
		logger.Warn("registry set service put failed, lease-id: %v errmsg: %v", r.leaseID, err)
		return gerrors.Newf(gerrors.EtcdFailure,
			"registry set service put failed, lease-id: %d, errmsg: %s", r.leaseID, err)
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

	if r.isInvalidClient() {
		logger.Debug("registry set trigger to recover.")
		if err := r.recoverConnection(ctx); err != nil {
			return err
		}
	}

	r.cliMu.RLock()
	defer r.cliMu.RUnlock()

	_, err := r.client.Put(ctx, key, value)
	if err != nil {
		return gerrors.New(gerrors.EtcdFailure, err.Error())
	}

	return nil
}

// Close Registry instance
func (r *Registry) Close() {
	r.cliMu.Lock()
	defer r.cliMu.Unlock()

	if r.keepAliveCancel != nil {
		r.keepAliveCancel()
	}

	if r.leaseID != 0 {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		r.client.Revoke(ctx, r.leaseID)
	}

	r.wg.Wait()
	logger.Debug("registry closed")
}

// GetRootKey returns the root key of the registry
func (r *Registry) GetRootKey() string {
	return r.rootKey
}

func (r *Registry) createKeepAlive() error {
	// NOTE: keepAlive must use the context without timeout.
	keepAliveCtx, cancel := context.WithCancel(context.Background())
	r.keepAliveCancel = cancel
	keepAliveResp, err := r.client.KeepAlive(keepAliveCtx, r.leaseID)
	if err != nil {
		r.client.Close()
		return gerrors.NewE(gerrors.EtcdFailure, err)
	}

	logger.Debug("registry start keepalive monitor, leaseID: %d", r.leaseID)

	r.wg.Add(1)
	go func() {
		defer r.wg.Done()
		r.handleKeepalive(keepAliveResp)
	}()

	return nil
}

func (r *Registry) isInvalidClient() bool {
	r.cliMu.RLock()
	defer r.cliMu.RUnlock()
	return r.client == nil || r.leaseID == 0
}

func (r *Registry) renewalLease(ctx context.Context) error {
	r.cliMu.Lock()
	defer r.cliMu.Unlock()

	resp, err := r.client.TimeToLive(ctx, r.leaseID)
	if err != nil {
		logger.Warn("failed to retrieve the lease, need to grant a new lease, errmsg: %s", err)
		return gerrors.New(gerrors.EtcdFailure, "failed to retrieve the lease")
	}

	if resp.TTL <= 0 {
		logger.Warn("registry lease expired, need to grant a new lease, TTL:%d, errmsg: %s", resp.TTL, err)
		return gerrors.New(gerrors.EtcdFailure, "need to grant a new lease")
	}

	return r.createKeepAlive()
}

func (r *Registry) recoverConnection(ctx context.Context) error {
	if r.isInvalidClient() {
		logger.Warn("registry invalid connection, need to grant a new lease.")
		return r.grant(ctx)
	}

	// renewal lease
	if err := r.renewalLease(ctx); err != nil {
		logger.Warn("failed to renewal lease, errmsg: %s", err)
		// create new lease
		return r.grant(ctx)
	}

	return nil
}
