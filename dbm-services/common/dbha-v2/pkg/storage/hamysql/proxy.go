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

package hamysql

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/jmoiron/sqlx"
)

// Proxy represents a mysql proxy client
type Proxy struct {
	db               *sqlx.DB
	ip               string
	port             int
	user             string
	password         string
	proto            string
	timeout          int
	maxAllowedPacket int
}

// NewProxy creates a new Proxy client
func NewProxy(ip string, port int, user string, password string) (*Proxy, error) {
	proxy := &Proxy{
		ip:               ip,
		port:             port,
		user:             user,
		password:         password,
		proto:            "tcp",
		timeout:          5,
		maxAllowedPacket: 4 * 1024 * 1024,
	}

	config := fmt.Sprintf("%s:%s@%s(%s:%d)/?timeout=%ds&maxAllowedPacket=%d",
		proxy.user,
		proxy.password,
		proxy.proto,
		proxy.ip,
		proxy.port,
		proxy.timeout,
		proxy.maxAllowedPacket)

	db, err := sqlx.Open("mysql", config)
	if err != nil {
		logger.Error("Failed to connect proxy(%s:%d), errmsg: %s", proxy.ip, proxy.port, err.Error())
		return nil, err
	}
	if _, err = db.Queryx("select version();"); err != nil {
		logger.Error("Check that the connection to proxy(%s:%d) is abnormal, errmsg: %s.",
			proxy.ip, proxy.port, err.Error())
		return nil, err
	}

	proxy.db = db
	return proxy, nil
}

// DB returns the underlying sqlx.DB
func (proxy Proxy) DB() *sqlx.DB {
	return proxy.db
}

// Host returns the host of the proxy
func (proxy Proxy) Host() string {
	return proxy.ip
}

// Port returns the adminport of the proxy
func (proxy Proxy) Port() int {
	return proxy.port
}
