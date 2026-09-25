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
	"time"
)

// Option applies configuration to haredis client options.
type Option interface {
	apply(*options) error
}

type options struct {
	ip           string
	port         int
	password     string
	db           int
	dialTimeout  time.Duration
	readTimeout  time.Duration
	writeTimeout time.Duration
}

type funcOptions struct {
	f func(opt *options) error
}

func (fdo *funcOptions) apply(opt *options) error {
	return fdo.f(opt)
}

// OptionIP sets the redis server IP address.
func OptionIP(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.ip = val
			return nil
		},
	}
}

// OptionPort sets the redis server port.
func OptionPort(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.port = val
			return nil
		},
	}
}

// OptionPassword sets the redis password.
func OptionPassword(val string) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.password = val
			return nil
		},
	}
}

// OptionDB sets the redis logical database index.
func OptionDB(val int) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.db = val
			return nil
		},
	}
}

// OptionDialTimeout sets the redis connection establishment timeout.
func OptionDialTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.dialTimeout = val
			return nil
		},
	}
}

// OptionReadWriteTimeout sets both read and write timeouts.
func OptionReadWriteTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.readTimeout = val
			opt.writeTimeout = val
			return nil
		},
	}
}

// OptionReadTimeout sets the redis read timeout.
func OptionReadTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.readTimeout = val
			return nil
		},
	}
}

// OptionWriteTimeout sets the redis write timeout.
func OptionWriteTimeout(val time.Duration) *funcOptions {
	return &funcOptions{
		f: func(opt *options) error {
			opt.writeTimeout = val
			return nil
		},
	}
}
