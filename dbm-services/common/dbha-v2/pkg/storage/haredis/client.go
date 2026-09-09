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

package haredis

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/go-redis/redis/v8"
)

// RedisNil is redis.Nil, re-exported so callers need not import go-redis.
var RedisNil = redis.Nil

// Client wraps a go-redis v8 instance client. It only opens a connection;
// typed commands stay in the caller, matching hamysql.
type Client struct {
	rdb  *redis.Client
	opts options
}

// NewClient creates a redis instance client.
func NewClient(opts ...Option) (*Client, error) {
	cli := &Client{}
	for _, opt := range opts {
		if err := opt.apply(&cli.opts); err != nil {
			return nil, err
		}
	}

	if cli.opts.ip == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "redis ip is empty")
	}
	if cli.opts.port <= 0 {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid redis port: %d", cli.opts.port)
	}

	cli.rdb = redis.NewClient(&redis.Options{
		Addr:         fmt.Sprintf("%s:%d", cli.opts.ip, cli.opts.port),
		Password:     cli.opts.password,
		DB:           cli.opts.db,
		DialTimeout:  cli.opts.dialTimeout,
		ReadTimeout:  cli.opts.readTimeout,
		WriteTimeout: cli.opts.writeTimeout,
		MaxRetries:   -1,
	})
	return cli, nil
}

// DB returns the underlying go-redis client.
func (c *Client) DB() *redis.Client {
	return c.rdb
}

// Host returns the configured redis IP.
func (c *Client) Host() string {
	return c.opts.ip
}

// Port returns the configured redis port.
func (c *Client) Port() int {
	return c.opts.port
}

// Close closes the underlying redis client.
func (c *Client) Close() {
	if c == nil || c.rdb == nil {
		return
	}
	_ = c.rdb.Close()
}
