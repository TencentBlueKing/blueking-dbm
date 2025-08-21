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
	"context"

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.etcd.io/etcd/client/v3/concurrency"
)

type ConcurrencyElection interface {
	// Campaign During the election process,
	// the Campagin will remain blocked until it's elected as the leader.
	Campaign(ctx context.Context) error
	Close()
	Done() <-chan struct{}
}

type concurrencyElection struct {
	etcdCli  *clientv3.Client
	session  *concurrency.Session
	election *concurrency.Election
	key      string
}

func (ce *concurrencyElection) Campaign(ctx context.Context) error {
	return ce.election.Campaign(ctx, ce.key)
}

func (ce *concurrencyElection) Close() {
	ce.session.Close()
	ce.etcdCli.Close()
}

func (ce *concurrencyElection) Done() <-chan struct{} {
	return ce.session.Done()
}
