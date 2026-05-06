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

package hanet

import (
	"fmt"
	"net"
	"net/url"
	"strconv"
	"strings"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// Endpoint represents a parsed network address. Three input formats are accepted:
//
//   - bare host:port (e.g. "127.0.0.1:3306")
//   - tcp://host:port
//   - http://host:port (or any scheme://host:port)
//
// When the input has no scheme, callers supply a default scheme that fits their
// transport (tcp for raw sockets / MySQL / Kafka, http for HTTP / etcd, etc.).
// The scheme is informational; the actual transport is decided by the consumer.
type Endpoint struct {
	Proto string `json:"proto"`
	Host  string `json:"host"`
	Port  int    `json:"port"`
}

// Parse parses a single address. When raw lacks a scheme, defaultScheme is used
// to populate Proto. Empty or port-less inputs return InvalidUrl.
func Parse(raw, defaultScheme string) (*Endpoint, error) {
	addr := strings.TrimSpace(raw)
	if addr == "" {
		return nil, gerrors.Newf(gerrors.InvalidUrl, "endpoint is empty")
	}

	scheme := strings.TrimSpace(defaultScheme)
	hostPort := addr

	// url.Parse silently drops path/query/fragment; only scheme and host:port are used.
	// e.g. "http://host:port/path?query=1" → Scheme="http", Host="host:port"
	if strings.Contains(addr, "://") {
		parsedURL, err := url.Parse(addr)
		if err != nil {
			return nil, gerrors.Newf(gerrors.InvalidUrl, "invalid endpoint(%s), errmsg: %s", raw, err)
		}

		scheme = parsedURL.Scheme
		hostPort = parsedURL.Host
		if hostPort == "" {
			return nil, gerrors.Newf(gerrors.InvalidUrl, "invalid endpoint(%s): missing host", raw)
		}
	}

	host, portStr, err := net.SplitHostPort(hostPort)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidUrl, "invalid endpoint(%s), errmsg: %s", raw, err)
	}

	port, err := strconv.Atoi(portStr)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidUrl, "invalid port in endpoint(%s), errmsg: %s", raw, err)
	}
	if port < 1 || port > 65535 {
		return nil, gerrors.Newf(gerrors.InvalidUrl, "port out of range in endpoint(%s): %d", raw, port)
	}

	return &Endpoint{
		Proto: scheme,
		Host:  host,
		Port:  port,
	}, nil
}

// ParseList parses a delimiter-separated address list (delimiter is constant.Delimiter,
// currently ";"). Each item passes through Parse with the same defaultScheme.
func ParseList(raw, defaultScheme string) ([]*Endpoint, error) {
	addr := strings.TrimSpace(raw)
	if addr == "" {
		return nil, gerrors.Newf(gerrors.InvalidUrl, "endpoint list is empty")
	}

	parts := strings.Split(addr, constant.Delimiter)
	endpoints := make([]*Endpoint, 0, len(parts))
	for _, part := range parts {
		ep, err := Parse(part, defaultScheme)
		if err != nil {
			return nil, err
		}
		endpoints = append(endpoints, ep)
	}
	return endpoints, nil
}

// NewEndpoint parses a single address using "tcp" as the default scheme. Kept for
// backward compatibility; new code should call Parse with an explicit default.
func NewEndpoint(dsn string) (*Endpoint, error) {
	return Parse(dsn, "tcp")
}

// NewEndpoints parses a ";" separated address list using "tcp" as the default
// scheme. Kept for backward compatibility; new code should call ParseList with
// an explicit default.
func NewEndpoints(dsns string) ([]*Endpoint, error) {
	return ParseList(dsns, "tcp")
}

// String returns the canonical scheme://host:port form.
func (e Endpoint) String() string {
	return fmt.Sprintf("%s://%s:%d", e.Proto, e.Host, e.Port)
}

// URL is an alias for String, used at call sites that expect a full URL form.
func (e Endpoint) URL() string {
	return e.String()
}

// Addr returns host:port (no scheme), suitable for net.Listen / http.Server.Addr.
func (e Endpoint) Addr() string {
	return net.JoinHostPort(e.Host, strconv.Itoa(e.Port))
}

// HostPort is an alias for Addr, used at call sites that emphasize the host:port form.
func (e Endpoint) HostPort() string {
	return e.Addr()
}

// ToURLs returns scheme://host:port for each endpoint as a string slice.
func ToURLs(endpoints []*Endpoint) []string {
	out := make([]string, len(endpoints))
	for i, ep := range endpoints {
		out[i] = ep.URL()
	}
	return out
}

// ToHostPorts returns host:port for each endpoint as a string slice.
func ToHostPorts(endpoints []*Endpoint) []string {
	out := make([]string, len(endpoints))
	for i, ep := range endpoints {
		out[i] = ep.HostPort()
	}
	return out
}
