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

package storage

import "fmt"

type MySQLOption interface {
	apply(*mysqlOptions)
}

type mysqlOptions struct {
	endpoint      string
	user          string
	password      string
	database      string
	timeoutSecond int
}

func (o *mysqlOptions) buildDSN() string {
	dsn := fmt.Sprintf("%s:%s@tcp(%s)/%s", o.user, o.password, o.endpoint, o.database)

	if o.timeoutSecond > 0 {
		dsn = fmt.Sprintf("%s?timeout=%d", dsn, o.timeoutSecond)
	}

	return dsn
}

type funcMySQLOption struct {
	do func(*mysqlOptions)
}

func (f *funcMySQLOption) apply(opt *mysqlOptions) {
	f.do(opt)
}

func MySQLOptionTimeout(second int) *funcMySQLOption {
	return &funcMySQLOption{
		do: func(opt *mysqlOptions) {
			opt.timeoutSecond = second
		},
	}
}
