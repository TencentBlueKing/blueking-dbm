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

package probe

import "testing"

func TestExtractPingHTTPAddrFromArgs(t *testing.T) {
	tests := []struct {
		name      string
		args      []string
		wantAddr  string
		wantFound bool
		wantErr   bool
	}{
		{
			name:      "subcommand with flag is not keepalive mode",
			args:      []string{"start", "--ping-http-addr=127.0.0.1:18080"},
			wantFound: false,
		},
		{
			name:      "ensure-keepalive with flag is not keepalive mode",
			args:      []string{"ensure-keepalive", "--ping-http-addr", "127.0.0.1:18080"},
			wantFound: false,
		},
		{
			name: "config flag before ensure-keepalive is not keepalive mode",
			args: []string{
				"-c", "./etc/probe.yaml", "ensure-keepalive", "--ping-http-addr", "127.0.0.1:1",
			},
			wantFound: false,
		},
		{
			name: "long config flag before ensure-keepalive is not keepalive mode",
			args: []string{
				"--config", "./etc/probe.yaml", "ensure-keepalive", "--ping-http-addr", "127.0.0.1:1",
			},
			wantFound: false,
		},
		{
			name: "config flag before start is not keepalive mode",
			args: []string{
				"-c", "./etc/probe.yaml", "start", "--ping-http-addr", "127.0.0.1:1",
			},
			wantFound: false,
		},
		{
			name: "config flag before daemon-start is not keepalive mode",
			args: []string{
				"-c", "./etc/probe.yaml", "daemon-start", "--ping-http-addr", "127.0.0.1:1",
			},
			wantFound: false,
		},
		{
			name:      "flag not present",
			args:      []string{"restart", "-c", "./etc/probe.yaml"},
			wantFound: false,
		},
		{
			name:      "root keepalive with split config flag",
			args:      []string{"-c", "./etc/probe.yaml", "--ping-http-addr", "127.0.0.1:18080"},
			wantAddr:  "127.0.0.1:18080",
			wantFound: true,
		},
		{
			name:      "root keepalive equals format",
			args:      []string{"--ping-http-addr=127.0.0.1:18080"},
			wantAddr:  "127.0.0.1:18080",
			wantFound: true,
		},
		{
			name:      "root keepalive split format",
			args:      []string{"--ping-http-addr", "127.0.0.1:18080"},
			wantAddr:  "127.0.0.1:18080",
			wantFound: true,
		},
		{
			name:      "flag empty value",
			args:      []string{"--ping-http-addr="},
			wantFound: true,
			wantErr:   true,
		},
		{
			name:      "flag missing value",
			args:      []string{"--ping-http-addr"},
			wantFound: true,
			wantErr:   true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotAddr, gotFound, err := ExtractPingHTTPAddrFromArgs(tt.args)
			if gotFound != tt.wantFound {
				t.Fatalf("found mismatch, expected: %v, actual: %v", tt.wantFound, gotFound)
			}
			if (err != nil) != tt.wantErr {
				t.Fatalf("error mismatch, expected error: %v, actual err: %v", tt.wantErr, err)
			}
			if gotAddr != tt.wantAddr {
				t.Fatalf("address mismatch, expected: %s, actual: %s", tt.wantAddr, gotAddr)
			}
		})
	}
}
