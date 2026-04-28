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
	"testing"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

func TestParseEtcdEndpointsSuccess(t *testing.T) {
	tests := []struct {
		name       string
		raw        string
		tlsEnabled bool
		wants      []string
	}{
		{
			name:       "host and port only with tls disabled",
			raw:        "127.0.0.1:2379",
			tlsEnabled: false,
			wants:      []string{"http://127.0.0.1:2379"},
		},
		{
			name:       "host and port only with tls enabled",
			raw:        "127.0.0.1:2379",
			tlsEnabled: true,
			wants:      []string{"https://127.0.0.1:2379"},
		},
		{
			name:       "http endpoint",
			raw:        "http://127.0.0.1:2379",
			tlsEnabled: true,
			wants:      []string{"http://127.0.0.1:2379"},
		},
		{
			name:       "uppercase http endpoint",
			raw:        "HTTP://127.0.0.1:2379",
			tlsEnabled: true,
			wants:      []string{"http://127.0.0.1:2379"},
		},
		{
			name:       "https endpoint",
			raw:        "https://127.0.0.1:2379",
			tlsEnabled: false,
			wants:      []string{"https://127.0.0.1:2379"},
		},
		{
			name:       "mixed endpoints with tls disabled",
			raw:        "127.0.0.1:2379;https://127.0.0.2:2380",
			tlsEnabled: false,
			wants:      []string{"http://127.0.0.1:2379", "https://127.0.0.2:2380"},
		},
		{
			name:       "mixed endpoints with tls enabled",
			raw:        "127.0.0.1:2379;https://127.0.0.2:2380",
			tlsEnabled: true,
			wants:      []string{"https://127.0.0.1:2379", "https://127.0.0.2:2380"},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got, err := ParseEtcdEndpoints(test.raw, test.tlsEnabled)
			if err != nil {
				t.Fatalf("ParseEtcdEndpoints failed, raw: %s, errmsg: %s", test.raw, err)
			}

			if len(got) != len(test.wants) {
				t.Fatalf("endpoint count is invalid, got: %d, want: %d", len(got), len(test.wants))
			}

			for i := range got {
				if got[i] != test.wants[i] {
					t.Fatalf("endpoint[%d] is invalid, got: %s, want: %s", i, got[i], test.wants[i])
				}
			}
		})
	}
}

func TestParseEtcdEndpointsFailure(t *testing.T) {
	tests := []struct {
		name string
		raw  string
	}{
		{name: "empty input", raw: ""},
		{name: "whitespace input", raw: "   "},
		{name: "tcp scheme", raw: "tcp://127.0.0.1:2379"},
		{name: "non-http scheme", raw: "udp://127.0.0.1:2379"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := ParseEtcdEndpoints(test.raw, false)
			if err == nil {
				t.Fatalf("ParseEtcdEndpoints should fail, raw: %s", test.raw)
			}

			ge, ok := err.(*gerrors.Error)
			if !ok {
				t.Fatalf("error type is invalid, expected: *gerrors.Error, actual: %T", err)
			}
			if !ge.HasCode(gerrors.InvalidConfiguration) {
				t.Fatalf("error code is invalid, got: %d, want: %d", ge.Code(), gerrors.InvalidConfiguration.Int())
			}
		})
	}
}
