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

package mysql

import (
	"dbm-services/common/dbha-v2/internal/probe/config"
	"fmt"
)

// Option is an option for MySQL probe.
type Option interface {
	apply(*mySqlOptions)
}

// mySqlOptions is the configuration of MySQL probe.
type mySqlOptions struct {
	user           string
	password       string
	reportInterval int
	host           string
	port           int
	instances      []config.InstanceConfig // support for multiple MySQL instances
}

var defaultMySqlOptions = mySqlOptions{}

type funcMySqlOptions struct {
	f func(opt *mySqlOptions)
}

func (fdo *funcMySqlOptions) apply(opt *mySqlOptions) {
	fdo.f(opt)
}

// OptionUser sets the user for MySQL probe.
func OptionUser(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.user = val
		},
	}
}

// OptionReportInterval sets the report interval for MySQL probe.
func OptionReportInterval(val int) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.reportInterval = val
		},
	}
}

// OptionHost sets the host for MySQL probe.
func OptionHost(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.host = val
		},
	}
}

// OptionPort sets the port for MySQL probe.
func OptionPort(val int) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.port = val
		},
	}
}

// OptionPassword sets the password for MySQL probe.
func OptionPassword(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.password = val
		},
	}
}

// OptionInstances sets multiple MySQL instances
func OptionInstances(instances []config.InstanceConfig) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.instances = instances
		},
	}
}

// OptionSingleInstance sets single MySQL instance
func OptionSingleInstance(host string, port int, user, password string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.host = host
			opt.port = port
			opt.user = user
			opt.password = password
			opt.instances = []config.InstanceConfig{
				{
					Host:     host,
					Port:     port,
					User:     user,
					Password: password,
					Name:     fmt.Sprintf("%s:%d", host, port),
				},
			}
		},
	}
}
