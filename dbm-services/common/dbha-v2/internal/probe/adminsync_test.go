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
	"reflect"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/configsync"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// syncProbe builds a Probe with just the fields the sync path touches, and seeds the config
// file with the given document.
func syncProbe(t *testing.T, doc string) *Probe {
	t.Helper()

	path := filepath.Join(t.TempDir(), "probe.yaml")
	if err := os.WriteFile(path, []byte(doc), 0o644); err != nil {
		t.Fatalf("seed config failed, errmsg: %s", err)
	}

	parent, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)

	return &Probe{
		parent:     parent,
		shutdown:   make(chan struct{}),
		reloadC:    make(chan struct{}, 1),
		configPath: path,
	}
}

// syncPayload is what admin returns for a machine with the given mysql ports.
func syncPayload(ports ...int) probeconfig.ProbeConfigPayload {
	metadata := make([]probeconfig.ProbeMetadataItem, 0, len(ports))
	for _, port := range ports {
		metadata = append(metadata, probeconfig.ProbeMetadataItem{
			IP:          "127.0.0.1",
			Port:        port,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
			AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
		})
	}

	return probeconfig.ProbeConfigPayload{
		Gse: probeconfig.GseConfig{Endpoint: "127.0.0.1:1234", DataID: 1, ConnTimeout: "5s"},
		MySQL: &probeconfig.ProbeMySQLConfig{
			User: "u", Password: "p", Interval: "20s", Timeout: "5s",
		},
		Metadata: metadata,
	}
}

func readFile(t *testing.T, path string) string {
	t.Helper()

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read config failed, errmsg: %s", err)
	}
	return string(data)
}

// TestReconcileConfigFile_WritesAndConverges is the core loop property: the first round applies
// what admin reports, and an immediately repeated round with the same payload writes nothing.
// Without convergence every round would rewrite the file and trigger a harvester rebuild.
func TestReconcileConfigFile_WritesAndConverges(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n")

	changed, err := reconcile(t, p, syncPayload(3306))
	if err != nil {
		t.Fatalf("first round failed, errmsg: %s", err)
	}
	if !changed {
		t.Fatal("first round should have written the config")
	}
	if !strings.Contains(readFile(t, p.configPath), "3306") {
		t.Fatal("config does not contain the port admin reported")
	}

	changed, err = reconcile(t, p, syncPayload(3306))
	if err != nil {
		t.Fatalf("second round failed, errmsg: %s", err)
	}
	if changed {
		t.Fatal("an unchanged payload must not rewrite the config")
	}
}

// TestReconcileConfigFile_PreservesCommentsWhenUnchanged pins why the comparison is semantic
// rather than byte-for-byte: an operator's comments and layout must survive a sync that has
// nothing to change.
func TestReconcileConfigFile_PreservesCommentsWhenUnchanged(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n")

	if _, err := reconcile(t, p, syncPayload(3306)); err != nil {
		t.Fatalf("seed round failed, errmsg: %s", err)
	}

	annotated := "# operator note: do not delete\n" + readFile(t, p.configPath)
	if err := os.WriteFile(p.configPath, []byte(annotated), 0o644); err != nil {
		t.Fatalf("annotate config failed, errmsg: %s", err)
	}

	changed, err := reconcile(t, p, syncPayload(3306))
	if err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	if changed {
		t.Fatal("comments alone must not count as a difference")
	}
	if !strings.Contains(readFile(t, p.configPath), "operator note") {
		t.Fatal("comment was erased by a sync that changed nothing")
	}
}

// TestReconcileConfigFile_KeepsLocalFieldsFromDisk covers the case an operator edited the file
// and has not reloaded yet, while admin's metadata changes in the same window. The edit lives
// only on disk, so taking local fields from memory would silently revert it.
func TestReconcileConfigFile_KeepsLocalFieldsFromDisk(t *testing.T) {
	restoreCfg(t)

	// Applied config carries the old identity; the file on disk carries the operator's edit.
	applied := config.Cfg
	applied.ServiceID = "stale-in-memory"
	config.Apply(applied)

	p := syncProbe(t, "name: probe\nserviceID: edited-on-disk\nadmin:\n"+
		"  endpoints: [\"127.0.0.1:19001\"]\n  syncInterval: 30s\n")

	if _, err := reconcile(t, p, syncPayload(3306)); err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}

	parsed, err := config.Parse(p.configPath)
	if err != nil {
		t.Fatalf("parse written config failed, errmsg: %s", err)
	}
	if parsed.ServiceID != "edited-on-disk" {
		t.Errorf("local edit was overwritten from memory, serviceID: %s", parsed.ServiceID)
	}
	if !parsed.Admin.SyncEnabled() {
		t.Errorf("admin block lost, sync would never run again, admin: %+v", parsed.Admin)
	}
}

// TestReconcileConfigFile_RejectsUnparsableRendering is the guard against unattended breakage:
// when a payload renders into something the probe cannot parse, the working file must survive.
// A zero mysql interval is the concrete shape of that defect, since it renders as interval: "".
func TestReconcileConfigFile_RejectsUnparsableRendering(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n")

	if _, err := reconcile(t, p, syncPayload(3306)); err != nil {
		t.Fatalf("seed round failed, errmsg: %s", err)
	}
	before := readFile(t, p.configPath)

	broken := syncPayload(3307)
	broken.MySQL.Interval = ""

	changed, err := reconcile(t, p, broken)
	if err == nil {
		t.Fatal("expected an unparsable rendering to be rejected")
	}
	if changed {
		t.Fatal("a rejected rendering must not be written")
	}
	if readFile(t, p.configPath) != before {
		t.Fatal("the working config was modified despite the rejection")
	}
}

// TestReconcileConfigFile_HealsUnparsableFile is the other direction: when the file on disk is
// already broken, comparison is impossible and sync should restore a valid one rather than
// refuse to act.
func TestReconcileConfigFile_HealsUnparsableFile(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n  broken-indent: true\n")

	changed, err := reconcile(t, p, syncPayload(3306))
	if err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	if !changed {
		t.Fatal("a broken config file should have been rewritten")
	}
	if _, err := config.Parse(p.configPath); err != nil {
		t.Fatalf("rewritten config still does not parse, errmsg: %s", err)
	}
}

// TestReconcileConfigFile_TakesTheConfigLock keeps the read-modify-write sequence atomic
// against gen-config: while the lock is held elsewhere, the round must fail instead of writing
// on top of the other writer.
func TestReconcileConfigFile_TakesTheConfigLock(t *testing.T) {
	if testing.Short() {
		t.Skip("waits out the config lock timeout")
	}
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n")
	before := readFile(t, p.configPath)

	lockPath, err := process.LockPathFor(p.configPath)
	if err != nil {
		t.Fatalf("resolve lock path failed, errmsg: %s", err)
	}
	fl, held, err := process.TryFileLock(lockPath)
	if err != nil || !held {
		t.Fatalf("could not take the lock for the test, held: %v, errmsg: %v", held, err)
	}
	defer func() { _ = fl.Unlock() }()

	done := make(chan error, 1)
	go func() {
		_, syncErr := reconcile(t, p, syncPayload(3306))
		done <- syncErr
	}()

	select {
	case syncErr := <-done:
		if syncErr == nil {
			t.Fatal("expected the round to fail while another writer holds the lock")
		}
	case <-time.After(syncLockTimeout + 5*time.Second):
		t.Fatal("round did not give up on the lock")
	}

	if readFile(t, p.configPath) != before {
		t.Fatal("config was written while another writer held the lock")
	}
}

// TestSyncOnce_RequestsReloadOnlyOnChange ties the write decision to the reload signal: a round
// that changed nothing must not wake the reload worker.
func TestSyncOnce_RequestsReloadOnlyOnChange(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n")

	if _, err := reconcile(t, p, syncPayload(3306)); err != nil {
		t.Fatalf("seed round failed, errmsg: %s", err)
	}
	drainReload(p)

	if _, err := reconcile(t, p, syncPayload(3306)); err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	select {
	case <-p.reloadC:
		t.Fatal("no change should mean no reload request")
	default:
	}

	changed, err := reconcile(t, p, syncPayload(3306, 3307))
	if err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	if !changed {
		t.Fatal("a new port should have changed the config")
	}
	p.requestReload()
	select {
	case <-p.reloadC:
	default:
		t.Fatal("a change should have queued a reload")
	}
}

// TestRequestReload_DropsRedundantSignal documents why dropping is safe: the worker re-reads
// the file, so one pending signal already covers any number of changes made before it runs.
func TestRequestReload_DropsRedundantSignal(t *testing.T) {
	p := syncProbe(t, "name: probe\n")

	p.requestReload()
	p.requestReload()

	if got := len(p.reloadC); got != 1 {
		t.Fatalf("queued reload requests: %d, want 1", got)
	}
}

func drainReload(p *Probe) {
	select {
	case <-p.reloadC:
	default:
	}
}

func reconcile(t *testing.T, p *Probe, payload probeconfig.ProbeConfigPayload) (bool, error) {
	t.Helper()
	admin := config.AdminConfig{}
	if disk, err := config.Parse(p.configPath); err == nil {
		admin = disk.Admin
	}
	return p.reconcileConfigFile(payload, admin)
}

func TestReconcileConfigFile_SkipsWriteWhenPullParamsDiverge(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n"+
		"  bkCloudID: 5\n  localIP: 127.0.0.1\n  syncInterval: 30s\n")
	before := readFile(t, p.configPath)

	changed, err := p.reconcileConfigFile(syncPayload(3306), config.AdminConfig{
		Endpoints: []string{"127.0.0.1:19002"},
		BkCloudID: 5,
		LocalIP:   "127.0.0.1",
	})
	if err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	if changed {
		t.Fatal("divergent pull params must not rewrite the file")
	}
	if readFile(t, p.configPath) != before {
		t.Fatal("file was rewritten despite divergent pull params")
	}
	select {
	case <-p.reloadC:
	default:
		t.Fatal("divergent pull params should request a reload")
	}
}

func TestReconcileConfigFile_HealsEvenIfMemoryAdminDiffers(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n  broken-indent: true\n")

	changed, err := p.reconcileConfigFile(syncPayload(3306), config.AdminConfig{
		Endpoints: []string{"127.0.0.1:19002"},
		BkCloudID: 9,
		LocalIP:   "127.0.0.1",
	})
	if err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	if !changed {
		t.Fatal("a broken config file should have been rewritten")
	}
	if _, err := config.Parse(p.configPath); err != nil {
		t.Fatalf("rewritten config still does not parse, errmsg: %s", err)
	}
}

func TestReconcileConfigFile_AppliesPersistedClearPorts(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\nclearPorts: [3306]\nadmin:\n"+
		"  endpoints: [\"127.0.0.1:19001\"]\n  localIP: 127.0.0.1\n  syncInterval: 30s\n")

	changed, err := reconcile(t, p, syncPayload(3306, 3307))
	if err != nil {
		t.Fatalf("first round failed, errmsg: %s", err)
	}
	if !changed {
		t.Fatal("first round should have written the config")
	}
	body := readFile(t, p.configPath)
	if !strings.Contains(body, "clearPorts:") {
		t.Fatal("expected persisted clearPorts")
	}
	parsed, err := config.Parse(p.configPath)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if !reflect.DeepEqual(parsed.ClearPorts, []int{3306}) {
		t.Errorf("clearPorts: %v", parsed.ClearPorts)
	}
	if parsed.Harvester.MySql == nil || len(parsed.Harvester.MySql.Endpoints) == 0 {
		t.Fatal("expected remaining mysql endpoint")
	}
	for _, ep := range parsed.Harvester.MySql.Endpoints {
		for _, port := range ep.Ports {
			if port == "3306" {
				t.Fatal("cleared port 3306 still present")
			}
		}
	}

	changed, err = reconcile(t, p, syncPayload(3306, 3307))
	if err != nil {
		t.Fatalf("second round failed, errmsg: %s", err)
	}
	if changed {
		t.Fatal("clearPorts must make gen-config and sync converge")
	}
}

// TestReconcileConfigFile_AgreesWithGenConfigOutput closes the cross-entry half of the convergence
// argument. The file is produced the way gen-config's locked stage produces it: same payload, same
// LocalFields. Sync must then find nothing to do, or the two writers would take turns rewriting
// the harvester on every cycle.
func TestReconcileConfigFile_AgreesWithGenConfigOutput(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\nclearPorts: [3307]\npidFile: /tmp/custom/probe.pid\nadmin:\n"+
		"  endpoints: [\"127.0.0.1:19001\"]\n  localIP: 127.0.0.1\n  syncInterval: 30s\n")

	local, err := config.Parse(p.configPath)
	if err != nil {
		t.Fatalf("parse seed failed, errmsg: %s", err)
	}
	payload := syncPayload(3306, 3307)
	rendered, err := configsync.Render(payload, config.LocalFields(local)...)
	if err != nil {
		t.Fatalf("gen-config style render failed, errmsg: %s", err)
	}
	if err := os.WriteFile(p.configPath, []byte(rendered), 0o644); err != nil {
		t.Fatalf("write failed, errmsg: %s", err)
	}

	changed, err := reconcile(t, p, payload)
	if err != nil {
		t.Fatalf("round failed, errmsg: %s", err)
	}
	if changed {
		t.Fatalf("sync disagreed with gen-config output, file:\n%s", readFile(t, p.configPath))
	}
}

// TestNextSyncDelay_StaysWithinJitterWindow checks the spread is bounded: never shorter than
// the configured interval, never more than a tenth over it.
func TestNextSyncDelay_StaysWithinJitterWindow(t *testing.T) {
	const interval = 60 * time.Second

	distinct := make(map[time.Duration]struct{})
	for i := 0; i < 200; i++ {
		got := nextSyncDelay(interval)
		if got < interval || got >= interval+interval/syncJitterDivisor {
			t.Fatalf("delay out of window: %s", got)
		}
		distinct[got] = struct{}{}
	}
	if len(distinct) < 2 {
		t.Fatal("delay is not jittered, probes would stay aligned")
	}

	// An interval too small to jitter must still be usable rather than collapsing to zero.
	if got := nextSyncDelay(time.Nanosecond); got != time.Nanosecond {
		t.Fatalf("tiny interval delay: %s, want 1ns", got)
	}
}

// TestOnlyAdminChanged separates the block that merely steers the sync loop from the ones that
// require rebuilding the runtime.
func TestOnlyAdminChanged(t *testing.T) {
	base := config.Configuration{
		Name:      "probe",
		ServiceID: "svc",
		Admin:     config.AdminConfig{Endpoints: []string{"127.0.0.1:19001"}, SyncInterval: time.Minute},
	}

	sameAdmin := base
	if onlyAdminChanged(base, sameAdmin) {
		t.Error("identical configs should not report an admin-only change")
	}

	adminOnly := base
	adminOnly.Admin.SyncInterval = 2 * time.Minute
	if !onlyAdminChanged(base, adminOnly) {
		t.Error("a change confined to the admin block should be reported as such")
	}

	alsoServiceID := base
	alsoServiceID.Admin.SyncInterval = 2 * time.Minute
	alsoServiceID.ServiceID = "other"
	if onlyAdminChanged(base, alsoServiceID) {
		t.Error("a change outside the admin block must force a full reload")
	}
}

// TestRunAdminSync_StopsOnShutdown makes sure the loop honours shutdown even while sync is
// disabled, which is the state it spends most of its time in on an unconfigured probe.
func TestRunAdminSync_StopsOnShutdown(t *testing.T) {
	restoreCfg(t)
	p := syncProbe(t, "name: probe\n")

	stopped := make(chan struct{})
	go func() {
		defer close(stopped)
		p.runAdminSync()
	}()

	close(p.shutdown)
	select {
	case <-stopped:
	case <-time.After(5 * time.Second):
		t.Fatal("sync loop did not stop on shutdown")
	}
}

// TestRunAdminSync_ExitsWithoutConfigPath covers the probe started without a config file: there
// is nothing to write back to, so the loop must not spin.
func TestRunAdminSync_ExitsWithoutConfigPath(t *testing.T) {
	p := syncProbe(t, "name: probe\n")
	p.configPath = ""

	stopped := make(chan struct{})
	go func() {
		defer close(stopped)
		p.runAdminSync()
	}()

	select {
	case <-stopped:
	case <-time.After(5 * time.Second):
		t.Fatal("sync loop should exit immediately without a config path")
	}
}
