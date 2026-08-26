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

import "testing"

func TestClassifyProbeCmdline(t *testing.T) {
	cases := []struct {
		name    string
		cmdline string
		want    ProbeProcKind
	}{
		{name: "keepalive", cmdline: `C:\x\bin\dbha-probe.exe --ping-http-addr 127.0.0.1:18080`, want: ProbeProcKeepalive},
		{name: "guard", cmdline: `/opt/dbha/bin/dbha-probe daemon-start -c ./etc/probe.yaml`, want: ProbeProcGuard},
		{name: "worker", cmdline: `/opt/dbha/bin/dbha-probe -c ./etc/probe.yaml`, want: ProbeProcWorker},
		{name: "keepalive_beats_guard", cmdline: `dbha-probe daemon-start --ping-http-addr=1:2`, want: ProbeProcKeepalive},
		{name: "ensure_not_worker", cmdline: `dbha-probe ensure -c etc/probe.yaml --from-cron`, want: ProbeProcUnknown},
		{name: "ensure_keepalive_not_keepalive", cmdline: `dbha-probe ensure-keepalive --ping-http-addr 127.0.0.1:18080 --from-cron`, want: ProbeProcUnknown},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := ClassifyProbeCmdline(tc.cmdline); got != tc.want {
				t.Fatalf("ClassifyProbeCmdline = %v, want %v", got, tc.want)
			}
		})
	}
}
