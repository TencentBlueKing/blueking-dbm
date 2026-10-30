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
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"

	"github.com/spf13/cobra"
)

func TestParsePausePorts(t *testing.T) {
	cases := []struct {
		name    string
		input   string
		want    []int
		wantErr bool
	}{
		{name: "empty means every port", input: "", want: nil},
		{name: "single", input: "3306", want: []int{3306}},
		{name: "comma and semicolon", input: "3306;6379,6380", want: []int{3306, 6379, 6380}},
		{name: "range", input: "30000-30002", want: []int{30000, 30001, 30002}},
		{name: "mixed", input: "3306,30000-30001", want: []int{3306, 30000, 30001}},
		{name: "dedup", input: "3306,3306", want: []int{3306}},
		{name: "non numeric", input: "3306,abc", wantErr: true},
		{name: "reversed range", input: "30002-30000", wantErr: true},
		{name: "separator only", input: ",,;", wantErr: true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parsePausePorts(tc.input)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected an error, got ports: %v", got)
				}
				return
			}
			if err != nil {
				t.Fatalf("parse failed, errmsg: %s", err)
			}
			if len(got) != len(tc.want) {
				t.Fatalf("ports = %v, want %v", got, tc.want)
			}
			for i := range tc.want {
				if got[i] != tc.want[i] {
					t.Errorf("ports = %v, want %v", got, tc.want)
					break
				}
			}
		})
	}
}

func TestMergePausePortsAppendsAndRefreshes(t *testing.T) {
	now := time.Now()
	pauseReq := func(ports []int, duration time.Duration) pauseRequest {
		return pauseRequest{ports: ports, hasPorts: len(ports) > 0, pause: true, duration: duration, now: now}
	}

	first := mergePausePorts(nil, pauseReq([]int{3306}, 10*time.Minute))
	if len(first) != 1 || first[0].ExpireAt != now.Add(10*time.Minute).Unix() {
		t.Fatalf("first merge = %+v", first)
	}

	both := mergePausePorts(first, pauseReq([]int{6379}, 20*time.Minute))
	if len(both) != 2 {
		t.Fatalf("append failed, got: %+v", both)
	}

	refreshed := mergePausePorts(both, pauseReq([]int{3306}, 30*time.Minute))
	if len(refreshed) != 2 {
		t.Fatalf("refresh must not add an entry, got: %+v", refreshed)
	}
	for _, p := range refreshed {
		if p.Port != 3306 {
			continue
		}
		if p.ExpireAt != now.Add(30*time.Minute).Unix() {
			t.Errorf("port 3306 expireAt = %d, want the refreshed one", p.ExpireAt)
		}
	}
}

func TestMergePausePortsResume(t *testing.T) {
	now := time.Now()
	pauseReq := pauseRequest{
		ports: []int{3306, 6379}, hasPorts: true, pause: true, duration: 10 * time.Minute, now: now,
	}
	paused := mergePausePorts(nil, pauseReq)

	one := mergePausePorts(paused, pauseRequest{ports: []int{3306}, hasPorts: true, now: now})
	if len(one) != 1 || one[0].Port != 6379 {
		t.Fatalf("resume one = %+v, want only 6379 left", one)
	}

	all := mergePausePorts(paused, pauseRequest{now: now})
	if len(all) != 0 {
		t.Fatalf("resume all = %+v, want empty", all)
	}
}

func TestRenderWithPausePortsKeepsRestOfFile(t *testing.T) {
	original := "# top comment\nname: probe\npidFile: ./pids/probe.pid\nclearPorts:\n    - 1\n"
	path := writeTempConfig(t, original)

	rendered, err := renderWithPausePorts(path, []config.PausePort{{Port: 3306, ExpireAt: 1761623400}})
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}

	out := string(rendered)
	for _, want := range []string{"# top comment", "name: probe", "pidFile: ./pids/probe.pid", "clearPorts:", "pausePorts:"} {
		if !strings.Contains(out, want) {
			t.Errorf("rendered yaml lost %q, got:\n%s", want, out)
		}
	}

	parsed, err := config.ParseBytes(rendered)
	if err != nil {
		t.Fatalf("rendered yaml does not parse, errmsg: %s", err)
	}
	if len(parsed.PausePorts) != 1 || parsed.PausePorts[0].Port != 3306 {
		t.Errorf("parsed pause ports = %+v", parsed.PausePorts)
	}
}

func TestRenderWithPausePortsRemovesKeyWhenEmpty(t *testing.T) {
	path := writeTempConfig(t, "name: probe\npausePorts:\n    - port: 3306\n      expireAt: 1761623400\n")

	rendered, err := renderWithPausePorts(path, nil)
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if strings.Contains(string(rendered), "pausePorts") {
		t.Errorf("empty list must drop the key, got:\n%s", rendered)
	}
}

func TestIntersectPorts(t *testing.T) {
	kept, ignored := intersectPorts([]int{1, 2, 3, 3306, 65535}, []int{3306, 6379})
	if len(kept) != 1 || kept[0] != 3306 {
		t.Errorf("kept = %v, want [3306]", kept)
	}
	if ignored != 4 {
		t.Errorf("ignored = %d, want 4", ignored)
	}
}

func TestResolvePauseTargetsResume(t *testing.T) {
	expire := time.Now().Add(time.Minute).Unix()
	disk := config.Configuration{PausePorts: []config.PausePort{
		{Port: 3306, ExpireAt: expire},
		{Port: 6379, ExpireAt: expire},
	}}

	write, reported, _ := resolvePauseTargets(disk, pauseFlags{ports: []int{3306, 9999}, hasPorts: true}, false)
	if len(reported) != 1 || reported[0] != 3306 {
		t.Errorf("reported = %v, want only the paused 3306", reported)
	}
	if len(write) != 2 {
		t.Errorf("write ports = %v, want the requested ones verbatim", write)
	}

	// Resuming everything must clear every entry, including ports that left the
	// configuration while they were paused.
	writeAll, reportedAll, _ := resolvePauseTargets(disk, pauseFlags{}, false)
	if len(writeAll) != 0 {
		t.Errorf("write ports = %v, want empty so the whole list is cleared", writeAll)
	}
	if len(reportedAll) != 2 {
		t.Errorf("reported = %v, want both paused ports", reportedAll)
	}
}

func TestFormatPortListShortensLongLists(t *testing.T) {
	short := formatPortList([]int{3306, 6379})
	if short != "3306, 6379" {
		t.Errorf("short list = %q", short)
	}

	ports := make([]int, 25)
	for i := range ports {
		ports[i] = 30000 + i
	}
	long := formatPortList(ports)
	if !strings.Contains(long, "(+5 more)") {
		t.Errorf("long list must be shortened, got: %q", long)
	}
}

func TestPrintPauseResultNoChange(t *testing.T) {
	cases := []struct {
		req  pauseRequest
		want string
	}{
		{req: pauseRequest{pause: true, hasPorts: true}, want: "not in the current collection scope"},
		{req: pauseRequest{pause: true}, want: "no port is being collected"},
		{req: pauseRequest{hasPorts: true}, want: "no paused port matches the requested ports"},
		{req: pauseRequest{}, want: "no paused port to resume"},
	}

	for _, tc := range cases {
		out := &bytes.Buffer{}
		printPauseResult(out, tc.req, nil)
		if !strings.Contains(out.String(), tc.want) {
			t.Errorf("output = %q, want %q", out.String(), tc.want)
		}
	}
}

// TestResumeAllClearsLeftovers guards the case a paused port left the config
// while it was paused: resuming everything must still drop it.
func TestResumeAllClearsLeftovers(t *testing.T) {
	expire := time.Now().Add(time.Hour).Unix()
	path := writeTempConfig(t, fixtureConfig()+fmt.Sprintf(
		"pausePorts:\n    - port: 9999\n      duration: 10m\n      expireAt: %d\n", expire))

	out := &bytes.Buffer{}
	cmd := newCollectCmd(t, path, true)
	cmd.SetOut(out)
	if err := CollectResumeCmdRunE(cmd, nil); err != nil {
		t.Fatalf("collect-resume failed, errmsg: %s", err)
	}

	parsed, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if len(parsed.PausePorts) != 0 {
		t.Fatalf("pause ports = %+v, want the list cleared", parsed.PausePorts)
	}
	if !strings.Contains(out.String(), "resumed 1 ports: 9999") {
		t.Errorf("output = %q, want the resumed port", out.String())
	}
}

// TestApplyPausePortsNarrowsHugeRange is the regression guard for the case that
// started this: a range typed by accident must not put thousands of entries in
// the config, and must not flood the output.
func TestApplyPausePortsNarrowsHugeRange(t *testing.T) {
	path := writeTempConfig(t, fixtureConfig())

	out := &bytes.Buffer{}
	cmd := newPauseCmd(t, path)
	cmd.SetOut(out)
	if err := CollectPauseCmdRunE(cmd, []string{"1-65535"}); err != nil {
		t.Fatalf("collect-pause failed, errmsg: %s", err)
	}

	parsed, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if len(parsed.PausePorts) != 3 {
		t.Fatalf("pause ports = %+v, want the 3 collected ports only", parsed.PausePorts)
	}

	text := out.String()
	for _, want := range []string{
		"are not in the current collection scope",
		"paused 3 ports",
		"currently paused (3)",
	} {
		if !strings.Contains(text, want) {
			t.Errorf("output missing %q, got:\n%s", want, text)
		}
	}
	if lines := strings.Count(strings.TrimSpace(text), "\n") + 1; lines > 10 {
		t.Errorf("output must stay short, got %d lines:\n%s", lines, text)
	}
}

// TestApplyPausePortsNoMatchWritesNothing makes sure a no-op cannot look like
// the ports were applied.
func TestApplyPausePortsNoMatchWritesNothing(t *testing.T) {
	path := writeTempConfig(t, fixtureConfig())
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read failed, errmsg: %s", err)
	}

	out := &bytes.Buffer{}
	cmd := newPauseCmd(t, path)
	cmd.SetOut(out)
	if err := CollectPauseCmdRunE(cmd, []string{"40000-40010"}); err != nil {
		t.Fatalf("collect-pause failed, errmsg: %s", err)
	}

	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read failed, errmsg: %s", err)
	}
	if !bytes.Equal(before, after) {
		t.Error("a no-op must not rewrite the config file")
	}
	if !strings.Contains(out.String(), "not in the current collection scope") {
		t.Errorf("output = %q, want the scope hint", out.String())
	}
	if strings.Contains(out.String(), "paused 0 ports") {
		t.Errorf("output must not claim an empty pause, got:\n%s", out.String())
	}
}

// TestRenderWithPausePortsReplacesInPlace guards that a second write only swaps
// the value of the existing key: the key keeps its position and the sibling keys
// below it keep both their order and their content.
func TestRenderWithPausePortsReplacesInPlace(t *testing.T) {
	doc := "name: probe\npausePorts:\n    - port: 3306\n      duration: 1m\n" +
		"      expireAt: 1761623400\nother: 1\ntail: last\n"
	path := writeTempConfig(t, doc)

	rendered, err := renderWithPausePorts(path, []config.PausePort{
		{Port: 3307, Duration: 10 * time.Minute, ExpireAt: 1761623500},
	})
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}

	out := string(rendered)
	if !strings.Contains(out, "port: 3307") || strings.Contains(out, "port: 3306") {
		t.Errorf("pause ports were not replaced, got:\n%s", out)
	}

	pauseAt, otherAt, tailAt := strings.Index(out, "pausePorts:"), strings.Index(out, "other: 1"),
		strings.Index(out, "tail: last")
	if pauseAt < 0 || otherAt < 0 || tailAt < 0 {
		t.Fatalf("a top level key is missing, got:\n%s", out)
	}
	if !(pauseAt < otherAt && otherAt < tailAt) {
		t.Errorf("top level key order changed, got:\n%s", out)
	}

	// Clearing drops only the pausePorts pair; the rest stays put.
	cleared, err := renderWithPausePorts(path, nil)
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if strings.Contains(string(cleared), "pausePorts") {
		t.Errorf("pausePorts must be removed, got:\n%s", cleared)
	}
	if !strings.Contains(string(cleared), "other: 1") || !strings.Contains(string(cleared), "tail: last") {
		t.Errorf("sibling keys were lost, got:\n%s", cleared)
	}
}

// TestRenderWithPausePortsKeepsReadableDuration guards the yaml encoding of
// time.Duration: it must stay a readable string ("10m0s") and survive a parse,
// not a nanosecond integer.
func TestRenderWithPausePortsKeepsReadableDuration(t *testing.T) {
	path := writeTempConfig(t, "name: probe\n")

	rendered, err := renderWithPausePorts(path, []config.PausePort{
		{Port: 3306, Duration: 10 * time.Minute, ExpireAt: 1761623400},
	})
	if err != nil {
		t.Fatalf("render failed, errmsg: %s", err)
	}
	if !strings.Contains(string(rendered), "duration: 10m0s") {
		t.Errorf("rendered yaml = %q, want a readable duration", rendered)
	}

	parsed, err := config.ParseBytes(rendered)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if parsed.PausePorts[0].Duration != 10*time.Minute {
		t.Errorf("duration = %v, want 10m", parsed.PausePorts[0].Duration)
	}
}

// TestMergePausePortsDropsExpiredOnWrite guards that an expired entry left in
// the file is cleaned up by the next write instead of living there forever.
func TestMergePausePortsDropsExpiredOnWrite(t *testing.T) {
	now := time.Now()
	current := []config.PausePort{
		{Port: 3306, ExpireAt: now.Add(-time.Minute).Unix()},
		{Port: 6379, ExpireAt: now.Add(time.Hour).Unix()},
	}

	req := pauseRequest{
		ports: []int{3307}, hasPorts: true, pause: true, duration: 10 * time.Minute, now: now,
	}
	got := mergePausePorts(current, req)

	if len(got) != 2 {
		t.Fatalf("merged = %+v, want the active entry plus the new one", got)
	}
	for _, port := range pausePortNumbers(got) {
		if port == 3306 {
			t.Errorf("merged = %+v, expired port 3306 must be dropped", got)
		}
	}
}

// TestPauseDropsExpiredEntriesFromFile is the same rule seen from the command:
// pausing another port must not carry an expired entry back into the file.
func TestPauseDropsExpiredEntriesFromFile(t *testing.T) {
	expired := time.Now().Add(-time.Hour).Unix()
	path := writeTempConfig(t, fixtureConfig()+fmt.Sprintf(
		"pausePorts:\n    - port: 9999\n      duration: 10m\n      expireAt: %d\n", expired))

	out := &bytes.Buffer{}
	cmd := newPauseCmd(t, path)
	cmd.SetOut(out)
	if err := CollectPauseCmdRunE(cmd, []string{"3306"}); err != nil {
		t.Fatalf("collect-pause failed, errmsg: %s", err)
	}

	parsed, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if len(parsed.PausePorts) != 1 || parsed.PausePorts[0].Port != 3306 {
		t.Fatalf("pause ports = %+v, want only 3306", parsed.PausePorts)
	}
}

// TestActivePausePortsDropsExpired guards the lazy expiry: entries past their
// time stay in the file but must never be reported or resumed.
func TestActivePausePortsDropsExpired(t *testing.T) {
	now := time.Now().Unix()
	cfg := config.Configuration{PausePorts: []config.PausePort{
		{Port: 3306, ExpireAt: now + 60},
		{Port: 3307, ExpireAt: now - 60},
	}}

	got := activePausePorts(cfg)
	if len(got) != 1 || got[0].Port != 3306 {
		t.Errorf("activePausePorts() = %+v, want only port 3306", got)
	}
}

// TestCollectPauseShowOnlyReads guards that --show lists the paused ports
// without touching the file or notifying the probe.
func TestCollectPauseShowOnlyReads(t *testing.T) {
	path := writeTempConfig(t, fixtureConfig())

	pauseCmd := newPauseCmd(t, path)
	pauseCmd.SetOut(&bytes.Buffer{})
	if err := CollectPauseCmdRunE(pauseCmd, []string{"3306"}); err != nil {
		t.Fatalf("collect-pause failed, errmsg: %s", err)
	}
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read failed, errmsg: %s", err)
	}

	out := &bytes.Buffer{}
	showCmd := newPauseCmd(t, path)
	showCmd.SetOut(out)
	if err := showCmd.Flags().Set("show", "true"); err != nil {
		t.Fatalf("set show failed, errmsg: %s", err)
	}
	if err := CollectPauseCmdRunE(showCmd, []string{"6379"}); err != nil {
		t.Fatalf("collect-pause --show failed, errmsg: %s", err)
	}

	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read failed, errmsg: %s", err)
	}
	if !bytes.Equal(before, after) {
		t.Error("--show must not rewrite the config file")
	}
	if !strings.Contains(out.String(), "currently paused (1): 3306") {
		t.Errorf("output = %q, want the paused 3306 only", out.String())
	}
	if strings.Contains(out.String(), "paused 1 ports") {
		t.Errorf("output = %q, --show must not report a change", out.String())
	}
}

// TestCollectPauseAcceptsPositionalPorts covers the spellings the positional
// ports support: several arguments, and comma separated ports in one argument.
func TestCollectPauseAcceptsPositionalPorts(t *testing.T) {
	path := writeTempConfig(t, fixtureConfig())

	out := &bytes.Buffer{}
	cmd := newPauseCmd(t, path)
	cmd.SetOut(out)
	if err := CollectPauseCmdRunE(cmd, []string{"3306", "6379,3307"}); err != nil {
		t.Fatalf("collect-pause failed, errmsg: %s", err)
	}

	parsed, err := config.Parse(path)
	if err != nil {
		t.Fatalf("parse failed, errmsg: %s", err)
	}
	if len(parsed.PausePorts) != 3 {
		t.Fatalf("pause ports = %+v, want 3306/3307/6379", parsed.PausePorts)
	}
	if !strings.Contains(out.String(), "paused 3 ports") {
		t.Errorf("output = %q, want the paused summary", out.String())
	}
}

func newPauseCmd(t *testing.T, configPath string) *cobra.Command {
	t.Helper()
	return newCollectCmd(t, configPath, false)
}

func newCollectCmd(t *testing.T, configPath string, resume bool) *cobra.Command {
	t.Helper()

	runE := CollectPauseCmdRunE
	if resume {
		runE = CollectResumeCmdRunE
	}

	root := &cobra.Command{Use: "probe"}
	root.PersistentFlags().String("config", configPath, "")
	cmd := &cobra.Command{Use: "collect", RunE: runE}
	cmd.Flags().Duration("duration", DefaultPauseDuration, "")
	cmd.Flags().Bool("show", false, "")
	root.AddCommand(cmd)
	return cmd
}

func fixtureConfig() string {
	return "name: probe\npidFile: ./pids/probe.pid\nharvester:\n" +
		"    mysql:\n        user: u\n        password: p\n        interval: 20s\n" +
		"        timeout: 5s\n        endpoints:\n" +
		"            - proto: tcp\n              clusterType: tendbha\n" +
		"              machineType: backend\n              instanceRole: \"\"\n" +
		"              accessLayer: storage\n              ip: 127.0.0.1\n" +
		"              ports:\n                - \"3306\"\n                - \"3307\"\n" +
		"              adminPorts: []\n" +
		"    redis:\n        user: \"\"\n        password: \"\"\n        interval: 20s\n" +
		"        timeout: 5s\n        endpoints:\n" +
		"            - proto: tcp\n              clusterType: RedisInstance\n" +
		"              machineType: tendiscache\n              instanceRole: \"\"\n" +
		"              accessLayer: storage\n              ip: 127.0.0.1\n" +
		"              ports:\n                - \"6379\"\n              adminPorts: []\n"
}

func writeTempConfig(t *testing.T, content string) string {
	t.Helper()

	path := t.TempDir() + "/probe.yaml"
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatalf("write fixture failed, errmsg: %s", err)
	}
	return path
}
