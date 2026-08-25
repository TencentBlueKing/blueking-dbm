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
	"errors"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
)

// fakePlugin is a minimal plugin used to drive the loadPlugins / startPlugin
// goroutine path in tests without touching real harvester code.
type fakePlugin struct {
	name    string
	started chan struct{}
}

func (f *fakePlugin) Name() (string, error) { return f.name, nil }

func (f *fakePlugin) Harvest(ctx context.Context, _, _ string) (<-chan *plugin.HarvestData, error) {
	if f.started != nil {
		close(f.started)
	}
	out := make(chan *plugin.HarvestData)
	go func() {
		<-ctx.Done()
		close(out)
	}()
	return out, nil
}

func (f *fakePlugin) Close() error { return nil }

// withPluginEntries swaps the package-level pluginEntries for the duration of t,
// so each test can drive startRuntime with controlled factories.
func withPluginEntries(t *testing.T, entries []pluginEntry) {
	t.Helper()
	saved := pluginEntries
	pluginEntries = entries
	t.Cleanup(func() {
		pluginEntries = saved
	})
}

func TestStartPlugin_SkipsNilPlugin(t *testing.T) {
	p := newProbe(context.Background(), "test-machine")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	rt := &harvestRuntime{}

	p.startPlugin(ctx, rt, "mysql", func() (plugin.Plugin, error) {
		return nil, nil
	}, "svc")

	done := make(chan struct{})
	go func() {
		rt.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("startPlugin started a goroutine for nil plug")
	}
}

func TestStartPlugin_SkipsErrorFactory(t *testing.T) {
	p := newProbe(context.Background(), "test-machine")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	rt := &harvestRuntime{}

	p.startPlugin(ctx, rt, "mysql", func() (plugin.Plugin, error) {
		return nil, errors.New("boom")
	}, "svc")

	done := make(chan struct{})
	go func() {
		rt.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("startPlugin started a goroutine when factory returned error")
	}
}

func TestStartRuntime_AllFactoriesReturnNil(t *testing.T) {
	var calls atomic.Int32
	nilFactory := func() (plugin.Plugin, error) {
		calls.Add(1)
		return nil, nil
	}
	withPluginEntries(t, []pluginEntry{
		{name: "mysql", factory: nilFactory},
		{name: "mysqlProxyAdmin", factory: nilFactory},
		{name: "redis", factory: nilFactory},
	})

	p := newProbe(context.Background(), "test-machine")
	rt := p.startRuntime(p.parent, "svc")

	if got := calls.Load(); got != 3 {
		t.Errorf("expected 3 factory calls, got: %d", got)
	}

	done := make(chan struct{})
	go func() {
		rt.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("startRuntime started goroutines for nil-returning factories")
	}
}

func TestStartRuntime_OnlyRedisConfigured(t *testing.T) {
	redisStarted := make(chan struct{})
	redisPlug := &fakePlugin{name: "redis", started: redisStarted}

	withPluginEntries(t, []pluginEntry{
		{
			name: "mysql",
			factory: func() (plugin.Plugin, error) {
				return nil, nil
			},
		},
		{
			name: "mysqlProxyAdmin",
			factory: func() (plugin.Plugin, error) {
				return nil, nil
			},
		},
		{
			name: "redis",
			factory: func() (plugin.Plugin, error) {
				return redisPlug, nil
			},
		},
	})

	p := newProbe(context.Background(), "test-machine")
	rt := p.startRuntime(p.parent, "svc")

	select {
	case <-redisStarted:
	case <-time.After(time.Second):
		rt.stop()
		t.Fatal("redis fakePlugin.Harvest was not called")
	}

	rt.stop()

	done := make(chan struct{})
	go func() {
		rt.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("startRuntime goroutines did not exit after stop")
	}
}
