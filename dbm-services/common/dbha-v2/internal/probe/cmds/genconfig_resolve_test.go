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

package cmds

import (
	"bytes"
	"errors"
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

	_ "dbm-services/common/dbha-v2/internal/provider/mysql/harvest"
	_ "dbm-services/common/dbha-v2/internal/provider/redis/harvest"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/cobra"
)

func TestResolveGenConfigParams_ExplicitWins(t *testing.T) {
	local := config.Configuration{
		Admin: config.AdminConfig{
			Endpoints: []string{"127.0.0.1:19001"},
			BkCloudID: 5,
			LocalIP:   "127.0.0.1",
		},
		ClearPorts: []int{3306},
	}
	flags := genConfigFlags{
		endpoints:     []string{"127.0.0.1:19002"},
		cloudID:       7,
		cloudIDSet:    true,
		localIP:       "127.0.0.1",
		clearPorts:    []int{13306},
		clearPortsSet: true,
	}
	got, err := resolveGenConfigParams(flags, local, true)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	if !reflect.DeepEqual(got.endpoints, flags.endpoints) {
		t.Errorf("endpoints: %v", got.endpoints)
	}
	if got.bkCloudID != 7 || got.localIP != "127.0.0.1" || !reflect.DeepEqual(got.clearPorts, []int{13306}) {
		t.Errorf("resolved: %+v", got)
	}
}

func TestResolveGenConfigParams_InheritsFile(t *testing.T) {
	local := config.Configuration{
		Admin: config.AdminConfig{
			Endpoints: []string{"127.0.0.1:19001"},
			BkCloudID: 5,
			LocalIP:   "127.0.0.1",
		},
		ClearPorts: []int{3306},
	}
	flags := genConfigFlags{
		endpointsStr: "127.0.0.1:19002",
		endpoints:    []string{"127.0.0.1:19002"},
	}
	got, err := resolveGenConfigParams(flags, local, true)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	if got.bkCloudID != 5 {
		t.Errorf("bkCloudID: %d, want 5", got.bkCloudID)
	}
	if got.localIP != "127.0.0.1" {
		t.Errorf("localIP: %s", got.localIP)
	}
	if !reflect.DeepEqual(got.clearPorts, []int{3306}) {
		t.Errorf("clearPorts: %v", got.clearPorts)
	}
}

func TestResolveGenConfigParams_EmptyClearPortFlagClears(t *testing.T) {
	local := config.Configuration{ClearPorts: []int{3306}}
	flags := genConfigFlags{
		endpoints:     []string{"127.0.0.1:19001"},
		localIP:       "127.0.0.1",
		clearPortsSet: true,
	}
	got, err := resolveGenConfigParams(flags, local, true)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	if got.clearPorts != nil {
		t.Errorf("clearPorts should be emptied, got: %v", got.clearPorts)
	}
}

// TestResolveGenConfigParams_EmptyLocalIPFalls covers `--local-ip ""`, which deploy scripts
// produce when the shell variable they interpolate is unset. It must behave as if the flag were
// absent instead of asking admin for the empty IP.
func TestResolveGenConfigParams_EmptyLocalIPFalls(t *testing.T) {
	local := config.Configuration{
		Admin: config.AdminConfig{LocalIP: "127.0.0.1", BkCloudID: 5},
	}
	flags := genConfigFlags{endpoints: []string{"127.0.0.1:19001"}, localIP: ""}
	got, err := resolveGenConfigParams(flags, local, true)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	if got.localIP != "127.0.0.1" {
		t.Errorf("empty --local-ip should fall back to the file, got: %q", got.localIP)
	}
}

// TestApplyResolvedLocal_WritesBackEveryPullParam is the same-source invariant: every field that
// fetchProbePayload sends to admin must land in the admin block that gets written, or the periodic
// sync will pull a different payload and the two writers will fight over the harvester.
func TestApplyResolvedLocal_WritesBackEveryPullParam(t *testing.T) {
	local := config.Configuration{
		Admin: config.AdminConfig{
			Endpoints: []string{"127.0.0.1:19009"},
			BkCloudID: 5,
			LocalIP:   "127.0.0.1",
		},
	}
	flags := genConfigFlags{endpoints: []string{"127.0.0.1:19001", "127.0.0.1:19002"}}

	resolved, err := resolveGenConfigParams(flags, local, true)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	got, err := applyResolvedLocal(local, resolved, false)
	if err != nil {
		t.Fatalf("apply failed, errmsg: %s", err)
	}
	if !reflect.DeepEqual(got.Admin.Endpoints, resolved.endpoints) {
		t.Errorf("endpoints diverge, written: %v, fetched with: %v", got.Admin.Endpoints, resolved.endpoints)
	}
	if got.Admin.BkCloudID != resolved.bkCloudID {
		t.Errorf("bkCloudID diverges, written: %d, fetched with: %d", got.Admin.BkCloudID, resolved.bkCloudID)
	}
	if got.Admin.LocalIP != resolved.localIP {
		t.Errorf("localIP diverges, written: %s, fetched with: %s", got.Admin.LocalIP, resolved.localIP)
	}

	// The half above proves the written block matches the resolved values. This one proves the
	// request does too, so the two can never be sourced from different places.
	req := probeConfigRequest(resolved)
	if req.BkCloudId != got.Admin.BkCloudID {
		t.Errorf("request bkCloudID: %d, written: %d", req.BkCloudId, got.Admin.BkCloudID)
	}
	if req.Ip != got.Admin.LocalIP {
		t.Errorf("request ip: %s, written: %s", req.Ip, got.Admin.LocalIP)
	}
}

// TestProbeConfigRequest_MatchesNewFileAdminBlock covers the same invariant on the path that has
// no file to write back through: what a first deployment sends must equal what it records.
func TestProbeConfigRequest_MatchesNewFileAdminBlock(t *testing.T) {
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		bkCloudID: 5,
		localIP:   "127.0.0.1",
	}
	req := probeConfigRequest(resolved)
	admin := adminFromResolved(resolved)
	if !reflect.DeepEqual(admin.Endpoints, resolved.endpoints) {
		t.Errorf("endpoints: %v, want: %v", admin.Endpoints, resolved.endpoints)
	}
	if req.BkCloudId != admin.BkCloudID || req.Ip != admin.LocalIP {
		t.Errorf("request and recorded admin diverge, request: %d/%s, admin: %d/%s",
			req.BkCloudId, req.Ip, admin.BkCloudID, admin.LocalIP)
	}
	if admin.SyncInterval != 0 {
		t.Errorf("a new file must not turn periodic sync on, syncInterval: %s", admin.SyncInterval)
	}
}

func TestPrintAdminEndpointChange(t *testing.T) {
	usable := genConfigFile{baseline: genConfigBaseline{
		exists: true, usable: true, endpoints: []string{"127.0.0.1:19001", "127.0.0.1:19002"},
	}}

	var changed bytes.Buffer
	cmd := &cobra.Command{}
	cmd.SetOut(&changed)
	printAdminEndpointChange(cmd, usable, genConfigResolved{endpoints: []string{"127.0.0.1:19003"}})
	out := changed.String()
	if !strings.Contains(out, "127.0.0.1:19001;127.0.0.1:19002") || !strings.Contains(out, "127.0.0.1:19003") {
		t.Errorf("expected both the previous and the current list, got: %q", out)
	}

	var same bytes.Buffer
	cmd.SetOut(&same)
	printAdminEndpointChange(cmd, usable, genConfigResolved{
		endpoints: []string{"127.0.0.1:19001", "127.0.0.1:19002"},
	})
	if same.String() != "" {
		t.Errorf("an unchanged list must stay quiet, got: %q", same.String())
	}

	var fresh bytes.Buffer
	cmd.SetOut(&fresh)
	printAdminEndpointChange(cmd, genConfigFile{}, genConfigResolved{endpoints: []string{"127.0.0.1:19003"}})
	if fresh.String() != "" {
		t.Errorf("a new file has nothing to compare against, got: %q", fresh.String())
	}

	// A parsable file that never carried an endpoint list is the legacy case: printing it would
	// show an empty "previous", which reads as if something was lost.
	var noList bytes.Buffer
	cmd.SetOut(&noList)
	printAdminEndpointChange(
		cmd,
		genConfigFile{baseline: genConfigBaseline{exists: true, usable: true}},
		genConfigResolved{endpoints: []string{"127.0.0.1:19003"}},
	)
	if noList.String() != "" {
		t.Errorf("a file without an endpoint list has nothing to replace, got: %q", noList.String())
	}
}

func TestApplyResolvedLocal_CopiesReporter(t *testing.T) {
	original := &config.ReporterConfig{Name: "gse", BkCloudID: 5, Endpoint: "127.0.0.1:1"}
	local := config.Configuration{Reporter: original}
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		bkCloudID: 7,
		localIP:   "127.0.0.1",
	}
	got, err := applyResolvedLocal(local, resolved, true)
	if err != nil {
		t.Fatalf("apply failed, errmsg: %s", err)
	}
	if original.BkCloudID != 5 {
		t.Errorf("shared reporter was mutated, bkCloudID: %d", original.BkCloudID)
	}
	if got.Reporter == original {
		t.Fatal("reporter pointer must be replaced")
	}
	if got.Reporter.BkCloudID != 7 || got.Reporter.Name != "gse" {
		t.Errorf("copied reporter: %+v", got.Reporter)
	}
	if got.Admin.BkCloudID != 7 {
		t.Errorf("admin bkCloudID: %d", got.Admin.BkCloudID)
	}
}

func TestApplyResolvedLocal_CreatesReporterWhenMissing(t *testing.T) {
	local := config.Configuration{}
	resolved := genConfigResolved{bkCloudID: 9, localIP: "127.0.0.1", endpoints: []string{"127.0.0.1:19001"}}
	got, err := applyResolvedLocal(local, resolved, true)
	if err != nil {
		t.Fatalf("apply failed, errmsg: %s", err)
	}
	if got.Reporter == nil || got.Reporter.BkCloudID != 9 {
		t.Errorf("reporter: %+v", got.Reporter)
	}
}

func TestBaselinesMatch_ClearPortsChange(t *testing.T) {
	a := genConfigBaseline{
		exists: true, usable: true,
		endpoints: []string{"127.0.0.1:19001"}, bkCloudID: 5, localIP: "127.0.0.1",
		clearPorts: []int{3306},
	}
	b := a
	if !baselinesMatch(a, b) {
		t.Fatal("identical baselines should match")
	}
	b.clearPorts = []int{13306}
	if baselinesMatch(a, b) {
		t.Fatal("clearPorts change must fail the baseline")
	}
}

// TestReadGenConfigFile_BaselineSurvivesSyncWrite is the "no false positives" half of the baseline
// check: the periodic sync rewrites the whole file every time the harvester moves, and that must
// not make concurrent gen-config runs fail.
func TestReadGenConfigFile_BaselineSurvivesSyncWrite(t *testing.T) {
	path := filepath.Join(t.TempDir(), "probe.yaml")
	doc := "name: probe\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n  bkCloudID: 5\n" +
		"  localIP: 127.0.0.1\n  syncInterval: 5m\nclearPorts: [13306]\n"
	if err := os.WriteFile(path, []byte(doc), 0o644); err != nil {
		t.Fatalf("seed failed, errmsg: %s", err)
	}
	stage1, err := readGenConfigFile(path)
	if err != nil {
		t.Fatalf("stage 1 read failed, errmsg: %s", err)
	}

	rendered, err := configsync.Render(resolveTestPayload(), config.LocalFields(stage1.local)...)
	if err != nil {
		t.Fatalf("sync render failed, errmsg: %s", err)
	}
	if err := os.WriteFile(path, []byte(rendered), 0o644); err != nil {
		t.Fatalf("sync write failed, errmsg: %s", err)
	}

	stage3, err := readGenConfigFile(path)
	if err != nil {
		t.Fatalf("stage 3 read failed, errmsg: %s", err)
	}
	if !baselinesMatch(stage1.baseline, stage3.baseline) {
		t.Fatalf("a sync write tripped the baseline, stage1: %+v, stage3: %+v",
			stage1.baseline, stage3.baseline)
	}
}

func TestBaselinesMatch_ExistenceFlip(t *testing.T) {
	missing := genConfigBaseline{}
	created := genConfigBaseline{exists: true, usable: true, endpoints: []string{"127.0.0.1:19001"}}
	if baselinesMatch(missing, created) {
		t.Fatal("file appearing during fetch must fail the baseline")
	}
	if baselinesMatch(created, missing) {
		t.Fatal("file disappearing during fetch must fail the baseline")
	}
}

func TestReadGenConfigFile_EmptyAndMissing(t *testing.T) {
	missing, err := readGenConfigFile(filepath.Join(t.TempDir(), "no-such.yaml"))
	if err != nil {
		t.Fatalf("missing file should not error, errmsg: %s", err)
	}
	if missing.baseline.exists || missing.baseline.usable {
		t.Errorf("missing baseline: %+v", missing.baseline)
	}

	emptyPath := filepath.Join(t.TempDir(), "empty.yaml")
	if err := os.WriteFile(emptyPath, nil, 0o644); err != nil {
		t.Fatalf("write empty file failed, errmsg: %s", err)
	}
	empty, err := readGenConfigFile(emptyPath)
	if err != nil {
		t.Fatalf("empty file should not error, errmsg: %s", err)
	}
	if !empty.baseline.exists || empty.baseline.usable {
		t.Errorf("empty baseline: %+v", empty.baseline)
	}
}

func TestReadGenConfigFile_Usable(t *testing.T) {
	path := filepath.Join(t.TempDir(), "probe.yaml")
	doc := "name: probe\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n  bkCloudID: 5\n" +
		"  localIP: 127.0.0.1\n  syncInterval: 5m\nclearPorts: [3306]\n"
	if err := os.WriteFile(path, []byte(doc), 0o644); err != nil {
		t.Fatalf("write failed, errmsg: %s", err)
	}
	got, err := readGenConfigFile(path)
	if err != nil {
		t.Fatalf("read failed, errmsg: %s", err)
	}
	if !got.baseline.usable {
		t.Fatal("expected usable file")
	}
	if got.baseline.bkCloudID != 5 || got.baseline.localIP != "127.0.0.1" {
		t.Errorf("baseline: %+v", got.baseline)
	}
	if got.local.Admin.SyncInterval != 5*time.Minute {
		t.Errorf("syncInterval: %s", got.local.Admin.SyncInterval)
	}
}

func TestApplyResolvedLocal_KeepsSyncInterval(t *testing.T) {
	local := config.Configuration{
		Admin: config.AdminConfig{SyncInterval: 5 * time.Minute, BkCloudID: 1},
	}
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		bkCloudID: 1,
		localIP:   "127.0.0.1",
	}
	got, err := applyResolvedLocal(local, resolved, false)
	if err != nil {
		t.Fatalf("apply failed, errmsg: %s", err)
	}
	if got.Admin.SyncInterval != 5*time.Minute {
		t.Errorf("syncInterval lost: %s", got.Admin.SyncInterval)
	}
	if got.Reporter != nil {
		t.Errorf("reporter should stay nil when cloud-id is not explicit, got: %+v", got.Reporter)
	}
}

func resolveTestPayload() probeconfig.ProbeConfigPayload {
	return probeconfig.ProbeConfigPayload{
		Gse: probeconfig.GseConfig{Endpoint: "127.0.0.1:1234", DataID: 1, ConnTimeout: "5s"},
		MySQL: &probeconfig.ProbeMySQLConfig{
			User: "u", Password: "p", Interval: "20s", Timeout: "5s",
		},
		Metadata: []probeconfig.ProbeMetadataItem{
			{
				IP:          "127.0.0.1",
				Port:        3306,
				ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
				MachineType: string(haprobe.DbmMetadataMachineTypeBackend),
				AccessLayer: string(haprobe.DbmMetadataAccessLayerTypeStorage),
			},
		},
	}
}

// TestRenderLockedProbeYAML_NewFileWritesAdmin covers a first deployment: the target file does
// not exist yet, and the admin block the operator just supplied on the command line has to land
// in it. Writing it later is not an option, because the next gen-config would have nothing to
// inherit and periodic sync could never be switched on.
func TestRenderLockedProbeYAML_NewFileWritesAdmin(t *testing.T) {
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		bkCloudID: 5,
		localIP:   "127.0.0.1",
	}
	_, parsed, err := renderLockedProbeYAML(resolveTestPayload(), resolved, false, genConfigFile{})
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if !reflect.DeepEqual(parsed.Admin.Endpoints, resolved.endpoints) {
		t.Errorf("endpoints: %v, want: %v", parsed.Admin.Endpoints, resolved.endpoints)
	}
	if parsed.Admin.BkCloudID != 5 || parsed.Admin.LocalIP != "127.0.0.1" {
		t.Errorf("admin: %+v", parsed.Admin)
	}
	if parsed.Admin.SyncEnabled() {
		t.Error("a new file must not enable periodic sync on its own")
	}

	// Everything outside the admin block still comes from the payload alone: pulling the rest of
	// LocalFields in would pin defaultConfiguration() values into a brand-new file.
	bare, err := configsync.Render(resolveTestPayload(), config.WithAdmin(adminFromResolved(resolved)))
	if err != nil {
		t.Fatalf("bare render failed, errmsg: %s", err)
	}
	got, err := renderNewProbeYAML(resolveTestPayload(), resolved)
	if err != nil {
		t.Fatalf("new render failed, errmsg: %s", err)
	}
	if got != bare {
		t.Errorf("new-file render injected more than the admin block, got:\n%s", got)
	}
}

// TestRenderLockedProbeYAML_UnparsableFileFallsBackToNew keeps a corrupted file from wedging
// gen-config: the file is rewritten from admin instead of inheriting garbage, matching what
// reconcileConfigFile does on its own diskErr branch.
func TestRenderLockedProbeYAML_UnparsableFileFallsBackToNew(t *testing.T) {
	src := genConfigFile{
		baseline: genConfigBaseline{exists: true},
		parseErr: errors.New("yaml: line 2: mapping values are not allowed"),
	}
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		bkCloudID: 5,
		localIP:   "127.0.0.1",
	}
	yamlStr, parsed, err := renderLockedProbeYAML(resolveTestPayload(), resolved, true, src)
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if parsed.Client.PingTime != 0 {
		t.Errorf("garbage must not be inherited, client: %+v", parsed.Client)
	}
	if parsed.Admin.BkCloudID != 5 || len(parsed.Admin.Endpoints) != 1 {
		t.Errorf("self-healed file still needs the admin block, got: %+v", parsed.Admin)
	}
	fresh, err := renderNewProbeYAML(resolveTestPayload(), resolved)
	if err != nil {
		t.Fatalf("new render failed, errmsg: %s", err)
	}
	if yamlStr != fresh {
		t.Errorf("unparsable file should render like a new one, got:\n%s", yamlStr)
	}
}

func TestRenderLockedProbeYAML_KeepsLocalPidFile(t *testing.T) {
	src := genConfigFile{
		baseline: genConfigBaseline{exists: true, usable: true},
		local: config.Configuration{
			PidFile: "/tmp/custom/probe.pid",
			Admin:   config.AdminConfig{SyncInterval: 5 * time.Minute},
			Client:  config.ClientConfig{PingTime: 42 * time.Second},
		},
	}
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		bkCloudID: 5,
		localIP:   "127.0.0.1",
	}
	_, parsed, err := renderLockedProbeYAML(resolveTestPayload(), resolved, true, src)
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if parsed.PidFile != "/tmp/custom/probe.pid" {
		t.Errorf("pidFile: %s", parsed.PidFile)
	}
	if parsed.Client.PingTime != 42*time.Second {
		t.Errorf("client block was not preserved, pingTime: %s", parsed.Client.PingTime)
	}
	if parsed.Harvester.MySql == nil || len(parsed.Harvester.MySql.Endpoints) == 0 {
		t.Fatalf("harvester should carry the payload, got: %+v", parsed.Harvester)
	}
	if parsed.Admin.BkCloudID != 5 || parsed.Reporter == nil || parsed.Reporter.BkCloudID != 5 {
		t.Errorf("cloud id not written, admin: %+v reporter: %+v", parsed.Admin, parsed.Reporter)
	}
	if !parsed.Admin.SyncEnabled() {
		t.Errorf("sync should stay enabled, admin: %+v", parsed.Admin)
	}
}

func TestRenderLockedProbeYAML_HealsMissingAdmin(t *testing.T) {
	src := genConfigFile{
		baseline: genConfigBaseline{exists: true, usable: true},
		local:    config.Configuration{PidFile: "./pids/probe.pid"},
	}
	resolved := genConfigResolved{
		endpoints: []string{"127.0.0.1:19001"},
		localIP:   "127.0.0.1",
	}
	_, parsed, err := renderLockedProbeYAML(resolveTestPayload(), resolved, false, src)
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if len(parsed.Admin.Endpoints) != 1 {
		t.Errorf("expected healed admin endpoints, got: %+v", parsed.Admin)
	}
	if parsed.Admin.SyncEnabled() {
		t.Fatal("healed admin must not enable sync without an inherited interval")
	}
}

// seedGenConfigFile writes a probe.yaml that already carries an admin block, which is the state
// every gen-config run against a deployed machine starts from.
func seedGenConfigFile(t *testing.T) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), "probe.yaml")
	doc := "name: probe\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n  bkCloudID: 5\n" +
		"  localIP: 127.0.0.1\n  syncInterval: 5m\n"
	if err := os.WriteFile(path, []byte(doc), 0o644); err != nil {
		t.Fatalf("seed failed, errmsg: %s", err)
	}
	return path
}

// runGenConfigCommit replays everything gen-config does around the network call: the stage 1 read,
// parameter resolution, and the locked commit. Only the fetch is substituted.
func runGenConfigCommit(
	t *testing.T, path string, flags genConfigFlags, payload probeconfig.ProbeConfigPayload,
) error {
	t.Helper()

	stage1, err := readGenConfigFile(path)
	if err != nil {
		t.Fatalf("stage 1 read failed, errmsg: %s", err)
	}
	resolved, err := resolveGenConfigParams(flags, stage1.local, stage1.baseline.usable)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	cmd := &cobra.Command{}
	cmd.SetOut(&bytes.Buffer{})
	_, err = commitGenConfigFile(cmd, genConfigCommit{
		outputPath:  path,
		lockTimeout: 5 * time.Second,
		stage1:      stage1,
		resolved:    resolved,
		payload:     payload,
		cloudIDSet:  flags.cloudIDSet,
	})
	return err
}

// TestCommitGenConfigFile_TwiceIsByteIdentical is the gen-config half of the convergence argument:
// the values it resolves are the values it writes, so a second run with the same command line and
// the same payload has nothing left to change.
func TestCommitGenConfigFile_TwiceIsByteIdentical(t *testing.T) {
	path := seedGenConfigFile(t)
	flags := genConfigFlags{endpoints: []string{"127.0.0.1:19001"}, localIP: "127.0.0.1"}

	if err := runGenConfigCommit(t, path, flags, resolveTestPayload()); err != nil {
		t.Fatalf("first run failed, errmsg: %s", err)
	}
	first, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read after first run failed, errmsg: %s", err)
	}
	if err := runGenConfigCommit(t, path, flags, resolveTestPayload()); err != nil {
		t.Fatalf("second run failed, errmsg: %s", err)
	}
	second, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read after second run failed, errmsg: %s", err)
	}
	if string(first) != string(second) {
		t.Errorf("second run rewrote the file, first:\n%s\nsecond:\n%s", first, second)
	}
}

// TestCommitGenConfigFile_MissingFileConvergesOnSecondRun is the first-deployment flow:
// `gen-config --admin-endpoints X -o etc/probe.yaml` against a machine that has no config yet.
// The first run has to produce the same file the second one would, otherwise the admin block
// only appears after running the command twice.
func TestCommitGenConfigFile_MissingFileConvergesOnSecondRun(t *testing.T) {
	path := filepath.Join(t.TempDir(), "probe.yaml")
	flags := genConfigFlags{endpoints: []string{"127.0.0.1:19001"}, localIP: "127.0.0.1"}

	if err := runGenConfigCommit(t, path, flags, resolveTestPayload()); err != nil {
		t.Fatalf("first run failed, errmsg: %s", err)
	}
	first, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read after first run failed, errmsg: %s", err)
	}
	parsed, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse after first run failed, errmsg: %s", err)
	}
	if !reflect.DeepEqual(parsed.Admin.Endpoints, flags.endpoints) {
		t.Fatalf("first run dropped the admin endpoints, got: %+v", parsed.Admin)
	}

	if err := runGenConfigCommit(t, path, flags, resolveTestPayload()); err != nil {
		t.Fatalf("second run failed, errmsg: %s", err)
	}
	second, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read after second run failed, errmsg: %s", err)
	}
	if string(first) != string(second) {
		t.Errorf("second run changed the file, first:\n%s\nsecond:\n%s", first, second)
	}
}

// TestCommitGenConfigFile_AgreesWithSyncOutput is the cross-idempotency check in the direction
// the sync-side test does not cover: periodic sync writes the file, then gen-config runs against
// it with the same payload and must leave it untouched. The two writers differ in one step —
// gen-config puts the resolved parameters through applyResolvedLocal first — so if that step ever
// stopped being an identity for flags that match the file, the two would rewrite each other on
// every crontab tick.
func TestCommitGenConfigFile_AgreesWithSyncOutput(t *testing.T) {
	path := seedGenConfigFile(t)
	local, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse seed failed, errmsg: %s", err)
	}
	payload := resolveTestPayload()

	// This is exactly what reconcileConfigFile writes.
	synced, err := configsync.Render(payload, config.LocalFields(local)...)
	if err != nil {
		t.Fatalf("sync render failed, errmsg: %s", err)
	}
	if err := os.WriteFile(path, []byte(synced), 0o644); err != nil {
		t.Fatalf("write failed, errmsg: %s", err)
	}

	flags := genConfigFlags{endpoints: []string{"127.0.0.1:19001"}, localIP: "127.0.0.1"}
	if err := runGenConfigCommit(t, path, flags, payload); err != nil {
		t.Fatalf("commit failed, errmsg: %s", err)
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read failed, errmsg: %s", err)
	}
	if string(after) != synced {
		t.Errorf("gen-config rewrote what sync produced, sync:\n%s\ngen-config:\n%s", synced, after)
	}
}

// TestCommitGenConfigFile_WritesBeforeSignaling pins the ordering --reload relies on. The file is
// already on disk when the commit returns, and the pid file it reports is the one the new content
// declares rather than the process default, so a reload that finds no process cannot undo the
// write and cannot signal the wrong path.
func TestCommitGenConfigFile_WritesBeforeSignaling(t *testing.T) {
	path := filepath.Join(t.TempDir(), "probe.yaml")
	pidFile := filepath.Join(t.TempDir(), "custom.pid")
	doc := "name: probe\npidFile: " + pidFile + "\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n" +
		"  bkCloudID: 5\n  localIP: 127.0.0.1\n  syncInterval: 5m\n"
	if err := os.WriteFile(path, []byte(doc), 0o644); err != nil {
		t.Fatalf("seed failed, errmsg: %s", err)
	}

	stage1, err := readGenConfigFile(path)
	if err != nil {
		t.Fatalf("stage 1 read failed, errmsg: %s", err)
	}
	resolved, err := resolveGenConfigParams(
		genConfigFlags{endpoints: []string{"127.0.0.1:19001"}, localIP: "127.0.0.1"},
		stage1.local, stage1.baseline.usable,
	)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}
	cmd := &cobra.Command{}
	cmd.SetOut(&bytes.Buffer{})
	parsed, err := commitGenConfigFile(cmd, genConfigCommit{
		outputPath:  path,
		lockTimeout: 5 * time.Second,
		stage1:      stage1,
		resolved:    resolved,
		payload:     resolveTestPayload(),
	})
	if err != nil {
		t.Fatalf("commit failed, errmsg: %s", err)
	}
	if parsed.PidFile != pidFile {
		t.Errorf("reload would signal the wrong pid file, got: %s, want: %s", parsed.PidFile, pidFile)
	}

	// This is what runGenConfigToFile does next when --reload is set.
	if err := process.ReloadIfRunning(cmd, parsed.PidFile, "probe"); !errors.Is(err, process.ErrProcessNotRunning) {
		t.Fatalf("err: %v, want ErrProcessNotRunning", err)
	}
	after, err := config.Parse(path)
	if err != nil {
		t.Fatalf("config should survive a failed reload, errmsg: %s", err)
	}
	if after.Harvester.MySql == nil {
		t.Errorf("written harvester disappeared, got: %+v", after.Harvester)
	}
}

// TestCommitGenConfigFile_AbortsWhenFileChangedDuringFetch guards the read-fetch-write race: the
// resolved parameters belong to the file as it looked in stage 1, so pairing them with a file
// somebody else has since edited would silently revert that edit.
func TestCommitGenConfigFile_AbortsWhenFileChangedDuringFetch(t *testing.T) {
	path := seedGenConfigFile(t)
	stage1, err := readGenConfigFile(path)
	if err != nil {
		t.Fatalf("stage 1 read failed, errmsg: %s", err)
	}
	resolved, err := resolveGenConfigParams(
		genConfigFlags{endpoints: []string{"127.0.0.1:19001"}, localIP: "127.0.0.1"},
		stage1.local, stage1.baseline.usable,
	)
	if err != nil {
		t.Fatalf("resolve failed, errmsg: %s", err)
	}

	// Another writer bumps the cloud id while this run is waiting on admin.
	concurrent := "name: probe\nadmin:\n  endpoints: [\"127.0.0.1:19001\"]\n  bkCloudID: 9\n" +
		"  localIP: 127.0.0.1\n  syncInterval: 5m\n"
	if err := os.WriteFile(path, []byte(concurrent), 0o644); err != nil {
		t.Fatalf("concurrent write failed, errmsg: %s", err)
	}

	cmd := &cobra.Command{}
	cmd.SetOut(&bytes.Buffer{})
	_, err = commitGenConfigFile(cmd, genConfigCommit{
		outputPath:  path,
		lockTimeout: 5 * time.Second,
		stage1:      stage1,
		resolved:    resolved,
		payload:     resolveTestPayload(),
	})
	if err == nil {
		t.Fatal("a concurrent edit must abort the write")
	}
	if !strings.Contains(err.Error(), "retry gen-config") {
		t.Errorf("error should tell the operator to retry, errmsg: %s", err)
	}
	after, readErr := os.ReadFile(path)
	if readErr != nil {
		t.Fatalf("read after abort failed, errmsg: %s", readErr)
	}
	if string(after) != concurrent {
		t.Errorf("aborted run still touched the file, got:\n%s", after)
	}
}
