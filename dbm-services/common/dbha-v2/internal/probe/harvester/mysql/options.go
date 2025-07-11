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

// Option databases option
type Option interface {
	apply(*mySqlOptions)
}

type mySqlOptions struct {
	user           string
	password       string
	host           string
	port           int
	reportInterval int
	instanceName   string
	outputFile     string
}

var defaultMySqlOptions = mySqlOptions{}

type funcMySqlOptions struct {
	f func(opt *mySqlOptions)
}

func (fdo *funcMySqlOptions) apply(opt *mySqlOptions) {
	fdo.f(opt)
}

// OptionUser initialize user
func OptionUser(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.user = val
		},
	}
}

// OptionReportInterval initialize ReportInterval
func OptionReportInterval(val int) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.reportInterval = val
		},
	}
}

// OptionHost initialize host
func OptionHost(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.host = val
		},
	}
}

// OptionPort initialize port
func OptionPort(val int) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.port = val
		},
	}
}

// OptionPassword initialize password
func OptionPassword(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.password = val
		},
	}
}

// OptionInstanceName initialize instance name
func OptionInstanceName(val string) *funcMySqlOptions {
	return &funcMySqlOptions{
		f: func(opt *mySqlOptions) {
			opt.instanceName = val
		},
	}
}
