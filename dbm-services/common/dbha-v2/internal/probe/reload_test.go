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

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type countingReporter struct {
	closeCount atomic.Int32
}

func (c *countingReporter) Name() string                       { return "fake" }
func (c *countingReporter) Post(context.Context, []byte) error { return nil }
func (c *countingReporter) GetBaseInfo() client.BaseInfo {
	return client.BaseInfo{BkCloudID: 1}
}
func (c *countingReporter) Close() { c.closeCount.Add(1) }

// channelPlugin emits from a caller-fed channel.
type channelPlugin struct {
	name string
	ch   chan *plugin.HarvestData
}

func (c *channelPlugin) Name() (string, error) { return c.name, nil }

func (c *channelPlugin) Harvest(ctx context.Context, _, _ string) (<-chan *plugin.HarvestData, error) {
	out := make(chan *plugin.HarvestData)
	go func() {
		defer close(out)
		for {
			select {
			case <-ctx.Done():
				return
			case d, ok := <-c.ch:
				if !ok {
					return
				}
				select {
				case out <- d:
				case <-ctx.Done():
					return
				}
			}
		}
	}()
	return out, nil
}

func (c *channelPlugin) Close() error { return nil }

type stubStatus struct{}

func (stubStatus) GetDbType() haprobe.DbType { return haprobe.DbTypeMySql }

func restoreCfg(t *testing.T) {
	t.Helper()
	saved := config.Cfg
	t.Cleanup(func() {
		config.Apply(saved)
	})
}

func stopProbe(p *Probe) {
	p.Close()
	p.reporter.quiesce()
	p.runtime.stop()
}

func writeProbeYAML(t *testing.T, dir, body string) string {
	t.Helper()
	path := filepath.Join(dir, "probe.yaml")
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}
	return path
}

func skipHarvesters(t *testing.T) {
	t.Helper()
	withPluginEntries(t, []pluginEntry{
		{name: "mysql", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})
}

func TestReloadOnce_ConfigChangedRebuildsPlugins(t *testing.T) {
	restoreCfg(t)

	var calls atomic.Int32
	started := make(chan struct{}, 8)
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				calls.Add(1)
				ch := make(chan struct{})
				started <- struct{}{}
				return &fakePlugin{name: "mysql", started: ch}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, "name: probe\nserviceID: before\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)

	select {
	case <-started:
	case <-time.After(time.Second):
		t.Fatal("initial plugin did not start")
	}
	before := calls.Load()

	path = writeProbeYAML(t, dir, "name: probe\nserviceID: after\n")
	p.reloadOnce(path)

	select {
	case <-started:
	case <-time.After(time.Second):
		t.Fatal("plugin was not rebuilt after reload")
	}
	if calls.Load() <= before {
		t.Fatalf("expected factory call after reload, before: %d, after: %d", before, calls.Load())
	}
	if config.Cfg.ServiceID != "after" {
		t.Fatalf("ServiceID = %q, want after", config.Cfg.ServiceID)
	}
	stopProbe(p)
}

func TestReloadOnce_UnchangedSkipsRebuild(t *testing.T) {
	restoreCfg(t)

	var calls atomic.Int32
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				calls.Add(1)
				return &fakePlugin{name: "mysql"}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	body := "name: probe\nserviceID: same\n"
	path := writeProbeYAML(t, dir, body)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	time.Sleep(50 * time.Millisecond)
	before := calls.Load()

	// Only log/pidFile differ — RetainIdentity must keep identity and skip.
	path = writeProbeYAML(t, dir, body+"pidFile: ./other.pid\nlog:\n  level: debug\n")
	p.reloadOnce(path)

	if calls.Load() != before {
		t.Fatalf("factory calls changed on no-op reload, before: %d, after: %d",
			before, calls.Load())
	}
	stopProbe(p)
}

// TestReloadOnce_AdminOnlyChangeSkipsRebuild covers editing admin.syncInterval and sending
// SIGHUP. The block only steers the sync loop, which reads it fresh every round, so collection
// must not be interrupted to apply it — while the new value still has to take effect.
func TestReloadOnce_AdminOnlyChangeSkipsRebuild(t *testing.T) {
	restoreCfg(t)

	var calls atomic.Int32
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				calls.Add(1)
				return &fakePlugin{name: "mysql"}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	body := "name: probe\nserviceID: same\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n"
	path := writeProbeYAML(t, dir, body+"  syncInterval: 30s\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	time.Sleep(50 * time.Millisecond)
	before := calls.Load()

	path = writeProbeYAML(t, dir, body+"  syncInterval: 90s\n")
	p.reloadOnce(path)

	if calls.Load() != before {
		t.Fatalf("harvesters were rebuilt for an admin-only change, before: %d, after: %d",
			before, calls.Load())
	}
	if got := config.Snapshot().Admin.SyncInterval; got != 90*time.Second {
		t.Fatalf("new sync interval did not take effect, got: %s", got)
	}
	stopProbe(p)
}

func TestReloadOnce_DeleteHarvesterBlock(t *testing.T) {
	restoreCfg(t)

	var redisCalls atomic.Int32
	withPluginEntries(t, []pluginEntry{
		{name: "mysql", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{
			name: "redis",
			factory: func() (plugin.Plugin, error) {
				redisCalls.Add(1)
				if config.Cfg.Harvester.Redis == nil {
					return nil, nil
				}
				return &fakePlugin{name: "redis"}, nil
			},
		},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
harvester:
  redis:
    user: u
    password: p
    interval: 10s
    timeout: 1s
    endpoints:
      - ip: 127.0.0.1
        ports: ["6379"]
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}
	if config.Cfg.Harvester.Redis == nil {
		t.Fatal("expected redis harvester after load")
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	time.Sleep(50 * time.Millisecond)

	path = writeProbeYAML(t, dir, "name: probe\n")
	p.reloadOnce(path)

	if config.Cfg.Harvester.Redis != nil {
		t.Fatal("expected redis harvester cleared after reload")
	}
	stopProbe(p)
}

func TestReloadOnce_ParseFailureLeavesRuntime(t *testing.T) {
	restoreCfg(t)

	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				return &fakePlugin{name: "mysql"}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, "name: probe\nserviceID: keep\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	oldRT := p.runtime

	t.Run("missing_file", func(t *testing.T) {
		p.reloadOnce(filepath.Join(dir, "missing.yaml"))
		if config.Cfg.ServiceID != "keep" {
			t.Fatalf("ServiceID = %q, want keep", config.Cfg.ServiceID)
		}
		if p.runtime != oldRT {
			t.Fatal("runtime pointer changed after missing-file parse failure")
		}
	})

	t.Run("illegal_yaml", func(t *testing.T) {
		bad := filepath.Join(dir, "bad.yaml")
		if err := os.WriteFile(bad, []byte("name: [\n"), 0o644); err != nil {
			t.Fatalf("write illegal yaml failed, errmsg: %s", err)
		}
		p.reloadOnce(bad)
		if config.Cfg.ServiceID != "keep" {
			t.Fatalf("ServiceID = %q, want keep", config.Cfg.ServiceID)
		}
		if p.runtime != oldRT {
			t.Fatal("runtime pointer changed after illegal yaml")
		}
	})

	stopProbe(p)
}

func TestReloadOnce_ReporterUnchangedNotClosed(t *testing.T) {
	restoreCfg(t)

	withPluginEntries(t, []pluginEntry{
		{name: "mysql", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
serviceID: a
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 1s
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	fake := &countingReporter{}
	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter
	p.reporter.mu.Lock()
	p.reporter.reporter = fake
	p.reporter.mu.Unlock()

	path = writeProbeYAML(t, dir, `
name: probe
serviceID: b
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 1s
  bkCloudID: 0
`)
	p.reloadOnce(path)

	if fake.closeCount.Load() != 0 {
		t.Fatalf("reporter Close count: %d, want 0", fake.closeCount.Load())
	}
	if p.reporter.get() != fake {
		t.Fatal("reporter instance was replaced unexpectedly")
	}
	stopProbe(p)
}

func TestReloadOnce_DeleteReporterClearsInstance(t *testing.T) {
	restoreCfg(t)

	withPluginEntries(t, []pluginEntry{
		{name: "mysql", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 1s
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	fake := &countingReporter{}
	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter
	p.reporter.mu.Lock()
	p.reporter.reporter = fake
	p.reporter.mu.Unlock()

	path = writeProbeYAML(t, dir, "name: probe\n")
	p.reloadOnce(path)

	if fake.closeCount.Load() != 1 {
		t.Fatalf("reporter Close count: %d, want 1", fake.closeCount.Load())
	}
	if p.reporter.get() != nil {
		t.Fatal("expected reporter cleared after delete")
	}
	if config.Cfg.Reporter != nil {
		t.Fatal("expected Cfg.Reporter nil after delete")
	}
	stopProbe(p)
}

func TestReloadOnce_NilReporterDuringEvents(t *testing.T) {
	restoreCfg(t)

	eventC := make(chan *plugin.HarvestData, 1)
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				return &channelPlugin{name: "mysql", ch: eventC}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, "svc")

	// Emit while reporter is still nil — must not panic.
	eventC <- &plugin.HarvestData{
		Value: stubStatus{},
	}
	time.Sleep(50 * time.Millisecond)
	stopProbe(p)
}

func TestClose_DoesNotBlockDuringReload(t *testing.T) {
	restoreCfg(t)

	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				return &fakePlugin{name: "mysql"}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, "name: probe\nserviceID: a\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	savedPath := ConfigFilePath
	ConfigFilePath = path
	p := newProbe(context.Background(), "test-machine")
	ConfigFilePath = savedPath

	done := make(chan error, 1)
	go func() {
		done <- p.Run(context.Background())
	}()

	time.Sleep(100 * time.Millisecond)
	_ = writeProbeYAML(t, dir, "name: probe\nserviceID: b\n")
	select {
	case p.reloadC <- struct{}{}:
	default:
	}

	closed := make(chan struct{})
	go func() {
		p.Close()
		close(closed)
	}()
	select {
	case <-closed:
	case <-time.After(time.Second):
		t.Fatal("Close blocked during reload")
	}
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("Run returned error, errmsg: %s", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Run did not return after Close")
	}
	select {
	case <-p.reloadWorkerDone:
	case <-time.After(2 * time.Second):
		t.Fatal("reload worker did not exit after Close")
	}
}

func TestReloadOnce_SameFileAfterLoadSkipped(t *testing.T) {
	restoreCfg(t)

	var calls atomic.Int32
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				calls.Add(1)
				return &fakePlugin{name: "mysql"}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, "name: probe\nserviceID: same\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	time.Sleep(50 * time.Millisecond)
	before := calls.Load()

	p.reloadOnce(path)
	if calls.Load() != before {
		t.Fatalf("factory calls after same-file reload: %d, want %d", calls.Load(), before)
	}
	stopProbe(p)
}

func TestNewProbe_EarlyReloadAndClose(t *testing.T) {
	restoreCfg(t)
	p := newProbe(context.Background(), "test-machine")
	select {
	case p.reloadC <- struct{}{}:
	default:
		t.Fatal("reloadC should accept a notification after newProbe")
	}
	p.Close()
	p.Close()

	done := make(chan error, 1)
	go func() {
		done <- p.Run(context.Background())
	}()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("Run returned error, errmsg: %s", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Run did not return after Close before start")
	}
}

func TestReloadOnce_ReporterConfigChangedClosesOld(t *testing.T) {
	restoreCfg(t)
	skipHarvesters(t)

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
serviceID: a
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	fake := &countingReporter{}
	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter
	p.reporter.mu.Lock()
	p.reporter.reporter = fake
	p.reporter.mu.Unlock()

	path = writeProbeYAML(t, dir, `
name: probe
serviceID: a
reporter:
  name: grpc
  endpoint: ""
  dataID: 2
  connTimeout: 200ms
  bkCloudID: 0
`)
	p.reloadOnce(path)

	if fake.closeCount.Load() != 1 {
		t.Fatalf("reporter Close count: %d, want 1", fake.closeCount.Load())
	}
	if p.reporter.get() == fake {
		t.Fatal("expected old reporter instance to be replaced")
	}
	stopProbe(p)
}

func TestReloadOnce_ClientPingTimeRebuildsReporter(t *testing.T) {
	restoreCfg(t)
	skipHarvesters(t)

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
serviceID: a
client:
  pingTime: 10s
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	fake := &countingReporter{}
	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter
	p.reporter.mu.Lock()
	p.reporter.reporter = fake
	p.reporter.mu.Unlock()

	path = writeProbeYAML(t, dir, `
name: probe
serviceID: a
client:
  pingTime: 20s
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	p.reloadOnce(path)

	if fake.closeCount.Load() != 1 {
		t.Fatalf("reporter Close count: %d, want 1", fake.closeCount.Load())
	}
	if p.reporter.get() == fake {
		t.Fatal("expected reporter rebuild when only client.pingTime changed")
	}
	stopProbe(p)
}

func TestReloadOnce_UnchangedNilReporterRestartsCreate(t *testing.T) {
	restoreCfg(t)
	skipHarvesters(t)

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
serviceID: a
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter

	path = writeProbeYAML(t, dir, `
name: probe
serviceID: b
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	p.reloadOnce(path)

	if p.reporter.cancel == nil {
		t.Fatal("expected create loop restarted when instance was nil")
	}
	stopProbe(p)
}

func TestReloadOnce_QuiesceDuringReporterRetry(t *testing.T) {
	restoreCfg(t)
	skipHarvesters(t)

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
serviceID: a
client:
  pingTime: 10s
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.start(p.parent, config.Cfg.Reporter)
	time.Sleep(50 * time.Millisecond)

	nextPath := writeProbeYAML(t, dir, `
name: probe
serviceID: b
client:
  pingTime: 10s
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	done := make(chan struct{})
	go func() {
		p.reloadOnce(nextPath)
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("quiesce/reloadOnce did not return while reporter create was retrying")
	}
	if config.Cfg.ServiceID != "b" {
		t.Fatalf("ServiceID = %q, want b", config.Cfg.ServiceID)
	}
	stopProbe(p)
}

func TestReloadOnce_DeleteReporterSkipsEvents(t *testing.T) {
	restoreCfg(t)

	eventC := make(chan *plugin.HarvestData, 1)
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				return &channelPlugin{name: "mysql", ch: eventC}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	fake := &countingReporter{}
	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter
	p.reporter.mu.Lock()
	p.reporter.reporter = fake
	p.reporter.mu.Unlock()

	path = writeProbeYAML(t, dir, "name: probe\n")
	p.reloadOnce(path)

	eventC <- &plugin.HarvestData{Value: stubStatus{}}
	time.Sleep(50 * time.Millisecond)
	stopProbe(p)
}

func TestRunPlugin_SwapReporterWhileEvents(t *testing.T) {
	restoreCfg(t)

	eventC := make(chan *plugin.HarvestData, 8)
	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				return &channelPlugin{name: "mysql", ch: eventC}, nil
			},
		},
		{name: "mysqlProxyAdmin", factory: func() (plugin.Plugin, error) { return nil, nil }},
		{name: "redis", factory: func() (plugin.Plugin, error) { return nil, nil }},
	})

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, `
name: probe
serviceID: a
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.cfg = config.Cfg.Reporter
	p.reporter.mu.Lock()
	p.reporter.reporter = &countingReporter{}
	p.reporter.mu.Unlock()

	stop := make(chan struct{})
	go func() {
		for {
			select {
			case <-stop:
				return
			case eventC <- &plugin.HarvestData{Value: stubStatus{}}:
			}
		}
	}()

	path = writeProbeYAML(t, dir, `
name: probe
serviceID: b
reporter:
  name: grpc
  endpoint: ""
  dataID: 1
  connTimeout: 200ms
  bkCloudID: 0
`)
	p.reloadOnce(path)
	close(stop)
	time.Sleep(50 * time.Millisecond)
	stopProbe(p)
}

func TestReloadWorker_CoalescesBursts(t *testing.T) {
	restoreCfg(t)
	skipHarvesters(t)

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, "name: probe\nserviceID: a\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	savedPath := ConfigFilePath
	ConfigFilePath = path
	p := newProbe(context.Background(), "test-machine")
	ConfigFilePath = savedPath

	done := make(chan error, 1)
	go func() {
		done <- p.Run(context.Background())
	}()
	time.Sleep(50 * time.Millisecond)

	for i := 0; i < 20; i++ {
		select {
		case p.reloadC <- struct{}{}:
		default:
		}
	}
	p.Close()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("Run returned error, errmsg: %s", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("worker did not exit after Close")
	}
	select {
	case <-p.reloadWorkerDone:
	case <-time.After(2 * time.Second):
		t.Fatal("reload worker did not exit after Close")
	}
}

func TestReloadOnce_NoGoroutineGrowth(t *testing.T) {
	restoreCfg(t)
	skipHarvesters(t)

	dir := t.TempDir()
	path := writeProbeYAML(t, dir, "name: probe\nserviceID: n0\n")
	if err := config.Load(path); err != nil {
		t.Fatalf("load failed, errmsg: %s", err)
	}

	p := newProbe(context.Background(), "test-machine")
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)

	var afterThird int
	for i := 0; i < 20; i++ {
		body := "name: probe\nserviceID: n" + strconv.Itoa(i) + "\n"
		path = writeProbeYAML(t, dir, body)
		p.reloadOnce(path)
		if i == 2 {
			afterThird = runtime.NumGoroutine()
		}
	}
	got := runtime.NumGoroutine()
	if got > afterThird+8 {
		t.Fatalf("goroutine count grew, after_third: %d, after_20: %d", afterThird, got)
	}
	stopProbe(p)
}
