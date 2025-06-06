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
	"dbm-services/common/dbha-v2/pkg/logger"
	"fmt"
	"strings"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
)

const (
	defaultChannelBuffMaxSize    = 1024
	defaultTTL                   = 6
	defaultDialTimeout           = 5 * time.Second
	defaultAutoSyncInterval      = 60 * time.Second
	defaultKeepAliveTime         = 30 * time.Second
	defaultKeepAliveTimeout      = 10 * time.Second
	defaultRegistryRootKeyPrefix = "/dbha/registry"
)

// NewClient create etcd client
func NewClient(endpoints []string, user, password string) (*clientv3.Client, error) {

	user = strings.TrimSpace(user)
	password = strings.TrimSpace(password)

	if user == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "user is required")
	}

	if password == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "password is required")
	}

	if len(endpoints) == 0 {
		return nil, gerrors.New(gerrors.InvalidParameter, "endpoints is required")
	}

	cli, err := clientv3.New(clientv3.Config{
		Username:  user,
		Password:  password,
		Endpoints: endpoints,
		// DialTimeout is the timeout for failing to establish a connection.
		DialTimeout: defaultDialTimeout,
		// AutoSyncInterval is the interval to update endpoints with its latest members.
		// 0 disables auto-sync. By default auto-sync is disabled.
		AutoSyncInterval: defaultAutoSyncInterval,
		// DialKeepAliveTime is the time after which client pings the server to see if
		// transport is alive.
		DialKeepAliveTime: defaultKeepAliveTime,
		// DialKeepAliveTimeout is the time that the client waits for a response for the
		// keep-alive probe. If the response is not received in this time, the connection is closed.
		DialKeepAliveTimeout: defaultKeepAliveTimeout,
	})

	if err != nil {
		return nil, gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	return cli, nil
}

// NewRegistry create a new service registry
func NewRegistry(cli *clientv3.Client, serviceId string, ttl int64) (*Registry, error) {

	if cli == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "cli is nil")
	}

	if serviceId == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "service id is required")
	}

	if ttl < defaultTTL {
		logger.Warn("use the default ttl, input ttl:%d, default ttl:%d", ttl, defaultTTL)
		ttl = defaultTTL
	}

	registry := &Registry{
		serviceId: serviceId,
		rootKey:   fmt.Sprintf("%s/%s", defaultRegistryRootKeyPrefix, serviceId),
		ttl:       defaultTTL,
		quit:      make(chan struct{}),
		eventChan: make(chan *RegistryEvent, 1024),
		client:    cli,
	}

	return registry, nil
}

// NewDiscovery create a new discovery
func NewDiscovery(cli *clientv3.Client) (*Discovery, error) {

	if cli == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "cli is nil")
	}

	discovery := &Discovery{
		quit:   make(chan struct{}),
		client: cli,
	}

	return discovery, nil
}
