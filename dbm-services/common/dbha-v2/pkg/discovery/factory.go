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
	"dbm-services/common/dbha-v2/pkg/gerrors"

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.etcd.io/etcd/client/v3/concurrency"
)

type ConcurrencyMutex interface {
	TryLock(key string) error
	Unlock() error
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
	if c.opts.serviceID == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "service-id is required")
	}

	rootKey := c.opts.registryRootKeyPrefix
	if c.opts.serviceName != "" {
		rootKey += "/" + c.opts.serviceName
	}

	if c.opts.serviceID != "" {
		rootKey += "/" + c.opts.serviceID
	}

	registry := &Registry{
		serviceId: c.opts.serviceID,
		rootKey:   rootKey,
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

	mu := concurrency.NewMutex(session, key)

	return &concurrencyMutex{
		session: session,
		key:     key,
		mutex:   mu,
	}, nil
}

func (c *concurrencyMutex) TryLock(key string) error {
	return nil
}

func (c *concurrencyMutex) Unlock() error {
	return nil
}
