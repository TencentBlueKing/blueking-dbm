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

package machine

import (
	"net"
	"testing"
)

func TestGetHost(t *testing.T) {
	ips, err := GetLocalIPs()
	if err != nil {
		t.Fatalf("failed to get local ips:%v", err)
	}

	for _, ip := range ips {
		t.Logf("local ip: %s", ip)
	}
}

func TestGetHostWithInterface(t *testing.T) {
	ip, err := GetLocalIPWithInterface("eth1")
	if err != nil {
		t.Fatalf("failed to get local ips:%v", err)
	}

	t.Logf("local ip: %s, eth1", ip)
}

func TestGetPrimaryLocalIPv4(t *testing.T) {
	ip, err := GetPrimaryLocalIPv4()
	if err != nil {
		t.Skipf("no physical ipv4 in test env, errmsg: %v", err)
	}
	parsed := net.ParseIP(ip)
	if parsed == nil || parsed.To4() == nil {
		t.Fatalf("expected valid IPv4, got: %q", ip)
	}
	t.Logf("primary local ipv4: %s", ip)
}

func TestHostFromEndpoint(t *testing.T) {
	cases := []struct {
		endpoint string
		want     string
		wantErr  bool
	}{
		{endpoint: "127.0.0.1:8080", want: "127.0.0.1"},
		{endpoint: "localhost", want: "localhost"},
		{endpoint: "[::1]:8080", want: "::1"},
		{endpoint: "", wantErr: true},
	}
	for _, tc := range cases {
		t.Run(tc.endpoint, func(t *testing.T) {
			got, err := HostFromEndpoint(tc.endpoint)
			if tc.wantErr {
				if err == nil {
					t.Fatal("expected error")
				}
				return
			}
			if err != nil {
				t.Fatalf("HostFromEndpoint failed, errmsg: %s", err)
			}
			if got != tc.want {
				t.Fatalf("HostFromEndpoint(%q) = %q, want %q", tc.endpoint, got, tc.want)
			}
		})
	}
}

// TestGetOutboundIP verifies the gen-config fallback path: primary local IPv4 first,
// then optional UDP route detection via a caller-provided host.
func TestGetOutboundIP(t *testing.T) {
	ip, err := GetOutboundIP("127.0.0.1")
	if err != nil {
		t.Skipf("outbound ip detection unavailable in test env, errmsg: %v", err)
	}
	if net.ParseIP(ip) == nil {
		t.Fatalf("GetOutboundIP returned invalid ip: %q", ip)
	}
	t.Logf("outbound ip: %s", ip)
}

func TestGetOutboundIP_NoDetectHostUsesPrimaryLocal(t *testing.T) {
	ip, err := GetOutboundIP("")
	if err != nil {
		t.Skipf("no primary local ipv4 in test env, errmsg: %v", err)
	}
	if net.ParseIP(ip) == nil || net.ParseIP(ip).To4() == nil {
		t.Fatalf("expected valid IPv4, got: %q", ip)
	}
}
