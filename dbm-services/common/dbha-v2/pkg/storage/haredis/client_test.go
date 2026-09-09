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
	"errors"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/go-redis/redis/v8"
)

func TestNewClient_emptyIP(t *testing.T) {
	_, err := NewClient(OptionPort(6379))
	if err == nil {
		t.Fatal("expected error when ip is empty")
	}
	var ge *gerrors.Error
	if !errors.As(err, &ge) || !ge.HasCode(gerrors.InvalidParameter) {
		t.Fatalf("expected InvalidParameter, got: %v", err)
	}
}

func TestNewClient_invalidPort(t *testing.T) {
	_, err := NewClient(OptionIP("127.0.0.1"), OptionPort(0))
	if err == nil {
		t.Fatal("expected error when port is invalid")
	}
	var ge *gerrors.Error
	if !errors.As(err, &ge) || !ge.HasCode(gerrors.InvalidParameter) {
		t.Fatalf("expected InvalidParameter, got: %v", err)
	}
}

func TestNewClient_appliesOptions(t *testing.T) {
	cli, err := NewClient(
		OptionIP("192.168.0.1"),
		OptionPort(6380),
		OptionPassword("secret"),
		OptionDB(1),
		OptionDialTimeout(3*time.Second),
		OptionReadWriteTimeout(10*time.Second),
	)
	if err != nil {
		t.Fatalf("unexpected NewClient error: %s", err.Error())
	}
	defer cli.Close()

	if cli.Host() != "192.168.0.1" {
		t.Fatalf("host: got %s, want 192.168.0.1", cli.Host())
	}
	if cli.Port() != 6380 {
		t.Fatalf("port: got %d, want 6380", cli.Port())
	}
	if cli.opts.password != "secret" {
		t.Fatalf("password: got %s, want secret", cli.opts.password)
	}
	if cli.opts.db != 1 {
		t.Fatalf("db: got %d, want 1", cli.opts.db)
	}
	if cli.opts.dialTimeout != 3*time.Second {
		t.Fatalf("dialTimeout: got %s, want 3s", cli.opts.dialTimeout)
	}
	if cli.opts.readTimeout != 10*time.Second || cli.opts.writeTimeout != 10*time.Second {
		t.Fatalf("read/write timeout: got %s/%s, want 10s/10s",
			cli.opts.readTimeout, cli.opts.writeTimeout)
	}
	if cli.DB() == nil {
		t.Fatal("expected non-nil underlying redis client")
	}
}

func TestOptionReadTimeoutAndWriteTimeout(t *testing.T) {
	cli, err := NewClient(
		OptionIP("127.0.0.1"),
		OptionPort(6379),
		OptionReadTimeout(2*time.Second),
		OptionWriteTimeout(4*time.Second),
	)
	if err != nil {
		t.Fatalf("unexpected NewClient error: %s", err.Error())
	}
	defer cli.Close()

	if cli.opts.readTimeout != 2*time.Second {
		t.Fatalf("readTimeout: got %s, want 2s", cli.opts.readTimeout)
	}
	if cli.opts.writeTimeout != 4*time.Second {
		t.Fatalf("writeTimeout: got %s, want 4s", cli.opts.writeTimeout)
	}
}

func TestClose_nilClient(t *testing.T) {
	var cli *Client
	cli.Close()
}

func TestRedisNil_matchesGoRedisNil(t *testing.T) {
	if RedisNil != redis.Nil {
		t.Fatal("RedisNil should be redis.Nil")
	}
	if !errors.Is(RedisNil, redis.Nil) {
		t.Fatal("errors.Is(RedisNil, redis.Nil) should be true")
	}
}
