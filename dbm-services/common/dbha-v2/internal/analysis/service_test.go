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

package analysis

import "testing"

func TestResolveBkMonitorEndpoint(t *testing.T) {
	t.Parallel()

	testCases := []struct {
		name    string
		raw     string
		want    string
		wantErr bool
	}{
		{
			name:    "domain socket path",
			raw:     "/var/run/bkmonitor.sock",
			want:    "/var/run/bkmonitor.sock",
			wantErr: false,
		},
		{
			name:    "domain socket path with spaces",
			raw:     "  /var/run/bkmonitor.sock  ",
			want:    "/var/run/bkmonitor.sock",
			wantErr: false,
		},
		{
			name:    "host port",
			raw:     "127.0.0.1:9090",
			want:    "127.0.0.1:9090",
			wantErr: false,
		},
		{
			name:    "http endpoint",
			raw:     "http://127.0.0.1:9090",
			want:    "127.0.0.1:9090",
			wantErr: false,
		},
		{
			name:    "empty endpoint",
			raw:     "   ",
			want:    "",
			wantErr: true,
		},
		{
			name:    "invalid endpoint",
			raw:     "bk-monitor-endpoint",
			want:    "",
			wantErr: true,
		},
	}

	for _, tc := range testCases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			got, err := resolveBkMonitorEndpoint(tc.raw)
			if (err != nil) != tc.wantErr {
				t.Fatalf("resolveBkMonitorEndpoint() error = %v, wantErr = %v", err, tc.wantErr)
			}

			if got != tc.want {
				t.Fatalf("resolveBkMonitorEndpoint() = %q, want = %q", got, tc.want)
			}
		})
	}
}
