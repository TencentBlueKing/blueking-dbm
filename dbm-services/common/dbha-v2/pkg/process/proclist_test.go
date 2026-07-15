/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
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
