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

	"dbm-services/common/dbha-v2/pkg/gerrors"

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.etcd.io/etcd/client/v3/concurrency"
)

type ConcurrencyMutex interface {
	TryLock(ctx context.Context) error
	Unlock(ctx context.Context) error
	Close()
}

type concurrencyMutex struct {
	etcdCli *clientv3.Client
	session *concurrency.Session
	mutex   *concurrency.Mutex
	key     string
}

func (c *concurrencyMutex) TryLock(ctx context.Context) error {
	if err := c.mutex.TryLock(context.Background()); err != nil {
		return gerrors.Newf(gerrors.Failure, "%v", err)
	}
	return nil
}

func (c *concurrencyMutex) Unlock(ctx context.Context) error {
	if err := c.mutex.Unlock(context.Background()); err != nil {
		return gerrors.Newf(gerrors.Failure, "%v", err)
	}
	return nil
}

func (c *concurrencyMutex) Close() {
	c.session.Close()
	c.etcdCli.Close()
}
