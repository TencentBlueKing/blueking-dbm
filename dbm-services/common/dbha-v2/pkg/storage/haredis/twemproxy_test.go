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
)

func TestNewTwemproxyAdminClient_emptyIP(t *testing.T) {
	_, err := NewTwemproxyAdminClient(OptionPort(50000))
	if err == nil {
		t.Fatal("expected error when ip is empty")
	}
	var ge *gerrors.Error
	if !errors.As(err, &ge) || !ge.HasCode(gerrors.InvalidParameter) {
		t.Fatalf("expected InvalidParameter, got: %v", err)
	}
}

func TestNewTwemproxyAdminClient_invalidPort(t *testing.T) {
	_, err := NewTwemproxyAdminClient(OptionIP("127.0.0.1"), OptionPort(0))
	if err == nil {
		t.Fatal("expected error when port is invalid")
	}
	var ge *gerrors.Error
	if !errors.As(err, &ge) || !ge.HasCode(gerrors.InvalidParameter) {
		t.Fatalf("expected InvalidParameter, got: %v", err)
	}
}

func TestNewTwemproxyAdminClient_defaultOptions(t *testing.T) {
	cli, err := NewTwemproxyAdminClient(OptionIP("127.0.0.1"), OptionPort(50000))
	if err != nil {
		t.Fatalf("unexpected NewTwemproxyAdminClient error: %s", err.Error())
	}

	if cli.opts.dialTimeout != defaultTwemproxyAdminDialTimeout {
		t.Fatalf("dialTimeout: got %s, want %s", cli.opts.dialTimeout, defaultTwemproxyAdminDialTimeout)
	}
	if cli.opts.readTimeout != defaultTwemproxyAdminDeadline {
		t.Fatalf("readTimeout: got %s, want %s", cli.opts.readTimeout, defaultTwemproxyAdminDeadline)
	}
	if cli.opts.writeTimeout != defaultTwemproxyAdminDeadline {
		t.Fatalf("writeTimeout: got %s, want %s", cli.opts.writeTimeout, defaultTwemproxyAdminDeadline)
	}
	if cli.deadline() != defaultTwemproxyAdminDeadline {
		t.Fatalf("deadline: got %s, want %s", cli.deadline(), defaultTwemproxyAdminDeadline)
	}
}

func TestNewTwemproxyAdminClient_overrideOptions(t *testing.T) {
	cli, err := NewTwemproxyAdminClient(
		OptionIP("192.168.0.1"),
		OptionPort(22122),
		OptionDialTimeout(3*time.Second),
		OptionReadWriteTimeout(2*time.Second),
	)
	if err != nil {
		t.Fatalf("unexpected NewTwemproxyAdminClient error: %s", err.Error())
	}

	if cli.opts.dialTimeout != 3*time.Second {
		t.Fatalf("dialTimeout: got %s, want 3s", cli.opts.dialTimeout)
	}
	if cli.opts.readTimeout != 2*time.Second || cli.opts.writeTimeout != 2*time.Second {
		t.Fatalf("read/write timeout: got %s/%s, want 2s/2s",
			cli.opts.readTimeout, cli.opts.writeTimeout)
	}
	if cli.deadline() != 2*time.Second {
		t.Fatalf("deadline: got %s, want 2s", cli.deadline())
	}
}

func TestTwemproxyAdminClientAddr(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		ip   string
		port int
		want string
	}{
		{name: "ipv4", ip: "127.0.0.1", port: 50000, want: "127.0.0.1:50000"},
		{name: "ipv6", ip: "2001:db8::1", port: 50000, want: "[2001:db8::1]:50000"},
		{name: "ipv6 loopback", ip: "::1", port: 22122, want: "[::1]:22122"},
		{name: "hostname", ip: "twemproxy.local", port: 50000, want: "twemproxy.local:50000"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			cli, err := NewTwemproxyAdminClient(OptionIP(tc.ip), OptionPort(tc.port))
			if err != nil {
				t.Fatalf("unexpected NewTwemproxyAdminClient error: %s", err.Error())
			}
			got := cli.addr()
			if got != tc.want {
				t.Fatalf("addr() = %q, want %q", got, tc.want)
			}
		})
	}
}
