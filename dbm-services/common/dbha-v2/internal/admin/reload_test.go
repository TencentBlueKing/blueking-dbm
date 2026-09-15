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

package admin

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/slot"
)

type fakeSlot struct {
	name       string
	err        error
	events     *[]string
	needsBuild bool
	minWork    time.Duration
}

func (s *fakeSlot) Name() string { return s.name }

func (s *fakeSlot) NeedsRebuild(config.Configuration) bool { return s.needsBuild }

func (s *fakeSlot) Rebuild(ctx context.Context, _ config.Configuration) error {
	if s.minWork > 0 {
		timer := time.NewTimer(s.minWork)
		defer timer.Stop()
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-timer.C:
		}
	} else {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
	}
	*s.events = append(*s.events, "build:"+s.name)
	return s.err
}

func (s *fakeSlot) Close(context.Context) {
	*s.events = append(*s.events, "close:"+s.name)
}

func TestStartSlotsClosesBuiltResourcesInReverseOnFailure(t *testing.T) {
	var events []string
	service := &Service{}
	service.slots = []slot.Ops{
		&fakeSlot{name: "one", events: &events},
		&fakeSlot{name: "two", events: &events, err: errors.New("failed")},
	}

	if err := service.startSlots(context.Background(), config.Configuration{}); err == nil {
		t.Fatal("startSlots should return the build failure")
	}
	want := []string{"build:one", "build:two", "close:one"}
	if !equalStrings(events, want) {
		t.Fatalf("events: %v, want: %v", events, want)
	}
}

func TestReloadAppliesSnapshotWhenSlotFails(t *testing.T) {
	saved := config.Snapshot()
	t.Cleanup(func() { config.Apply(saved) })
	current := validReloadConfig()
	current.Name = "stable-name"
	config.Apply(current)

	path := writeReloadConfig(t, `
name: ignored-name
discovery:
  endpoint: "127.0.0.1:2379"
storage:
  endpoint: "127.0.0.1:3307"
apm:
  listenAddress: "127.0.0.1:19091"
grpc:
  listenAddress: "127.0.0.1:15052"
web:
  listenAddress: "127.0.0.1:18081"
log:
  level: debug
`)

	var events []string
	failing := &fakeSlot{name: "storage", events: &events, needsBuild: true, err: errors.New("failed")}
	service := &Service{
		configPath: path,
		shutdown:   make(chan struct{}),
		slots:      []slot.Ops{failing},
	}
	service.reloadOnce()

	got := config.Snapshot()
	if got.Storage.Endpoint != "127.0.0.1:3307" {
		t.Fatalf("storage endpoint: %s, want reloaded endpoint", got.Storage.Endpoint)
	}
	if got.Name != "stable-name" {
		t.Fatalf("identity changed during reload, name: %s", got.Name)
	}
	if !lastReloadOutcome.failed {
		t.Fatal("slot failure should mark reload failed")
	}

	failing.err = nil
	service.reloadOnce()
	if lastReloadOutcome.failed {
		t.Fatal("retry after slot success should mark reload success")
	}
	if !equalStrings(lastReloadOutcome.successNames, []string{"storage"}) {
		t.Fatalf("success names: %v", lastReloadOutcome.successNames)
	}
}

func TestReloadIndependentSlotTimeoutContinues(t *testing.T) {
	savedTotal, savedSlot := reloadTotalTimeout, reloadSlotTimeout
	t.Cleanup(func() {
		reloadTotalTimeout = savedTotal
		reloadSlotTimeout = savedSlot
	})
	reloadTotalTimeout = 70 * time.Millisecond
	reloadSlotTimeout = 200 * time.Millisecond

	service, events := newReloadTestService(t, []slot.Ops{
		&fakeSlot{name: "slow", needsBuild: true, minWork: 45 * time.Millisecond},
		&fakeSlot{name: "next", needsBuild: true, minWork: 45 * time.Millisecond},
	})
	service.reloadOnce()
	if !equalStrings(*events, []string{"build:slow", "build:next"}) {
		t.Fatalf("events: %v, want both slots rebuilt under independent slot timeout", *events)
	}
	if lastReloadOutcome.failed {
		t.Fatal("both slots should succeed with independent timeouts")
	}
}

func TestReloadSlotTimeoutFailsThatSlotThenContinues(t *testing.T) {
	savedTotal, savedSlot := reloadTotalTimeout, reloadSlotTimeout
	t.Cleanup(func() {
		reloadTotalTimeout = savedTotal
		reloadSlotTimeout = savedSlot
	})
	reloadTotalTimeout = time.Second
	reloadSlotTimeout = 30 * time.Millisecond

	service, events := newReloadTestService(t, []slot.Ops{
		&fakeSlot{name: "slow", needsBuild: true, minWork: 80 * time.Millisecond},
		&fakeSlot{name: "next", needsBuild: true},
	})
	service.reloadOnce()
	if !equalStrings(*events, []string{"build:next"}) {
		t.Fatalf("events: %v, want only next rebuilt after slow timeout", *events)
	}
	if !lastReloadOutcome.failed {
		t.Fatal("timed-out slot should mark reload failed")
	}
	if !equalStrings(lastReloadOutcome.failureNames, []string{"slow"}) {
		t.Fatalf("failure names: %v, want slow", lastReloadOutcome.failureNames)
	}
	if !equalStrings(lastReloadOutcome.successNames, []string{"next"}) {
		t.Fatalf("success names: %v, want next", lastReloadOutcome.successNames)
	}
}

func TestReloadTotalBudgetSkipsRemainingSlots(t *testing.T) {
	savedTotal, savedSlot := reloadTotalTimeout, reloadSlotTimeout
	t.Cleanup(func() {
		reloadTotalTimeout = savedTotal
		reloadSlotTimeout = savedSlot
	})
	reloadTotalTimeout = 40 * time.Millisecond
	reloadSlotTimeout = 200 * time.Millisecond

	service, events := newReloadTestService(t, []slot.Ops{
		&fakeSlot{name: "first", needsBuild: true, minWork: 50 * time.Millisecond},
		&fakeSlot{name: "second", needsBuild: true, minWork: 10 * time.Millisecond},
	})
	service.reloadOnce()
	if !equalStrings(*events, []string{"build:first"}) {
		t.Fatalf("events: %v, want only first slot rebuilt", *events)
	}
	if !lastReloadOutcome.failed {
		t.Fatal("skipped remaining slot should mark reload failed")
	}
	if !equalStrings(lastReloadOutcome.failureNames, []string{"second"}) {
		t.Fatalf("failure names: %v, want second", lastReloadOutcome.failureNames)
	}
}

func TestReloadOnceAfterShutdownDoesNotReportSuccess(t *testing.T) {
	saved := config.Snapshot()
	t.Cleanup(func() { config.Apply(saved) })
	config.Apply(validReloadConfig())

	shutdown := make(chan struct{})
	close(shutdown)
	service := &Service{
		configPath: filepath.Join(t.TempDir(), "missing.yaml"),
		shutdown:   shutdown,
	}
	lastReloadOutcome = reloadOutcome{}
	service.reloadOnce()
	if !lastReloadOutcome.failed {
		t.Fatal("reloadOnce after shutdown must not report success")
	}
}

func newReloadTestService(t *testing.T, slots []slot.Ops) (*Service, *[]string) {
	t.Helper()
	saved := config.Snapshot()
	t.Cleanup(func() { config.Apply(saved) })
	current := validReloadConfig()
	config.Apply(current)
	path := writeReloadConfig(t, `
discovery:
  endpoint: "127.0.0.1:2379"
storage:
  endpoint: "127.0.0.1:3307"
apm:
  listenAddress: "127.0.0.1:19091"
grpc:
  listenAddress: "127.0.0.1:15052"
web:
  listenAddress: "127.0.0.1:18081"
log:
  level: debug
`)
	var events []string
	for _, resourceSlot := range slots {
		if fake, ok := resourceSlot.(*fakeSlot); ok {
			fake.events = &events
		}
	}
	return &Service{
		configPath: path,
		shutdown:   make(chan struct{}),
		slots:      slots,
	}, &events
}

func writeReloadConfig(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "admin.yaml")
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}
	return path
}

func validReloadConfig() config.Configuration {
	return config.Configuration{
		Name:      "admin",
		Discovery: config.DiscoveryConfig{Endpoint: "127.0.0.1:2379"},
		Storage:   config.StorageConfig{Endpoint: "127.0.0.1:3306"},
		Apm:       config.ApmConfig{ListenAddress: "127.0.0.1:19090"},
		Grpc:      config.GrpcConfig{ListenAddress: "127.0.0.1:15051"},
		Web:       config.WebConfig{ListenAddress: "127.0.0.1:18080"},
		Log:       config.LogConfig{Level: "info"},
	}
}

func equalStrings(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}
