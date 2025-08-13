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

type Option interface {
	apply(*options) error
}

var defaultOptions = options{
	bufferMaxSize:         defaultChannelBuffMaxSize,
	ttl:                   defaultTTL,
	dialTimeout:           defaultDialTimeout,
	autoSyncInterval:      defaultAutoSyncInterval,
	keepAliveTime:         defaultKeepAliveTime,
	keepAliveTimeout:      defaultKeepAliveTimeout,
	registryRootKeyPrefix: defaultRegistryRootKeyPrefix,
}

type options struct {
	user                  string
	password              string
	bufferMaxSize         int
	ttl                   int
	serviceID             string
	serviceName           string
	endpoints             []string
	dialTimeout           time.Duration
	autoSyncInterval      time.Duration
	keepAliveTime         time.Duration
	keepAliveTimeout      time.Duration
	registryRootKeyPrefix string
}

func (o options) Config() clientv3.Config {
	return clientv3.Config{
		Username:  o.user,
		Password:  o.password,
		Endpoints: o.endpoints,

		// DialTimeout is the timeout for failing to establish a connection.
		DialTimeout: o.dialTimeout,

		// AutoSyncInterval is the interval to update endpoints with its latest members.
		// 0 disables auto-sync. By default auto-sync is disabled.
		AutoSyncInterval: o.autoSyncInterval,

		// DialKeepAliveTime is the time after which client pings the server to see if
		// transport is alive.
		DialKeepAliveTime: o.keepAliveTime,

		// DialKeepAliveTimeout is the time that the client waits for a response for the
		// keep-alive probe. If the response is not received in this time, the connection is closed.
		DialKeepAliveTimeout: o.keepAliveTimeout,
	}
}

type funcOptions struct {
	f func(opt *options) error
}

func (fdo *funcOptions) apply(opt *options) error {
	return fdo.f(opt)
}

func OptionUser(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.user = val
			return nil
		},
	}
}

func OptionPassword(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.password = val
			return nil
		},
	}
}

func OptionBufferMaxSize(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.bufferMaxSize = val
			return nil
		},
	}
}

func OptionTTL(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			if val < defaultTTL {
				opt.ttl = defaultTTL
				return nil
			}

			opt.ttl = val
			return nil
		},
	}
}

func OptionServiceID(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.serviceID = val
			if opt.serviceID == "" {
				return gerrors.New(gerrors.InvalidParameter, "service-id is required")
			}

			return nil
		},
	}
}

func OptionServiceName(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.serviceName = val
			return nil
		},
	}
}

func OptionEndpoints(epoints []string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.endpoints = append(opt.endpoints, epoints...)
			return nil
		},
	}
}

func OptionDialTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.dialTimeout = val
			return nil
		},
	}
}

func OptionAutoSyncInterval(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.autoSyncInterval = val
			return nil
		},
	}
}

func OptionKeepAliveTime(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.keepAliveTime = val
			return nil
		},
	}
}

func OptionKeepAliveTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.keepAliveTimeout = val
			return nil
		},
	}
}

func OptionRegistryRootKeyPrefix(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.registryRootKeyPrefix = val
			return nil
		},
	}
}
