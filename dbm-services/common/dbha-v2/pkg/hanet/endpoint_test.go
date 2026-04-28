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

package hanet_test

import (
	"testing"

	"dbm-services/common/dbha-v2/pkg/hanet"
)

func TestEndpoint(t *testing.T) {
	epoint, err := hanet.NewEndpoint("tcp://127.0.0.1:3306")
	if err != nil {
		t.Fatalf("create endpoint failed, %v", err)
	}

	if epoint.Proto != "tcp" {
		t.Fatalf("unidentified schema(%s)", epoint.Proto)
	}

	if epoint.Host != "127.0.0.1" {
		t.Fatalf("unidentified host(%s)", epoint.Host)
	}

	if epoint.Port != 3306 {
		t.Fatalf("unidentified port(%d)", epoint.Port)
	}
}

func TestEndpoints(t *testing.T) {
	epoints, err := hanet.NewEndpoints("tcp://127.0.0.1:3306;tcp6://127.0.0.2:3308")
	if err != nil {
		t.Fatalf("create endpoints failed, %v", err)
	}

	if len(epoints) != 2 {
		t.Fatalf("create endpoints failed, invalid endpoint count(%d)", len(epoints))
	}

	if epoints[0].Proto != "tcp" {
		t.Fatalf("unidentified schema(%s)", epoints[0].Proto)
	}

	if epoints[0].Host != "127.0.0.1" {
		t.Fatalf("unidentified host(%s)", epoints[0].Host)
	}

	if epoints[0].Port != 3306 {
		t.Fatalf("unidentified port(%d)", epoints[0].Port)
	}

	if epoints[1].Proto != "tcp6" {
		t.Fatalf("unidentified schema(%s)", epoints[1].Proto)
	}

	if epoints[1].Host != "127.0.0.2" {
		t.Fatalf("unidentified host(%s)", epoints[1].Host)
	}

	if epoints[1].Port != 3308 {
		t.Fatalf("unidentified port(%d)", epoints[1].Port)
	}
}

func TestParseAcceptsThreeFormats(t *testing.T) {
	cases := []struct {
		name          string
		raw           string
		defaultScheme string
		wantProto     string
		wantHost      string
		wantPort      int
	}{
		{
			name:          "bare host:port uses default scheme",
			raw:           "127.0.0.1:3306",
			defaultScheme: "tcp",
			wantProto:     "tcp",
			wantHost:      "127.0.0.1",
			wantPort:      3306,
		},
		{
			name:          "tcp scheme is preserved",
			raw:           "tcp://127.0.0.1:3306",
			defaultScheme: "http",
			wantProto:     "tcp",
			wantHost:      "127.0.0.1",
			wantPort:      3306,
		},
		{
			name:          "http scheme is preserved",
			raw:           "http://127.0.0.1:50080",
			defaultScheme: "tcp",
			wantProto:     "http",
			wantHost:      "127.0.0.1",
			wantPort:      50080,
		},
		{
			name:          "https scheme is preserved",
			raw:           "https://127.0.0.2:50080",
			defaultScheme: "http",
			wantProto:     "https",
			wantHost:      "127.0.0.2",
			wantPort:      50080,
		},
		{
			name:          "bare host:port with http default",
			raw:           "127.0.0.1:2379",
			defaultScheme: "http",
			wantProto:     "http",
			wantHost:      "127.0.0.1",
			wantPort:      2379,
		},
		{
			name:          "ipv6 bare with brackets",
			raw:           "[::1]:3306",
			defaultScheme: "tcp",
			wantProto:     "tcp",
			wantHost:      "::1",
			wantPort:      3306,
		},
		{
			name:          "ipv6 explicit tcp scheme",
			raw:           "tcp://[2001:db8::1]:3307",
			defaultScheme: "http",
			wantProto:     "tcp",
			// url.Parse + net.SplitHostPort strips brackets for schemed URLs.
			wantHost: "2001:db8::1",
			wantPort: 3307,
		},
		{
			name:          "ipv6 http scheme",
			raw:           "http://[::1]:50080",
			defaultScheme: "tcp",
			wantProto:     "http",
			// url.Parse + net.SplitHostPort strips brackets for schemed URLs.
			wantHost: "::1",
			wantPort: 50080,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			ep, err := hanet.Parse(tc.raw, tc.defaultScheme)
			if err != nil {
				t.Fatalf("parse(%s) failed, errmsg: %s", tc.raw, err)
			}
			if ep.Proto != tc.wantProto {
				t.Fatalf("proto = %s, want %s", ep.Proto, tc.wantProto)
			}
			if ep.Host != tc.wantHost {
				t.Fatalf("host = %s, want %s", ep.Host, tc.wantHost)
			}
			if ep.Port != tc.wantPort {
				t.Fatalf("port = %d, want %d", ep.Port, tc.wantPort)
			}
		})
	}
}

func TestParseRejectsInvalid(t *testing.T) {
	cases := []struct {
		name string
		raw  string
	}{
		{name: "empty", raw: ""},
		{name: "whitespace only", raw: "   "},
		{name: "missing port", raw: "127.0.0.1"},
		{name: "non-numeric port", raw: "127.0.0.1:abc"},
		{name: "scheme without host", raw: "http://"},
		{name: "scheme without port", raw: "http://127.0.0.1"},
		{name: "ipv6 missing port", raw: "[::1]"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := hanet.Parse(tc.raw, "tcp"); err == nil {
				t.Fatalf("expected error for raw(%q), got nil", tc.raw)
			}
		})
	}
}

func TestParseListMixedSchemes(t *testing.T) {
	endpoints, err := hanet.ParseList("127.0.0.1:2379;http://127.0.0.2:2379;https://127.0.0.3:2380", "http")
	if err != nil {
		t.Fatalf("parse list failed, errmsg: %s", err)
	}
	if got := len(endpoints); got != 3 {
		t.Fatalf("endpoint count = %d, want 3", got)
	}
	if endpoints[0].Proto != "http" || endpoints[0].URL() != "http://127.0.0.1:2379" {
		t.Fatalf("first endpoint = %+v, want default http scheme", endpoints[0])
	}
	if endpoints[1].Proto != "http" {
		t.Fatalf("second endpoint proto = %s, want http", endpoints[1].Proto)
	}
	if endpoints[2].Proto != "https" {
		t.Fatalf("third endpoint proto = %s, want https", endpoints[2].Proto)
	}

	urls := hanet.ToURLs(endpoints)
	if len(urls) != 3 || urls[2] != "https://127.0.0.3:2380" {
		t.Fatalf("ToURLs = %v, want full scheme://host:port forms", urls)
	}

	hostPorts := hanet.ToHostPorts(endpoints)
	wanted := []string{"127.0.0.1:2379", "127.0.0.2:2379", "127.0.0.3:2380"}
	for i, want := range wanted {
		if hostPorts[i] != want {
			t.Fatalf("ToHostPorts[%d] = %s, want %s", i, hostPorts[i], want)
		}
	}
}

func TestEndpointAddrAndURL(t *testing.T) {
	ep, err := hanet.Parse("tcp://127.0.0.10:8080", "tcp")
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if got := ep.Addr(); got != "127.0.0.10:8080" {
		t.Fatalf("Addr() = %s, want 127.0.0.10:8080", got)
	}
	if got := ep.HostPort(); got != "127.0.0.10:8080" {
		t.Fatalf("HostPort() = %s, want 127.0.0.10:8080", got)
	}
	if got := ep.URL(); got != "tcp://127.0.0.10:8080" {
		t.Fatalf("URL() = %s, want tcp://127.0.0.10:8080", got)
	}
}
