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
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/spf13/viper"
)

func TestClampProbeHarvesterInterval(t *testing.T) {
	cases := []struct {
		name string
		in   time.Duration
		min  time.Duration
		want time.Duration
	}{
		{name: "zero is clamped", in: 0, min: minProbeHarvesterInterval, want: minProbeHarvesterInterval},
		{name: "below minimum is clamped", in: time.Second, min: minProbeHarvesterInterval, want: minProbeHarvesterInterval},
		{name: "at minimum is preserved", in: minProbeHarvesterInterval, min: minProbeHarvesterInterval, want: minProbeHarvesterInterval},
		{name: "above minimum is preserved", in: 30 * time.Second, min: minProbeHarvesterInterval, want: 30 * time.Second},
		{name: "heartbeat below floor is clamped", in: 100 * time.Millisecond, min: minProbeHarvesterHeartbeatInterval, want: minProbeHarvesterHeartbeatInterval},
		{name: "heartbeat at floor is preserved", in: minProbeHarvesterHeartbeatInterval, min: minProbeHarvesterHeartbeatInterval, want: minProbeHarvesterHeartbeatInterval},
		{name: "repl heartbeat below floor is clamped", in: time.Second, min: minProbeHarvesterReplHeartbeatInterval, want: minProbeHarvesterReplHeartbeatInterval},
		{name: "repl heartbeat at floor is preserved", in: minProbeHarvesterReplHeartbeatInterval, min: minProbeHarvesterReplHeartbeatInterval, want: minProbeHarvesterReplHeartbeatInterval},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := clampProbeHarvesterInterval("test", tc.in, tc.min)
			if got != tc.want {
				t.Errorf("clampProbeHarvesterInterval(%s, min=%s) = %s, want: %s", tc.in, tc.min, got, tc.want)
			}
		})
	}
}

func TestClampProbeHarvesterTimeout(t *testing.T) {
	cases := []struct {
		name string
		in   time.Duration
		want time.Duration
	}{
		{name: "zero is clamped", in: 0, want: minProbeHarvesterTimeout},
		{name: "below minimum is clamped", in: 100 * time.Millisecond, want: minProbeHarvesterTimeout},
		{name: "at minimum is preserved", in: minProbeHarvesterTimeout, want: minProbeHarvesterTimeout},
		{name: "above minimum is preserved", in: 5 * time.Second, want: 5 * time.Second},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := clampProbeHarvesterTimeout("test", tc.in)
			if got != tc.want {
				t.Errorf("clampProbeHarvesterTimeout(%s) = %s, want: %s", tc.in, got, tc.want)
			}
		})
	}
}

func TestLoad_ClampsProbeHarvesterIntervalsAndTimeouts(t *testing.T) {
	saved := Cfg
	t.Cleanup(func() {
		Cfg = saved
		viper.Reset()
	})

	dir := t.TempDir()
	path := filepath.Join(dir, "admin.yaml")
	content := `name: admin
version: v0
pidFile: ""
docFileDir: ""
discovery:
  endpoint: ""
  user: ""
  password: ""
  certFile: ""
  keyFile: ""
  trustedCAFile: ""
  serviceTimerInterval: 0s
  serviceUpdateTimeout: 0s
apm:
  readTimeout: 0s
  writeTimeout: 0s
  listenAddress: ""
grpc:
  listenAddress: ""
  serverPingTime: 0s
  pingTimeout: 0s
  keepAliveMinTime: 0s
  permitWithoutStream: false
  maxReceiveMessageSize: 0
  maxSendMessageSize: 0
web:
  listenAddress: ""
  readTimeout: 0s
  writeTimeout: 0s
dbmApi: []
storage:
  endpoint: ""
  user: ""
  password: ""
log:
  path: ""
  level: ""
  fileCount: 0
  fileSize: 0
probeGse:
  endpoint: ""
  dataID: 0
  connTimeout: ""
probeMysql:
  user: ""
  password: ""
  interval: 0s
  heartbeatInterval: 0s
  replDelayInterval: 0s
  timeout: 0s
probeRedis:
  user: ""
  password: ""
  interval: 0s
  timeout: 0s
probeProxyAdmin:
  user: ""
  password: ""
  interval: 0s
  heartbeatInterval: 0s
  replDelayInterval: 0s
  timeout: 0s
`
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write temp admin.yaml failed, errmsg: %s", err)
	}

	if err := Load(path); err != nil {
		t.Fatalf("Load failed, errmsg: %s", err)
	}

	if Cfg.ProbeMysql.Interval != minProbeHarvesterInterval {
		t.Errorf("ProbeMysql.Interval not clamped, got: %s", Cfg.ProbeMysql.Interval)
	}
	if Cfg.ProbeMysql.HeartbeatInterval != minProbeHarvesterHeartbeatInterval {
		t.Errorf("ProbeMysql.HeartbeatInterval not clamped, got: %s", Cfg.ProbeMysql.HeartbeatInterval)
	}
	if Cfg.ProbeMysql.ReplDelayInterval != minProbeHarvesterReplHeartbeatInterval {
		t.Errorf("ProbeMysql.ReplDelayInterval not clamped, got: %s", Cfg.ProbeMysql.ReplDelayInterval)
	}
	if Cfg.ProbeMysql.Timeout != minProbeHarvesterTimeout {
		t.Errorf("ProbeMysql.Timeout not clamped, got: %s", Cfg.ProbeMysql.Timeout)
	}
	if Cfg.ProbeRedis.Interval != minProbeHarvesterInterval {
		t.Errorf("ProbeRedis.Interval not clamped, got: %s", Cfg.ProbeRedis.Interval)
	}
	if Cfg.ProbeRedis.Timeout != minProbeHarvesterTimeout {
		t.Errorf("ProbeRedis.Timeout not clamped, got: %s", Cfg.ProbeRedis.Timeout)
	}
	if Cfg.ProbeProxyAdmin.Interval != minProbeHarvesterInterval {
		t.Errorf("ProbeProxyAdmin.Interval not clamped, got: %s", Cfg.ProbeProxyAdmin.Interval)
	}
	if Cfg.ProbeProxyAdmin.HeartbeatInterval != minProbeHarvesterHeartbeatInterval {
		t.Errorf("ProbeProxyAdmin.HeartbeatInterval not clamped, got: %s", Cfg.ProbeProxyAdmin.HeartbeatInterval)
	}
	if Cfg.ProbeProxyAdmin.ReplDelayInterval != minProbeHarvesterReplHeartbeatInterval {
		t.Errorf("ProbeProxyAdmin.ReplDelayInterval not clamped, got: %s", Cfg.ProbeProxyAdmin.ReplDelayInterval)
	}
	if Cfg.ProbeProxyAdmin.Timeout != minProbeHarvesterTimeout {
		t.Errorf("ProbeProxyAdmin.Timeout not clamped, got: %s", Cfg.ProbeProxyAdmin.Timeout)
	}
}

func TestLoad_PreservesValidProbeHarvesterValues(t *testing.T) {
	saved := Cfg
	t.Cleanup(func() {
		Cfg = saved
		viper.Reset()
	})

	dir := t.TempDir()
	path := filepath.Join(dir, "admin.yaml")
	content := `probeGse:
  endpoint: ""
  dataID: 0
  connTimeout: 10s
probeMysql:
  user: ""
  password: ""
  interval: 30s
  heartbeatInterval: 3s
  replDelayInterval: 25s
  timeout: 4s
probeRedis:
  user: ""
  password: ""
  interval: 25s
  timeout: 3s
probeProxyAdmin:
  user: ""
  password: ""
  interval: 40s
  heartbeatInterval: 4s
  replDelayInterval: 30s
  timeout: 2s
`
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write temp admin.yaml failed, errmsg: %s", err)
	}

	if err := Load(path); err != nil {
		t.Fatalf("Load failed, errmsg: %s", err)
	}

	if Cfg.ProbeMysql.Interval != 30*time.Second {
		t.Errorf("ProbeMysql.Interval altered, got: %s", Cfg.ProbeMysql.Interval)
	}
	if Cfg.ProbeMysql.HeartbeatInterval != 3*time.Second {
		t.Errorf("ProbeMysql.HeartbeatInterval altered, got: %s", Cfg.ProbeMysql.HeartbeatInterval)
	}
	if Cfg.ProbeMysql.ReplDelayInterval != 25*time.Second {
		t.Errorf("ProbeMysql.ReplDelayInterval altered, got: %s", Cfg.ProbeMysql.ReplDelayInterval)
	}
	if Cfg.ProbeMysql.Timeout != 4*time.Second {
		t.Errorf("ProbeMysql.Timeout altered, got: %s", Cfg.ProbeMysql.Timeout)
	}
	if Cfg.ProbeRedis.Interval != 25*time.Second {
		t.Errorf("ProbeRedis.Interval altered, got: %s", Cfg.ProbeRedis.Interval)
	}
	if Cfg.ProbeRedis.Timeout != 3*time.Second {
		t.Errorf("ProbeRedis.Timeout altered, got: %s", Cfg.ProbeRedis.Timeout)
	}
	if Cfg.ProbeProxyAdmin.Interval != 40*time.Second {
		t.Errorf("ProbeProxyAdmin.Interval altered, got: %s", Cfg.ProbeProxyAdmin.Interval)
	}
	if Cfg.ProbeProxyAdmin.HeartbeatInterval != 4*time.Second {
		t.Errorf("ProbeProxyAdmin.HeartbeatInterval altered, got: %s", Cfg.ProbeProxyAdmin.HeartbeatInterval)
	}
	if Cfg.ProbeProxyAdmin.ReplDelayInterval != 30*time.Second {
		t.Errorf("ProbeProxyAdmin.ReplDelayInterval altered, got: %s", Cfg.ProbeProxyAdmin.ReplDelayInterval)
	}
	if Cfg.ProbeProxyAdmin.Timeout != 2*time.Second {
		t.Errorf("ProbeProxyAdmin.Timeout altered, got: %s", Cfg.ProbeProxyAdmin.Timeout)
	}
}
