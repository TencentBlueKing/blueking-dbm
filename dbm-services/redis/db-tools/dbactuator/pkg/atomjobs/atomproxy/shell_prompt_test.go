package atomproxy

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

// useTempShellPromptFile 将提示符脚本路径注入临时目录, 测试结束后还原
func useTempShellPromptFile(t *testing.T) string {
	t.Helper()
	oldPath := consts.RedisShellPromptFilePath
	path := filepath.Join(t.TempDir(), "profile.d", consts.RedisShellPromptFileName)
	consts.RedisShellPromptFilePath = path
	t.Cleanup(func() { consts.RedisShellPromptFilePath = oldPath })
	return path
}

// newProxyTestRuntime 构造测试用 runtime, 日志丢弃
func newProxyTestRuntime() *jobruntime.JobGenericRuntime {
	testLogger := logger.New(io.Discard, false, logger.InfoLevel)
	mylog.SetDefaultLogger(testLogger)
	return &jobruntime.JobGenericRuntime{Logger: testLogger}
}

// readPromptFile 读取提示符脚本内容
func readPromptFile(t *testing.T, path string) string {
	t.Helper()
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read prompt file %s failed:%v", path, err)
	}
	return string(content)
}

func TestPredixyInstallSetShellPrompt(t *testing.T) {
	path := useTempShellPromptFile(t)
	job := &PredixyInstall{
		runtime:    newProxyTestRuntime(),
		ConfParams: &PredixyConfParams{IP: "1.1.1.1"},
	}
	job.setShellPrompt()
	content := readPromptFile(t, path)
	if !strings.Contains(content, "@predixy-1.1.1.1 ") {
		t.Fatalf("predixy prompt label not written, content:%s", content)
	}
	if !strings.Contains(content, "PS1='[\\t \\u@predixy-1.1.1.1 \\W]\\$ '") {
		t.Fatalf("unexpected predixy prompt content:%s", content)
	}
}

func TestTwemproxyInstallSetShellPrompt(t *testing.T) {
	path := useTempShellPromptFile(t)
	job := &twemproxyInstall{
		runtime: newProxyTestRuntime(),
		params:  &TwemproxyInstallParams{IP: "1.1.1.2"},
	}
	job.setShellPrompt()
	content := readPromptFile(t, path)
	if !strings.Contains(content, "@twemproxy-1.1.1.2 ") {
		t.Fatalf("twemproxy prompt label not written, content:%s", content)
	}
}

func TestProxyOperateRemoveShellPrompt(t *testing.T) {
	path := useTempShellPromptFile(t)
	if err := consts.SetRedisShellPrompt("predixy-1.1.1.1", true); err != nil {
		t.Fatalf("prepare prompt file failed:%v", err)
	}
	job := &PredixyOperate{runtime: newProxyTestRuntime(), params: &PredixyOperateParams{IP: "1.1.1.1"}}
	job.removeShellPrompt()
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("predixy prompt file should be removed, stat err:%v", err)
	}
	// 已删除后再调用不报错(幂等)
	job.removeShellPrompt()

	if err := consts.SetRedisShellPrompt("twemproxy-1.1.1.2", true); err != nil {
		t.Fatalf("prepare prompt file failed:%v", err)
	}
	twemproxyJob := &TwemproxyOperate{runtime: newProxyTestRuntime(), params: &TwemproxyOperateParams{IP: "1.1.1.2"}}
	twemproxyJob.removeShellPrompt()
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("twemproxy prompt file should be removed, stat err:%v", err)
	}
	twemproxyJob.removeShellPrompt()
}

func TestProxyInstallSetShellPromptDegradesWhenUnwritable(t *testing.T) {
	oldPath := consts.RedisShellPromptFilePath
	parent := filepath.Join(t.TempDir(), "not-a-dir")
	if err := os.WriteFile(parent, []byte("x"), 0644); err != nil {
		t.Fatalf("prepare unwritable parent failed:%v", err)
	}
	consts.RedisShellPromptFilePath = filepath.Join(parent, consts.RedisShellPromptFileName)
	t.Cleanup(func() { consts.RedisShellPromptFilePath = oldPath })

	// 写入失败只应告警, 不得 panic 或阻断调用方后续步骤
	predixyJob := &PredixyInstall{
		runtime:    newProxyTestRuntime(),
		ConfParams: &PredixyConfParams{IP: "1.1.1.1"},
	}
	predixyJob.setShellPrompt()
	twemproxyJob := &twemproxyInstall{
		runtime: newProxyTestRuntime(),
		params:  &TwemproxyInstallParams{IP: "1.1.1.2"},
	}
	// setShellPrompt 内部吞掉错误只打 Warn, 能执行到下一行即说明未阻断调用方
	twemproxyJob.setShellPrompt()
}

func TestProxyOperateRemoveShellPromptDegradesWhenUnremovable(t *testing.T) {
	oldPath := consts.RedisShellPromptFilePath
	// 用同名非空目录模拟删除失败
	dir := filepath.Join(t.TempDir(), consts.RedisShellPromptFileName)
	if err := os.MkdirAll(filepath.Join(dir, "sub"), 0755); err != nil {
		t.Fatalf("prepare unremovable dir failed:%v", err)
	}
	consts.RedisShellPromptFilePath = dir
	t.Cleanup(func() { consts.RedisShellPromptFilePath = oldPath })

	// removeShellPrompt 内部吞掉错误只打 Warn, 能执行到下一行即说明未阻断调用方
	job := &PredixyOperate{runtime: newProxyTestRuntime(), params: &PredixyOperateParams{IP: "1.1.1.1"}}
	job.removeShellPrompt()
	twemproxyJob := &TwemproxyOperate{runtime: newProxyTestRuntime(), params: &TwemproxyOperateParams{IP: "1.1.1.2"}}
	twemproxyJob.removeShellPrompt()
}
