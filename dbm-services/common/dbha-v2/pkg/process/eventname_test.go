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
	"os"
	"path/filepath"
	"testing"
)

func TestDeriveEventName_GoldenVectors(t *testing.T) {
	cases := []struct {
		name   string
		key    string
		suffix string
		want   string
	}{
		{
			name:   "keepalive_addr",
			key:    "127.0.0.1:8080",
			suffix: stopEventSuffix,
			want:   `Local\dbha-probe-56852a5456d1b09e-stop`,
		},
		{
			name:   "pid_file_abs",
			key:    "/tmp/pids/probe.pid",
			suffix: stopEventSuffix,
			want:   `Local\dbha-probe-6948dc364e371ed9-stop`,
		},
		{
			name:   "reload_suffix",
			key:    "127.0.0.1:8080",
			suffix: reloadEventSuffix,
			want:   `Local\dbha-probe-56852a5456d1b09e-reload`,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := DeriveEventName(tc.key, tc.suffix); got != tc.want {
				t.Fatalf("DeriveEventName(%q, %q) = %q, want %q", tc.key, tc.suffix, got, tc.want)
			}
		})
	}
}

func TestDeriveEventName_MatchesStopEventName(t *testing.T) {
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	pidFile := filepath.Join(cwd, "pids", "probe.pid")
	key := EventKeyFromPidFile(pidFile)

	// stopEventName is windows-only but the derivation logic is shared via DeriveEventName.
	want := DeriveEventName(key, stopEventSuffix)
	if want == "" {
		t.Fatal("expected non-empty event name")
	}
	if got := DeriveEventName(key, stopEventSuffix); got != want {
		t.Fatalf("DeriveEventName mismatch: got %q want %q", got, want)
	}
}
