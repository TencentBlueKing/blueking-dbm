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

package config

import (
	"testing"
	"time"
)

func TestIsPortPaused(t *testing.T) {
	now := time.Now().Unix()
	cases := []struct {
		name string
		cfg  Configuration
		port int
		want bool
	}{
		{
			name: "empty list never pauses",
			cfg:  Configuration{},
			port: 3306,
			want: false,
		},
		{
			name: "paused port",
			cfg:  Configuration{PausePorts: []PausePort{{Port: 3306, ExpireAt: now + 60}}},
			port: 3306,
			want: true,
		},
		{
			name: "other port stays collected",
			cfg:  Configuration{PausePorts: []PausePort{{Port: 3306, ExpireAt: now + 60}}},
			port: 3307,
			want: false,
		},
		{
			name: "expired entry is ignored",
			cfg:  Configuration{PausePorts: []PausePort{{Port: 3306, ExpireAt: now - 1}}},
			port: 3306,
			want: false,
		},
		{
			name: "expiry exactly now is already over",
			cfg:  Configuration{PausePorts: []PausePort{{Port: 3306, ExpireAt: now}}},
			port: 3306,
			want: false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := tc.cfg.IsPortPaused(tc.port); got != tc.want {
				t.Errorf("IsPortPaused(%d) = %v, want %v", tc.port, got, tc.want)
			}
		})
	}
}

func TestNormalizePausePorts(t *testing.T) {
	got := NormalizePausePorts([]PausePort{
		{Port: 6380, ExpireAt: 2},
		{Port: 3306, ExpireAt: 1},
		{Port: 3306, ExpireAt: 3},
	})
	want := []PausePort{{Port: 3306, ExpireAt: 3}, {Port: 6380, ExpireAt: 2}}

	if len(got) != len(want) {
		t.Fatalf("len = %d, want %d, got: %+v", len(got), len(want), got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("entry %d = %+v, want %+v", i, got[i], want[i])
		}
	}

	if NormalizePausePorts(nil) != nil {
		t.Error("nil input should stay nil so the key is omitted from the yaml")
	}
}

func TestPausePortsRoundTripInYAML(t *testing.T) {
	doc := "name: probe\npidFile: ./pids/probe.pid\npausePorts:\n" +
		"    - port: 3306\n      duration: 10m\n      expireAt: 1761623400\n"

	parsed, err := ParseBytes([]byte(doc))
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if len(parsed.PausePorts) != 1 {
		t.Fatalf("pause ports = %+v, want one entry", parsed.PausePorts)
	}

	entry := parsed.PausePorts[0]
	if entry.Port != 3306 || entry.ExpireAt != 1761623400 || entry.Duration != 10*time.Minute {
		t.Errorf("entry = %+v, want port 3306 / 10m / 1761623400", entry)
	}
}
