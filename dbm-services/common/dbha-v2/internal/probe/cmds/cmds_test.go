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

package cmds

import (
	"net"
	"testing"
)

func TestResolveGenConfigLocalIP_FallbackToOutbound(t *testing.T) {
	ip, err := resolveGenConfigLocalIP(
		"__no_such_interface_for_genconfig_test__",
		"127.0.0.1:19999",
	)
	if err != nil {
		t.Fatalf("resolveGenConfigLocalIP failed, errmsg: %s", err)
	}
	parsed := net.ParseIP(ip)
	if parsed == nil || parsed.To4() == nil {
		t.Fatalf("expected valid IPv4, got: %q", ip)
	}
}

func TestParseAdminEndpoints(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  []string
	}{
		{
			name:  "semicolon separated",
			input: "127.0.0.1:8080;127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "space separated",
			input: "127.0.0.1:8080 127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "mixed delimiters",
			input: "127.0.0.1:8080; 127.0.0.2:8080 127.0.0.3:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080", "127.0.0.3:8080"},
		},
		{
			name:  "newline separated",
			input: "127.0.0.1:8080\n127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "mixed with newline",
			input: "127.0.0.1:8080; 127.0.0.2:8080\n127.0.0.3:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080", "127.0.0.3:8080"},
		},
		{
			name:  "crlf separated",
			input: "127.0.0.1:8080\r\n127.0.0.2:8080",
			want:  []string{"127.0.0.1:8080", "127.0.0.2:8080"},
		},
		{
			name:  "trim and skip empty",
			input: " ; 127.0.0.1:8080;; ",
			want:  []string{"127.0.0.1:8080"},
		},
		{
			name:  "empty input",
			input: "",
			want:  nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := parseAdminEndpoints(tt.input)
			if len(got) != len(tt.want) {
				t.Fatalf("parseAdminEndpoints(%q) len = %d, want %d, got: %v", tt.input, len(got), len(tt.want), got)
			}
			for i := range tt.want {
				if got[i] != tt.want[i] {
					t.Fatalf("parseAdminEndpoints(%q)[%d] = %q, want %q", tt.input, i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestResolveGenConfigLocalIP_ExplicitInterface(t *testing.T) {
	iface, err := net.InterfaceByName("lo")
	if err != nil {
		t.Skipf("loopback interface unavailable, errmsg: %s", err)
	}
	ip, err := resolveGenConfigLocalIP(iface.Name, "127.0.0.1:19999")
	if err != nil {
		t.Fatalf("resolveGenConfigLocalIP failed, errmsg: %s", err)
	}
	if ip == "" {
		t.Fatal("expected non-empty IP from loopback interface")
	}
}
