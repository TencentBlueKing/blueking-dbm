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

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.etcd.io/etcd/client/v3/concurrency"
)

type ConcurrencyMutex interface {
	TryLock(ctx context.Context) error
	Unlock(ctx context.Context) error
}

type concurrencyMutex struct {
	session *concurrency.Session
	mutex   *concurrency.Mutex
	key     string
}

// Client etcd client
type Client struct {
	opts    options
	etcdCli *clientv3.Client
}

// NewClientWithOptions create etcd client with option
func NewClientWithOptions(opts ...Option) (*Client, error) {
	cli := &Client{
		opts: defaultOptions,
	}

	for _, opt := range opts {
		if err := opt.apply(&cli.opts); err != nil {
			return nil, err
		}
	}

	if cli.opts.serviceName != "" {
		cli.opts.registryRootKeyPrefix += "/" + cli.opts.serviceName
	}

	if cli.opts.serviceID != "" {
		cli.opts.registryRootKeyPrefix += "/" + cli.opts.serviceID
	}

	etcdCli, err := clientv3.New(cli.opts.Config())
	if err != nil {
		return nil, gerrors.Newf(gerrors.ComponentFailure, "%v", err)
	}
	cli.etcdCli = etcdCli

	return cli, nil
}

// OriginClient return the origin etcd client
func (c Client) OriginClient() *clientv3.Client {
	return c.etcdCli
}

// CreateRegistry create new etcd registry
func (c Client) CreateRegistry() (*Registry, error) {
	registry := &Registry{
		serviceId: c.opts.serviceID,
		rootKey:   c.opts.registryRootKeyPrefix,
		ttl:       defaultTTL,
		quit:      make(chan struct{}),
		eventChan: make(chan *RegistryEvent, c.opts.bufferMaxSize),
		client:    c.etcdCli,
	}

	return registry, nil
}

// CreateDiscovery create etcd discovery
func (c Client) CreateDiscovery() (*Discovery, error) {
	discovery := &Discovery{
		quit:   make(chan struct{}),
		client: c.etcdCli,
	}

	return discovery, nil
}

func (c Client) CreateMutex(key string) (ConcurrencyMutex, error) {
	session, err := concurrency.NewSession(c.etcdCli)
	if err != nil {
		return nil, gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	mu := &concurrencyMutex{
		session: session,
		key:     c.opts.registryRootKeyPrefix + "/" + key,
	}

	mu.mutex = concurrency.NewMutex(session, mu.key)
	return mu, nil
}

func (c *concurrencyMutex) TryLock(ctx context.Context) error {
	if err := c.mutex.TryLock(context.Background()); err != nil {
		return gerrors.Newf(gerrors.Failure, "%v", err)
	}
	return nil
}

func (c *concurrencyMutex) Unlock(ctx context.Context) error {
	if err := c.mutex.Unlock(context.Background()); err != nil {
		return gerrors.Newf(gerrors.Failure, "%v", err)
	}
	return nil
}
