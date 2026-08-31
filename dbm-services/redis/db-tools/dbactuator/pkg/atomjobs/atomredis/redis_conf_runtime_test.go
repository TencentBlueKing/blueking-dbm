package atomredis

import (
	"fmt"
	"io"
	"strings"
	"testing"

	"dbm-services/common/go-pubpkg/logger"
)

func TestClassifyConfSetKind(t *testing.T) {
	if classifyConfSetKind("requirepass") != confSetSkip {
		t.Error("requirepass should be skip")
	}
	if classifyConfSetKind("replicaof") != confSetSkip {
		t.Error("replicaof should be skip")
	}
	if classifyConfSetKind("slaveof") != confSetSkip {
		t.Error("slaveof should be skip")
	}
	if classifyConfSetKind("maxmemory") != confSetSkip {
		t.Error("maxmemory should be skip")
	}
	if classifyConfSetKind("databases") != confSetSkip {
		t.Error("databases should be skip (restart-only, RedisInstance rewrites conf)")
	}
	if classifyConfSetKind("dir") != confSetApply {
		t.Error("dir should be apply (python chooses restart vs set)")
	}
	if classifyConfSetKind("rename-command") != confSetApply {
		t.Error("rename-command should be apply")
	}
	if classifyConfSetKind("tcp-backlog") != confSetApply {
		t.Error("tcp-backlog should be apply")
	}
	if classifyConfSetKind("timeout") != confSetApply {
		t.Error("timeout should be apply")
	}
	if classifyConfSetKind("save") != confSetApply {
		t.Error("save should be apply (joined into one SET)")
	}
}

func TestSameConfRuntimeValue(t *testing.T) {
	cases := []struct {
		a, b string
		eq   bool
	}{
		{`"/data/redis/30000/data"`, "/data/redis/30000/data", true},
		{"yes", "1", true},
		{"no", "0", true},
		{"256mb", "268435456", true},
		{"3600 1 300 100", "3600 1 300 100", true},
		{"normal 256mb 512mb 300", "normal 268435456 536870912 300", true},
		{"10", "20", false},
		{"", `""`, true},
	}
	for _, tc := range cases {
		if got := sameConfRuntimeValue(tc.a, tc.b); got != tc.eq {
			t.Errorf("sameConfRuntimeValue(%q,%q)=%v, want %v", tc.a, tc.b, got, tc.eq)
		}
	}
}

type fakeConfClient struct {
	get    map[string]string
	sets   [][2]string
	setErr map[string]error
}

func (f *fakeConfClient) ConfigGet(name string) (map[string]string, error) {
	v, ok := f.get[strings.ToLower(name)]
	if !ok {
		return map[string]string{}, nil
	}
	return map[string]string{name: v}, nil
}

func (f *fakeConfClient) ConfigSet(name, val string) (string, error) {
	if f.setErr != nil {
		if err := f.setErr[strings.ToLower(name)]; err != nil {
			return "", err
		}
	}
	f.sets = append(f.sets, [2]string{name, val})
	f.get[strings.ToLower(name)] = val
	return "OK", nil
}

func TestApplyConfigSet(t *testing.T) {
	log := logger.New(io.Discard, false, logger.InfoLevel)

	t.Run("skip list never set", func(t *testing.T) {
		cli := &fakeConfClient{get: map[string]string{
			"requirepass": "oldpass",
			"maxmemory":   "100",
			"timeout":     "10",
		}}
		conf := "requirepass newpass\nmaxmemory 200\ntimeout 10\n"
		if err := applyConfigSet(cli, conf, log); err != nil {
			t.Fatalf("err:%v", err)
		}
		for _, s := range cli.sets {
			if s[0] == "requirepass" || s[0] == "maxmemory" {
				t.Errorf("skip-list directive %s was SET", s[0])
			}
		}
	})

	t.Run("config set error hints restart", func(t *testing.T) {
		cli := &fakeConfClient{
			get:    map[string]string{"dir": "/old/data"},
			setErr: map[string]error{"dir": fmt.Errorf("ERR Unsupported CONFIG parameter: dir")},
		}
		err := applyConfigSet(cli, "dir /new/data\n", log)
		if err == nil || !strings.Contains(err.Error(), "apply_mode=restart") {
			t.Errorf("err=%v, want restart-mode hint", err)
		}
	})

	t.Run("rename-command unqueryable does not fail", func(t *testing.T) {
		cli := &fakeConfClient{get: map[string]string{}}
		if err := applyConfigSet(cli, "rename-command config confxx\ntimeout 10\n", log); err != nil {
			t.Errorf("unqueryable rename-command should skip, err:%v", err)
		}
		if len(cli.sets) != 0 {
			t.Errorf("unqueryable directive was SET: %v", cli.sets)
		}
	})

	t.Run("save join compared as one value", func(t *testing.T) {
		cli := &fakeConfClient{get: map[string]string{"save": "3600 1 300 100"}}
		conf := "save 3600 1\nsave 300 100\n"
		if err := applyConfigSet(cli, conf, log); err != nil {
			t.Fatalf("err:%v", err)
		}
		if len(cli.sets) != 0 {
			t.Errorf("matching save should not SET, got %v", cli.sets)
		}
	})

	t.Run("unchanged not set, changed set", func(t *testing.T) {
		cli := &fakeConfClient{get: map[string]string{"timeout": "10", "tcp-keepalive": "300"}}
		conf := "timeout 60\ntcp-keepalive 300\n"
		if err := applyConfigSet(cli, conf, log); err != nil {
			t.Fatalf("err:%v", err)
		}
		if len(cli.sets) != 1 || cli.sets[0][0] != "timeout" || cli.sets[0][1] != "60" {
			t.Errorf("sets=%v, want only timeout=60", cli.sets)
		}
	})

	t.Run("already matches", func(t *testing.T) {
		cli := &fakeConfClient{get: map[string]string{"timeout": "60"}}
		if err := applyConfigSet(cli, "timeout 60\n", log); err != nil {
			t.Fatalf("err:%v", err)
		}
		if len(cli.sets) != 0 {
			t.Errorf("no-diff should SET nothing, got %v", cli.sets)
		}
	})
}

func TestRuntimeMatchesPlanIgnoresSkipList(t *testing.T) {
	cli := &fakeConfClient{get: map[string]string{
		"requirepass": "diskpass",
		"maxmemory":   "999",
		"timeout":     "60",
	}}
	conf := "requirepass otherpass\nmaxmemory 1\ntimeout 60\n"
	ok, err := runtimeMatchesPlan(cli, conf)
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Error("skip-list mismatch should not make runtime unsettled")
	}

	cli.get["timeout"] = "10"
	ok, err = runtimeMatchesPlan(cli, conf)
	if err != nil {
		t.Fatal(err)
	}
	if ok {
		t.Error("settable mismatch should make runtime unsettled")
	}
}

func TestJoinDirectiveValues(t *testing.T) {
	got := joinDirectiveValues([]string{"3600 1", "300 100"})
	if got != "3600 1 300 100" {
		t.Errorf("join save = %q", got)
	}
	got = joinDirectiveValues([]string{`"xxxxpasswd"`})
	if got != "xxxxpasswd" {
		t.Errorf("unquote join = %q", got)
	}
}
