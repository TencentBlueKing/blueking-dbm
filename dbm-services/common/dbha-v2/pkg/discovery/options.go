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
	"crypto/tls"
	"crypto/x509"
	"os"
	"path/filepath"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.uber.org/zap"
)

const (
	defaultChannelBuffMaxSize    = 1024
	defaultTTL                   = 6
	defaultMaxUnaryRetries       = 3
	defaultDialTimeout           = 5 * time.Second
	defaultAutoSyncInterval      = 60 * time.Second
	defaultKeepAliveTime         = 30 * time.Second
	defaultKeepAliveTimeout      = 10 * time.Second
	defaultRegistryRootKeyPrefix = "/dbha/registry"
)

var (
	// ErrNoValidCACerts is returned when trustedCAFile contains no valid CA certificates.
	ErrNoValidCACerts = gerrors.New(gerrors.InvalidParameter, "no valid CA certs in trustedCAFile")

	// ErrServiceIDRequired indicates service-id is required.
	ErrServiceIDRequired = gerrors.New(gerrors.InvalidParameter, "service-id is required")

	// ErrCertFileEmpty indicates certFile cannot be empty.
	ErrCertFileEmpty = gerrors.New(gerrors.InvalidParameter, "certFile cannot be empty")
	// ErrCertFileNotAbsolutePath indicates certFile must be an absolute path.
	ErrCertFileNotAbsolutePath = gerrors.New(gerrors.InvalidParameter, "certFile must be absolute path")

	// ErrKeyFileEmpty indicates keyFile cannot be empty.
	ErrKeyFileEmpty = gerrors.New(gerrors.InvalidParameter, "keyFile cannot be empty")
	// ErrKeyFileNotAbsolutePath indicates keyFile must be an absolute path.
	ErrKeyFileNotAbsolutePath = gerrors.New(gerrors.InvalidParameter, "keyFile must be absolute path")

	// ErrTrustedCAFileNotAbsolutePath indicates trustedCAFile must be an absolute path when set.
	ErrTrustedCAFileNotAbsolutePath = gerrors.New(
		gerrors.InvalidParameter,
		"trustedCAFile must be absolute path when set",
	)
)

// Option applies custom settings to discovery client options.
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
	maxUnaryRetries:       defaultMaxUnaryRetries,
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
	maxUnaryRetries       uint
	Logger                *zap.Logger

	// TLS: when certFile and keyFile are both set, use TLS for etcd connection.
	certFile      string
	keyFile       string
	trustedCAFile string
	tlsConfig     *tls.Config
}

func (o options) Config() (clientv3.Config, error) {
	cfg := clientv3.Config{
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

		// MaxUnaryRetries is the maximum number of retries for unary RPCs.
		MaxUnaryRetries: o.maxUnaryRetries,

		// Logger export the gRPC log into the custom.
		Logger: o.Logger,
	}

	if o.certFile != "" && o.keyFile != "" {
		if o.tlsConfig != nil {
			cfg.TLS = o.tlsConfig
		} else {
			tlsCfg, err := buildTLSConfig(o.certFile, o.keyFile, o.trustedCAFile)
			if err != nil {
				return clientv3.Config{}, err
			}
			cfg.TLS = tlsCfg
		}
	}

	return cfg, nil
}

// buildTLSConfig builds *tls.Config from cert/key and optional CA file.
func buildTLSConfig(certFile, keyFile, trustedCAFile string) (*tls.Config, error) {
	cert, err := tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		return nil, err
	}

	cfg := &tls.Config{
		Certificates: []tls.Certificate{cert},
		MinVersion:   tls.VersionTLS12,
	}

	if trustedCAFile != "" {
		data, err := os.ReadFile(trustedCAFile)
		if err != nil {
			return nil, err
		}
		pool := x509.NewCertPool()
		if !pool.AppendCertsFromPEM(data) {
			return nil, ErrNoValidCACerts
		}
		cfg.RootCAs = pool
	}

	return cfg, nil
}

type funcOptions struct {
	f func(opt *options) error
}

func (fdo *funcOptions) apply(opt *options) error {
	return fdo.f(opt)
}

// OptionUser sets etcd username for authentication.
func OptionUser(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.user = val
			return nil
		},
	}
}

// OptionPassword sets etcd password for authentication.
func OptionPassword(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.password = val
			return nil
		},
	}
}

// OptionBufferMaxSize sets the max buffered event size for watchers.
func OptionBufferMaxSize(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.bufferMaxSize = val
			return nil
		},
	}
}

// OptionTTL sets service registration TTL; values below defaultTTL fallback to defaultTTL.
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

// OptionServiceID sets the unique service ID used by registry and election keys.
func OptionServiceID(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.serviceID = val
			if opt.serviceID == "" {
				return ErrServiceIDRequired
			}

			return nil
		},
	}
}

// OptionServiceName sets service name and affects the registry root path.
func OptionServiceName(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.serviceName = val
			return nil
		},
	}
}

// OptionEndpoints appends etcd endpoints for client connections.
func OptionEndpoints(epoints []string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.endpoints = append(opt.endpoints, epoints...)
			return nil
		},
	}
}

// OptionDialTimeout sets the etcd dial timeout.
func OptionDialTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.dialTimeout = val
			return nil
		},
	}
}

// OptionAutoSyncInterval sets the endpoint auto-sync interval.
func OptionAutoSyncInterval(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.autoSyncInterval = val
			return nil
		},
	}
}

// OptionKeepAliveTime sets gRPC keepalive ping interval.
func OptionKeepAliveTime(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.keepAliveTime = val
			return nil
		},
	}
}

// OptionKeepAliveTimeout sets keepalive response timeout.
func OptionKeepAliveTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.keepAliveTimeout = val
			return nil
		},
	}
}

// OptionRegistryRootKeyPrefix sets the etcd root key prefix for registry-related keys.
func OptionRegistryRootKeyPrefix(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.registryRootKeyPrefix = val
			return nil
		},
	}
}

// OptionMaxUnaryRetries sets the maximum retries for unary RPC requests.
func OptionMaxUnaryRetries(val uint) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.maxUnaryRetries = val
			return nil
		},
	}
}

// OptionLogger sets the custom logger used by etcd client.
func OptionLogger(val *zap.Logger) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.Logger = val
			return nil
		},
	}
}

// OptionCertFile sets the client certificate file path for TLS. Used together with OptionKeyFile.
// Path must be non-empty and absolute.
func OptionCertFile(path string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			if path == "" {
				return ErrCertFileEmpty
			}
			if !filepath.IsAbs(path) {
				return ErrCertFileNotAbsolutePath
			}
			opt.certFile = path
			return nil
		},
	}
}

// OptionKeyFile sets the client private key file path for TLS. Used together with OptionCertFile.
// Path must be non-empty and absolute.
func OptionKeyFile(path string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			if path == "" {
				return ErrKeyFileEmpty
			}
			if !filepath.IsAbs(path) {
				return ErrKeyFileNotAbsolutePath
			}
			opt.keyFile = path
			return nil
		},
	}
}

// OptionTrustedCAFile sets the trusted CA certificate file for TLS (optional).
// If non-empty, path must be absolute.
func OptionTrustedCAFile(path string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			if path != "" && !filepath.IsAbs(path) {
				return ErrTrustedCAFileNotAbsolutePath
			}
			opt.trustedCAFile = path
			return nil
		},
	}
}
