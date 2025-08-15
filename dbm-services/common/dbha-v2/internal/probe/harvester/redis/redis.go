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

package redis

import (
	"context"

	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
)

const (
	Name    = "redis"
	Version = "v1.0.0"
)

type Redis struct {
	opts *redisOptions
}

func NewRedis(opts ...Option) *Redis {
	redisOpt := defaultRedisOptions

	for _, opt := range opts {
		opt.apply(&redisOpt)
	}

	return &Redis{
		opts: &redisOpt,
	}
}

func (r *Redis) Name() (string, error) {
	return Name, nil
}

func (r *Redis) Version() (string, error) {
	return Version, nil
}

func (r *Redis) Harvest(ctx context.Context) (chan *plugin.HarvestData, error) {
	return nil, nil
}

func (r *Redis) Close() error {
	return nil
}
