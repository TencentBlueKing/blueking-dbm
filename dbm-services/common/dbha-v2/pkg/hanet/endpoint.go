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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"net/url"
	"strconv"
	"strings"
)

// Endpoint for parsing DSN addresses
type Endpoint struct {
	Proto string
	Host  string
	Port  int
}

// NewEndpoint create new endpoint by DSN
func NewEndpoint(dsn string) (*Endpoint, error) {
	parsedURL, err := url.Parse(dsn)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidURL, "invalid DSN(%s)", dsn)
	}

	epoint := &Endpoint{}
	epoint.Proto = parsedURL.Scheme
	epoint.Host = parsedURL.Hostname()
	port, err := strconv.Atoi(parsedURL.Port())
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidURL, "invalid port in DSN(%s)", dsn)
	}
	epoint.Port = port

	return epoint, nil
}

// NewEndpoints create a group endpoint by DSNs
//
// split with ';'
func NewEndpoints(dsns string) ([]*Endpoint, error) {
	epoints := []*Endpoint{}

	endpoints := strings.Split(dsns, ";")
	for _, endpoint := range endpoints {
		epoint, err := NewEndpoint(endpoint)
		if err != nil {
			return nil, err
		}
		epoints = append(epoints, epoint)
	}

	return epoints, nil
}
