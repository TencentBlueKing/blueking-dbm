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

package haredis_test

import (
	"context"
	"errors"
	"log"
	"net"
	"os"
	"strconv"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haredis"
)

type redisTestConfig struct {
	host           string
	port           int
	password       string
	db             int
	dialTimeout    time.Duration
	commandTimeout time.Duration
}

func getRedisTestConfig(t *testing.T) redisTestConfig {
	t.Helper()

	host := os.Getenv("DBHA_REDIS_HOST")
	if host == "" {
		t.Skip("DBHA_REDIS_HOST is not set")
	}

	port, err := strconv.Atoi(os.Getenv("DBHA_REDIS_PORT"))
	if err != nil {
		t.Fatalf("invalid redis port(%s), errmsg(%s)", os.Getenv("DBHA_REDIS_PORT"), err)
	}

	db := 0
	if dbStr := os.Getenv("DBHA_REDIS_DB"); dbStr != "" {
		db, err = strconv.Atoi(dbStr)
		if err != nil {
			t.Fatalf("invalid redis db(%s), errmsg(%s)", dbStr, err)
		}
	}

	dialTimeout := 3 * time.Second
	if raw := os.Getenv("DBHA_REDIS_DIAL_TIMEOUT"); raw != "" {
		dialTimeout, err = time.ParseDuration(raw)
		if err != nil {
			t.Fatalf("invalid dial timeout(%s), errmsg(%s)", raw, err)
		}
	}

	commandTimeout := 10 * time.Second
	if raw := os.Getenv("DBHA_REDIS_COMMAND_TIMEOUT"); raw != "" {
		commandTimeout, err = time.ParseDuration(raw)
		if err != nil {
			t.Fatalf("invalid command timeout(%s), errmsg(%s)", raw, err)
		}
	}

	return redisTestConfig{
		host:           host,
		port:           port,
		password:       os.Getenv("DBHA_REDIS_PASSWORD"),
		db:             db,
		dialTimeout:    dialTimeout,
		commandTimeout: commandTimeout,
	}
}

func newTestClient(t *testing.T, cfg redisTestConfig) *haredis.Client {
	t.Helper()

	cli, err := haredis.NewClient(
		haredis.OptionIP(cfg.host),
		haredis.OptionPort(cfg.port),
		haredis.OptionPassword(cfg.password),
		haredis.OptionDB(cfg.db),
		haredis.OptionDialTimeout(cfg.dialTimeout),
		haredis.OptionReadWriteTimeout(cfg.commandTimeout),
	)
	if err != nil {
		t.Fatalf("failed to create redis client, errmsg: %s", err.Error())
	}
	return cli
}

func TestNewClientPing(t *testing.T) {
	cfg := getRedisTestConfig(t)
	log.Println("host:", cfg.host)
	log.Println("port:", cfg.port)
	log.Println("db:", cfg.db)

	cli := newTestClient(t, cfg)
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), cfg.commandTimeout)
	defer cancel()

	if err := cli.DB().Ping(ctx).Err(); err != nil {
		t.Fatalf("failed to ping redis(%s:%d), errmsg: %s", cfg.host, cfg.port, err.Error())
	}
}

func TestGetMissingKeyIsRedisNil(t *testing.T) {
	cfg := getRedisTestConfig(t)
	cli := newTestClient(t, cfg)
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), cfg.commandTimeout)
	defer cancel()

	_, err := cli.DB().Get(ctx, "dbha-v2:haredis:missing-key").Result()
	if !errors.Is(err, haredis.RedisNil) {
		t.Fatalf("expected RedisNil for missing key, got: %v", err)
	}
}

func TestOptionReadWriteTimeout(t *testing.T) {
	cfg := getRedisTestConfig(t)

	pingCli := newTestClient(t, cfg)
	defer pingCli.Close()

	pingCtx, pingCancel := context.WithTimeout(context.Background(), cfg.commandTimeout)
	defer pingCancel()
	if err := pingCli.DB().Ping(pingCtx).Err(); err != nil {
		t.Fatalf("redis(%s:%d) is unreachable, errmsg: %s", cfg.host, cfg.port, err.Error())
	}

	// PING is available on Redis / Tendis / Predixy. A timeout shorter than
	// one RTT makes the socket deadline fire without needing a blocking command.
	rwTimeout := time.Microsecond
	cli, err := haredis.NewClient(
		haredis.OptionIP(cfg.host),
		haredis.OptionPort(cfg.port),
		haredis.OptionPassword(cfg.password),
		haredis.OptionDB(cfg.db),
		haredis.OptionDialTimeout(cfg.dialTimeout),
		haredis.OptionReadWriteTimeout(rwTimeout),
	)
	if err != nil {
		t.Fatalf("failed to create redis client, errmsg: %s", err.Error())
	}
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	start := time.Now()
	err = cli.DB().Ping(ctx).Err()
	elapsed := time.Since(start)
	log.Printf("read/write timeout ping err=%v, elapsed=%s", err, elapsed)
	if err == nil {
		t.Fatal("expected PING to fail after ReadWriteTimeout")
	}
	if !isTimeoutErr(err) {
		t.Fatalf("expected i/o timeout, got: %v", err)
	}
}

func isTimeoutErr(err error) bool {
	if err == nil {
		return false
	}
	if os.IsTimeout(err) || errors.Is(err, context.DeadlineExceeded) {
		return true
	}
	var ne net.Error
	return errors.As(err, &ne) && ne.Timeout()
}

func TestDialTimeout(t *testing.T) {
	// TEST-NET-1 (RFC 5737) should not be routable; built from octets to avoid CI IP literals.
	start := time.Now()
	cli, err := haredis.NewClient(
		haredis.OptionIP(net.IPv4(192, 0, 2, 1).String()),
		haredis.OptionPort(6379),
		haredis.OptionDialTimeout(1*time.Second),
		haredis.OptionReadWriteTimeout(1*time.Second),
	)
	if err != nil {
		t.Fatalf("NewClient should not fail before the first command, errmsg: %s", err.Error())
	}
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	pingErr := cli.DB().Ping(ctx).Err()
	elapsed := time.Since(start)
	log.Printf("dial timeout ping err=%v, elapsed=%s", pingErr, elapsed)
	if pingErr == nil {
		t.Fatal("expected ping to fail against an unreachable address")
	}
}
