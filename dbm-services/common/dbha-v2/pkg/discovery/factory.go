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

const (
	etcdKeySegmentSelf     = "self"
	etcdKeySegmentMutex    = "mutex"
	etcdKeySegmentElection = "election/leader"
)

// Client etcd client
type Client struct {
	opts             options
	createEtcdClient func() (*clientv3.Client, error)
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

	cli.createEtcdClient = func() (*clientv3.Client, error) {
		etcdCli, err := clientv3.New(cli.opts.Config())
		if err != nil {
			return nil, gerrors.Newf(gerrors.EtcdFailure, "%v", err)
		}

		return etcdCli, nil
	}

	return cli, nil
}

// OriginClient return the origin etcd client
func (c Client) OriginClient() (*clientv3.Client, error) {
	return c.createEtcdClient()
}

// GetRegistryPrefix returns the etcd key prefix under which same-module instances register.
// Use with Discovery.GetWithPrefix / WatchWithPrefix to list or watch analysis instances.
func (c Client) GetRegistryPrefix() string {
	return c.opts.registryRootKeyPrefix
}

// GetSelfPrefix returns the etcd key prefix under which same-module instances register (self nodes).
// Full key for one instance is GetSelfPrefix() + "/" + serviceID.
// Use with GetWithPrefix to list all instances.
func (c Client) GetSelfPrefix() string {
	return c.opts.registryRootKeyPrefix + "/" + etcdKeySegmentSelf
}

// GetElectionPrefix returns the etcd key prefix for leader election.
//
//	Full key for one election is GetElectionPrefix() + "/" + name.
func (c Client) GetElectionPrefix() string {
	return c.opts.registryRootKeyPrefix + "/" + etcdKeySegmentElection
}

// CreateRegistry create new etcd registry
func (c Client) CreateRegistry() *Registry {
	rootKey := c.opts.registryRootKeyPrefix
	if c.opts.serviceID != "" {
		rootKey += "/" + etcdKeySegmentSelf + "/" + c.opts.serviceID
	}

	registry := &Registry{
		serviceID:        c.opts.serviceID,
		rootKey:          rootKey,
		ttl:              defaultTTL,
		createEtcdClient: c.createEtcdClient,
	}

	return registry
}

// CreateDiscovery create etcd discovery
func (c Client) CreateDiscovery() (*Discovery, error) {
	discovery := &Discovery{
		quit:             make(chan struct{}),
		createEtcdClient: c.createEtcdClient,
	}

	return discovery, nil
}

// CreateMutex returns concurrency mutex.
func (c Client) CreateMutex(key string) (ConcurrencyMutex, error) {
	etcdCli, err := c.createEtcdClient()
	if err != nil {
		return nil, err
	}

	session, err := concurrency.NewSession(etcdCli)
	if err != nil {
		return nil, gerrors.NewE(gerrors.EtcdFailure, err)
	}

	muKey := c.opts.registryRootKeyPrefix + "/" + etcdKeySegmentMutex + "/" + key
	mu := &concurrencyMutex{
		etcdCli: etcdCli,
		session: session,
		key:     muKey,
		mutex:   concurrency.NewMutex(session, muKey),
	}

	return mu, nil
}

// CreateElection returns concurrency election.
func (c Client) CreateElection(name string) (ConcurrencyElection, error) {
	etcdCli, err := c.createEtcdClient()
	if err != nil {
		return nil, err
	}

	session, err := concurrency.NewSession(etcdCli)
	if err != nil {
		return nil, gerrors.NewE(gerrors.EtcdFailure, err)
	}

	electionKey := c.opts.registryRootKeyPrefix + "/" + etcdKeySegmentElection + "/" + name

	election := &concurrencyElection{
		etcdCli:  etcdCli,
		session:  session,
		election: concurrency.NewElection(session, electionKey),
		key:      c.opts.serviceID,
	}

	return election, nil
}
