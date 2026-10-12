package redisconf

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/go-pubpkg/logger"
)

// includePlan 一份 GCS 布局的重建计划: redis.conf include 了实例目录里的 instance.conf
func includePlan(t *testing.T) (plan *Plan, instConf string) {
	t.Helper()
	instDir := t.TempDir()
	confFile := filepath.Join(instDir, "redis.conf")
	instConf = filepath.Join(instDir, "instance.conf")
	raw := "port 30000\ninclude " + instConf + "\n"
	writeTestFile(t, confFile, raw)
	writeTestFile(t, instConf, "requirepass xxxxpasswd\n")
	return &Plan{
		Port:       30000,
		ConfFile:   confFile,
		OldConf:    "port 30000\nrequirepass xxxxpasswd\n",
		RawOldConf: raw,
		Includes:   []string{instConf, instConf},
		NewConf:    "port 30000\nrequirepass xxxxpasswd\n",
	}, instConf
}

func TestPlanChanges(t *testing.T) {
	plan, _ := includePlan(t)
	changes := plan.Changes()
	// 重复 include 同一个文件只退役一次
	if len(changes) != 2 {
		t.Fatalf("changes = %v, want conf write + one include retire", changes)
	}
	if plan.NeedsStopped() {
		t.Error("conf write and include retire can run while the process is up")
	}

	plan.NodesMove = &NodesFileMove{From: "/a/nodes-30000.conf", To: "/a/nodes.conf"}
	changes = plan.Changes()
	if len(changes) != 3 || !plan.NeedsStopped() {
		t.Errorf("nodes file move must be planned and require a stopped process, got %v", changes)
	}
	// 每次返回新的动作: 执行状态不能串到 Plan 上
	if changes[2].(*NodesFileMove) == plan.NodesMove {
		t.Error("Changes should hand out a copy of NodesMove")
	}
}

func TestApplyChangesAndUndo(t *testing.T) {
	plan, instConf := includePlan(t)
	applied, err := ApplyChanges(plan.Changes(), testLogger())
	if err != nil {
		t.Fatalf("ApplyChanges err:%v", err)
	}
	if got := readTestFile(t, plan.ConfFile); got != plan.NewConf {
		t.Errorf("conf not written:\n%s", got)
	}
	if backup := applied.ConfBackup(); backup == "" || readTestFile(t, backup) != plan.RawOldConf {
		t.Errorf("backup should hold the raw conf with include, backup=%q", backup)
	}
	if _, err = os.Stat(instConf); !os.IsNotExist(err) {
		t.Errorf("instance.conf should be retired,stat err:%v", err)
	}

	if err = applied.Undo(testLogger()); err != nil {
		t.Fatalf("Undo err:%v", err)
	}
	if got := readTestFile(t, plan.ConfFile); got != plan.RawOldConf {
		t.Errorf("conf should be back to the raw conf:\n%s", got)
	}
	if got := readTestFile(t, instConf); got != "requirepass xxxxpasswd\n" {
		t.Errorf("instance.conf should be back,got %q", got)
	}
	if !applied.Empty() {
		t.Error("nothing should remain applied after Undo")
	}
}

func TestApplyChangesRestoresWhenRetireFails(t *testing.T) {
	plan, instConf := includePlan(t)
	orig := renameIncludedConfFile
	renameIncludedConfFile = func(string, string) error { return os.ErrPermission }
	t.Cleanup(func() { renameIncludedConfFile = orig })

	applied, err := ApplyChanges(plan.Changes(), testLogger())
	if err == nil || !strings.Contains(err.Error(), "retire include") {
		t.Fatalf("err = %v, want retire failure", err)
	}
	if applied != nil {
		t.Error("failed ApplyChanges should not hand out anything to undo")
	}
	if got := readTestFile(t, plan.ConfFile); got != plan.RawOldConf {
		t.Errorf("redis.conf should be restored to the raw conf,got:\n%s", got)
	}
	if _, statErr := os.Stat(instConf); statErr != nil {
		t.Errorf("instance.conf should stay in place,err:%v", statErr)
	}
}

// fakeChange 记录调用顺序, 可以让 Apply 失败
type fakeChange struct {
	name    string
	failErr error
	log     *[]string
}

func (c *fakeChange) String() string     { return c.name }
func (c *fakeChange) NeedsStopped() bool { return false }

func (c *fakeChange) Apply(_ *logger.Logger) error {
	if c.failErr != nil {
		return c.failErr
	}
	*c.log = append(*c.log, "apply "+c.name)
	return nil
}

func (c *fakeChange) Undo(_ *logger.Logger) error {
	*c.log = append(*c.log, "undo "+c.name)
	return nil
}

func TestApplyChangesUndoesInReverseOnFailure(t *testing.T) {
	var calls []string
	changes := []Change{
		&fakeChange{name: "a", log: &calls},
		&fakeChange{name: "b", log: &calls},
		&fakeChange{name: "c", failErr: errors.New("boom"), log: &calls},
	}
	_, err := ApplyChanges(changes, testLogger())
	if err == nil || !strings.Contains(err.Error(), "c failed: boom") {
		t.Fatalf("err = %v", err)
	}
	want := "apply a,apply b,undo b,undo a"
	if got := strings.Join(calls, ","); got != want {
		t.Errorf("calls = %s, want %s", got, want)
	}
}
