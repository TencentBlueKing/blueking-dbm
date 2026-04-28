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
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
)

// ParseEtcdEndpoints normalizes a ";" separated etcd endpoint configuration
// (host:port, http://host:port, https://host:port) into the URL form expected
// by the etcd client. Default scheme is selected by TLS mode:
//
//   - TLS disabled: host:port => http://host:port
//   - TLS enabled: host:port => https://host:port
//
// Empty input returns InvalidConfiguration since discovery endpoint is mandatory.
func ParseEtcdEndpoints(raw string, tlsEnabled bool) ([]string, error) {
	if strings.TrimSpace(raw) == "" {
		return nil, gerrors.New(gerrors.InvalidConfiguration, "discovery endpoint is required")
	}

	defaultScheme := "http"
	if tlsEnabled {
		defaultScheme = "https"
	}

	endpoints, err := hanet.ParseList(raw, defaultScheme)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid discovery endpoint, errmsg: %s", err)
	}

	for _, endpoint := range endpoints {
		switch strings.ToLower(endpoint.Proto) {
		case "http", "https":
			continue
		default:
			return nil, gerrors.Newf(
				gerrors.InvalidConfiguration,
				"invalid discovery endpoint scheme, scheme: %s, use host:port or http://host:port or https://host:port",
				endpoint.Proto,
			)
		}
	}
	return hanet.ToURLs(endpoints), nil
}
