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

import (
	"dbm-services/common/dbha-v2/pkg/logger"
)

const NameDoris = "doris"

type DorisOption interface {
	apply(*dorisOptions)
}

type dorisOptions struct {
	endpoints     []string
	user          string
	password      string
	timeoutSecond int
}

type funcDorisOption struct {
	do func(*dorisOptions)
}

func (f *funcDorisOption) apply(opt *dorisOptions) {
	f.do(opt)
}

func DorisOptionTimeout(second int) *funcDorisOption {
	return &funcDorisOption{
		do: func(opt *dorisOptions) {
			opt.timeoutSecond = second
		},
	}
}

func NewDoris(endpoints []string, user, password string, opts ...DorisOption) (*Doris, error) {

	doris := &Doris{opts: &dorisOptions{}}

	for _, opt := range opts {
		opt.apply(doris.opts)
	}

	return doris, nil
}

type Doris struct {
	opts *dorisOptions
}

func (d *Doris) Save(data interface{}) error {

	logger.Debug("doris exporter save:%v", data)
	return nil
}

func (d *Doris) Close() {

}
