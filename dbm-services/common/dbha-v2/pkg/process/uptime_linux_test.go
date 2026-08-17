//go:build linux

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

package process

import (
	"strings"
	"testing"
)

func TestParseSelfStatStartTicks(t *testing.T) {
	cases := []struct {
		name    string
		content string
		want    uint64
		wantErr bool
	}{
		{
			name: "normal",
			content: "1234 (dbha-probe) S 1 1234 1234 0 -1 4194304 0 0 0 0 " +
				"0 0 0 0 20 0 1 0 98765 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
			want: 98765,
		},
		{
			name: "comm with spaces and parens",
			content: "1234 (dbha probe (x)) S 1 1234 1234 0 -1 4194304 0 0 0 0 " +
				"0 0 0 0 20 0 1 0 4242 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
			want: 4242,
		},
		{
			name:    "missing closing paren",
			content: "1234 (dbha-probe S 1 2 3",
			wantErr: true,
		},
		{
			name:    "insufficient fields",
			content: "1234 (dbha-probe) S 1 2 3",
			wantErr: true,
		},
		{
			name: "starttime not a number",
			content: "1234 (dbha-probe) S 1 1234 1234 0 -1 4194304 0 0 0 0 " +
				"0 0 0 0 20 0 1 0 notanum 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
			wantErr: true,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseSelfStatStartTicks(tc.content)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got ticks: %d", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("parse failed, errmsg: %s", err)
			}
			if got != tc.want {
				t.Errorf("got %d, want %d", got, tc.want)
			}
		})
	}
}

func TestParseProcUptimeSeconds(t *testing.T) {
	cases := []struct {
		name    string
		content string
		want    float64
		wantErr bool
	}{
		{name: "normal", content: "12345.67 9876.54\n", want: 12345.67},
		{name: "single field", content: "42.5\n", want: 42.5},
		{name: "empty", content: "", wantErr: true},
		{name: "non numeric", content: "abc 1\n", wantErr: true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseProcUptimeSeconds(tc.content)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got: %v", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("parse failed, errmsg: %s", err)
			}
			if got != tc.want {
				t.Errorf("got %v, want %v", got, tc.want)
			}
		})
	}
}

func TestParseProcStatBootTime(t *testing.T) {
	cases := []struct {
		name    string
		content string
		want    int64
		wantErr bool
	}{
		{
			name:    "normal",
			content: "cpu 1 2 3\nbtime 1700000000\nintr 0\n",
			want:    1700000000,
		},
		{
			name:    "missing btime",
			content: "cpu 1 2 3\nintr 0\n",
			wantErr: true,
		},
		{
			name:    "btime not a number",
			content: "btime abc\n",
			wantErr: true,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseProcStatBootTime(tc.content)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got: %d", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("parse failed, errmsg: %s", err)
			}
			if got != tc.want {
				t.Errorf("got %d, want %d", got, tc.want)
			}
			if !strings.Contains(tc.content, "btime") && err == nil {
				t.Fatal("unexpected success without btime")
			}
		})
	}
}
