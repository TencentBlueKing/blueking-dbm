package consts

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// useTempShellPromptFile 将提示符脚本路径注入临时目录, 测试结束后还原
func useTempShellPromptFile(t *testing.T) string {
	t.Helper()
	oldPath := RedisShellPromptFilePath
	path := filepath.Join(t.TempDir(), "profile.d", RedisShellPromptFileName)
	RedisShellPromptFilePath = path
	t.Cleanup(func() { RedisShellPromptFilePath = oldPath })
	return path
}

func TestProxyShellPromptLabel(t *testing.T) {
	tests := []struct {
		proxyRole string
		ip        string
		want      string
		wantErr   bool
	}{
		{proxyRole: MetaRolePredixy, ip: "1.1.1.1", want: "predixy-1.1.1.1"},
		{proxyRole: MetaRoleTwemproxy, ip: "1.1.1.2", want: "twemproxy-1.1.1.2"},
		{proxyRole: MetaRolePredixy, ip: "", wantErr: true},
		{proxyRole: "unknown", ip: "1.1.1.1", wantErr: true},
		{proxyRole: MetaRolePredixy, ip: "1.1.1.1;rm -rf /", wantErr: true},
	}
	for _, tt := range tests {
		got, err := ProxyShellPromptLabel(tt.proxyRole, tt.ip)
		if tt.wantErr {
			if err == nil {
				t.Fatalf("ProxyShellPromptLabel(%q,%q) expect error, got %q", tt.proxyRole, tt.ip, got)
			}
			continue
		}
		if err != nil {
			t.Fatalf("ProxyShellPromptLabel(%q,%q) unexpected error:%v", tt.proxyRole, tt.ip, err)
		}
		if got != tt.want {
			t.Fatalf("ProxyShellPromptLabel(%q,%q)=%q, want %q", tt.proxyRole, tt.ip, got, tt.want)
		}
	}
}

func TestStorageRoleShellPromptLabel(t *testing.T) {
	tests := []struct {
		name      string
		metaRoles []string
		ip        string
		want      string
		wantErr   bool
	}{
		{name: "single master", metaRoles: []string{MetaRoleRedisMaster}, ip: "1.1.1.1", want: "master-1.1.1.1"},
		{name: "single slave", metaRoles: []string{MetaRoleRedisSlave}, ip: "1.1.1.2", want: "slave-1.1.1.2"},
		{
			name:      "master and slave mixed",
			metaRoles: []string{MetaRoleRedisMaster, MetaRoleRedisSlave},
			ip:        "1.1.1.1",
			want:      "mixed-1.1.1.1",
		},
		{name: "duplicated master", metaRoles: []string{MetaRoleRedisMaster, MetaRoleRedisMaster}, ip: "1.1.1.1", want: "master-1.1.1.1"},
		{name: "predixy", metaRoles: []string{MetaRolePredixy}, ip: "1.1.1.1", want: "predixy-1.1.1.1"},
		{name: "twemproxy", metaRoles: []string{MetaRoleTwemproxy}, ip: "1.1.1.2", want: "twemproxy-1.1.1.2"},
		{name: "empty roles", metaRoles: nil, ip: "1.1.1.1", wantErr: true},
		{name: "blank roles", metaRoles: []string{"", "  "}, ip: "1.1.1.1", wantErr: true},
		{name: "unknown role", metaRoles: []string{"unknown"}, ip: "1.1.1.1", wantErr: true},
		{name: "proxy and storage mixed", metaRoles: []string{MetaRolePredixy, MetaRoleRedisMaster}, ip: "1.1.1.1", wantErr: true},
		{name: "metachar in ip", metaRoles: []string{MetaRoleRedisMaster}, ip: "1.1.1.1'$(id)", wantErr: true},
	}
	for _, tt := range tests {
		got, err := StorageRoleShellPromptLabel(tt.metaRoles, tt.ip)
		if tt.wantErr {
			if err == nil {
				t.Fatalf("%s: expect error, got %q", tt.name, got)
			}
			continue
		}
		if err != nil {
			t.Fatalf("%s: unexpected error:%v", tt.name, err)
		}
		if got != tt.want {
			t.Fatalf("%s: got %q, want %q", tt.name, got, tt.want)
		}
	}
}

func TestStorageEngineShellPromptLabel(t *testing.T) {
	tests := []struct {
		dbType  string
		ip      string
		want    string
		wantErr bool
	}{
		{dbType: TendisTypePredixyRedisCluster, ip: "1.1.1.1", want: "redis-1.1.1.1"},
		{dbType: TendisTypeTwemproxyRedisInstance, ip: "1.1.1.1", want: "redis-1.1.1.1"},
		{dbType: TendisTypeRedisInstance, ip: "1.1.1.1", want: "redis-1.1.1.1"},
		{dbType: TendisTypeRedisCluster, ip: "1.1.1.1", want: "redis-1.1.1.1"},
		{dbType: TendisTypeTendisSSDInsance, ip: "1.1.1.1", want: "tendisssd-1.1.1.1"},
		{dbType: TendisTypeTwemproxyTendisSSDInstance, ip: "1.1.1.1", want: "tendisssd-1.1.1.1"},
		{dbType: TendisTypeTendisplusInsance, ip: "1.1.1.2", want: "tendisplus-1.1.1.2"},
		{dbType: TendisTypePredixyTendisplusCluster, ip: "1.1.1.2", want: "tendisplus-1.1.1.2"},
		{dbType: "unknown_db_type", ip: "1.1.1.1", wantErr: true},
		{dbType: TendisTypeRedisInstance, ip: "", wantErr: true},
	}
	for _, tt := range tests {
		got, err := StorageEngineShellPromptLabel(tt.dbType, tt.ip)
		if tt.wantErr {
			if err == nil {
				t.Fatalf("StorageEngineShellPromptLabel(%q,%q) expect error, got %q", tt.dbType, tt.ip, got)
			}
			continue
		}
		if err != nil {
			t.Fatalf("StorageEngineShellPromptLabel(%q,%q) unexpected error:%v", tt.dbType, tt.ip, err)
		}
		if got != tt.want {
			t.Fatalf("StorageEngineShellPromptLabel(%q,%q)=%q, want %q", tt.dbType, tt.ip, got, tt.want)
		}
	}
}

func TestSetRedisShellPromptRejectsInvalidLabel(t *testing.T) {
	path := useTempShellPromptFile(t)
	invalidLabels := []string{
		"",
		"predixy-1.1.1.1'",
		"master-1.1.1.1; id",
		"master-1.1.1.1\"",
		"master-1.1.1.1 $(id)",
		"master-1.1.1.1\nrm -rf /",
		"master-1.1.1.1|x",
	}
	for _, label := range invalidLabels {
		if err := SetRedisShellPrompt(label, true); err == nil {
			t.Fatalf("SetRedisShellPrompt(%q) expect error", label)
		}
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("invalid label should not create %s, stat err:%v", path, err)
	}
}

func TestSetRedisShellPromptContent(t *testing.T) {
	path := useTempShellPromptFile(t)
	if err := SetRedisShellPrompt("predixy-1.1.1.1", true); err != nil {
		t.Fatalf("SetRedisShellPrompt failed:%v", err)
	}
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s failed:%v", path, err)
	}
	want := "# Managed by DBM Redis dbactuator. Do not edit manually.\n" +
		"case \"$-\" in\n" +
		"    *i*) PS1='[\\t \\u@predixy-1.1.1.1 \\W]\\$ ' ;;\n" +
		"esac\n"
	if string(content) != want {
		t.Fatalf("unexpected content:\n%s\nwant:\n%s", content, want)
	}
	if strings.Contains(string(content), "export") {
		t.Fatalf("prompt script must not export PS1:\n%s", content)
	}
	if got := readRedisShellPromptLabel(path); got != "predixy-1.1.1.1" {
		t.Fatalf("readRedisShellPromptLabel=%q, want predixy-1.1.1.1", got)
	}
	stat, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat %s failed:%v", path, err)
	}
	if perm := stat.Mode().Perm(); perm != 0644 {
		t.Fatalf("prompt file perm=%o, want 0644", perm)
	}
}

func TestSetRedisShellPromptAntiDowngrade(t *testing.T) {
	path := useTempShellPromptFile(t)
	if err := SetRedisShellPrompt("master-1.1.1.1", true); err != nil {
		t.Fatalf("write role prompt failed:%v", err)
	}
	// 同 IP 的引擎兜底提示符不得覆盖已有角色提示符
	if err := SetRedisShellPrompt("redis-1.1.1.1", false); err != nil {
		t.Fatalf("SetRedisShellPrompt(force=false) failed:%v", err)
	}
	if got := readRedisShellPromptLabel(path); got != "master-1.1.1.1" {
		t.Fatalf("role prompt should not downgrade, got %q", got)
	}
	// slave/mixed 同样受保护
	if err := SetRedisShellPrompt("slave-1.1.1.1", true); err != nil {
		t.Fatalf("write slave prompt failed:%v", err)
	}
	if err := SetRedisShellPrompt("tendisssd-1.1.1.1", false); err != nil {
		t.Fatalf("SetRedisShellPrompt(force=false) failed:%v", err)
	}
	if got := readRedisShellPromptLabel(path); got != "slave-1.1.1.1" {
		t.Fatalf("slave prompt should not downgrade, got %q", got)
	}
	// 不同 IP 的引擎兜底提示符可以正常覆盖
	if err := SetRedisShellPrompt("redis-1.1.1.2", false); err != nil {
		t.Fatalf("SetRedisShellPrompt(force=false) failed:%v", err)
	}
	if got := readRedisShellPromptLabel(path); got != "redis-1.1.1.2" {
		t.Fatalf("different ip should be overwritten, got %q", got)
	}
	// force=true 时角色提示符会被强制刷新
	if err := SetRedisShellPrompt("mixed-1.1.1.2", true); err != nil {
		t.Fatalf("SetRedisShellPrompt(force=true) failed:%v", err)
	}
	if got := readRedisShellPromptLabel(path); got != "mixed-1.1.1.2" {
		t.Fatalf("force=true should overwrite, got %q", got)
	}
}

func TestRemoveRedisShellPromptIdempotent(t *testing.T) {
	path := useTempShellPromptFile(t)
	// 文件不存在时删除视为成功
	if err := RemoveRedisShellPrompt(); err != nil {
		t.Fatalf("remove non-exist prompt failed:%v", err)
	}
	if err := SetRedisShellPrompt("twemproxy-1.1.1.2", true); err != nil {
		t.Fatalf("SetRedisShellPrompt failed:%v", err)
	}
	if err := RemoveRedisShellPrompt(); err != nil {
		t.Fatalf("remove prompt failed:%v", err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("prompt file should be removed, stat err:%v", err)
	}
	// 再次删除仍然成功
	if err := RemoveRedisShellPrompt(); err != nil {
		t.Fatalf("remove prompt twice failed:%v", err)
	}
}

func TestSetRedisShellPromptDegradesWhenUnwritable(t *testing.T) {
	oldPath := RedisShellPromptFilePath
	// 父级是普通文件, mkdir 必然失败
	parent := filepath.Join(t.TempDir(), "not-a-dir")
	if err := os.WriteFile(parent, []byte("x"), 0644); err != nil {
		t.Fatalf("prepare unwritable parent failed:%v", err)
	}
	RedisShellPromptFilePath = filepath.Join(parent, RedisShellPromptFileName)
	t.Cleanup(func() { RedisShellPromptFilePath = oldPath })

	if err := SetRedisShellPrompt("master-1.1.1.1", true); err == nil {
		t.Fatalf("SetRedisShellPrompt should return error when path is unwritable")
	}
}

func TestRedisShellPromptBashLoading(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("bash loading check is not supported on windows")
	}
	bashPath, err := exec.LookPath("bash")
	if err != nil {
		t.Skipf("bash not found:%v", err)
	}
	path := useTempShellPromptFile(t)
	if err = SetRedisShellPrompt("predixy-1.1.1.1", true); err != nil {
		t.Fatalf("SetRedisShellPrompt failed:%v", err)
	}

	// 非交互式 source 脚本: 零 stdout/stderr, 且 PS1 保持不变
	nonInteractive := exec.Command(bashPath, "--norc", "-c",
		fmt.Sprintf("PS1=sentinel; source %q; printf 'PS1_IS:<%%s>' \"$PS1\"", path))
	out, err := nonInteractive.CombinedOutput()
	if err != nil {
		t.Fatalf("non-interactive bash failed:%v, output:%s", err, out)
	}
	if string(out) != "PS1_IS:<sentinel>" {
		t.Fatalf("non-interactive bash should keep PS1 unchanged and print nothing else, got:%q", out)
	}

	// 仅 source 脚本: 零输出
	onlySource := exec.Command(bashPath, "--norc", "-c", fmt.Sprintf("source %q", path))
	out, err = onlySource.CombinedOutput()
	if err != nil {
		t.Fatalf("non-interactive source failed:%v, output:%s", err, out)
	}
	if len(out) != 0 {
		t.Fatalf("sourcing prompt script should emit nothing, got:%q", out)
	}

	// 交互式 shell: PS1 被设置为带时间戳/用户/label/目录的模板
	interactive := exec.Command(bashPath, "--norc", "-i")
	interactive.Stdin = strings.NewReader(fmt.Sprintf(
		"source %q\nprintf 'PS1_IS:<%%s>\\n' \"$PS1\"\nexit\n", path))
	stdout, err := interactive.Output()
	if err != nil {
		t.Fatalf("interactive bash failed:%v, stdout:%s", err, stdout)
	}
	wantPS1 := "PS1_IS:<[\\t \\u@predixy-1.1.1.1 \\W]\\$ >"
	if !strings.Contains(string(stdout), wantPS1) {
		t.Fatalf("interactive bash PS1 not set as expected, want contains %q, got:%q", wantPS1, stdout)
	}
}
