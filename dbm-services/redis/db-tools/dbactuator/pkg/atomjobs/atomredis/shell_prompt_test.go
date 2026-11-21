package atomredis

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

// newAtomredisTestRuntime 构造测试用 runtime, 日志丢弃
func newAtomredisTestRuntime() *jobruntime.JobGenericRuntime {
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

// newBkDbmonTestJob 构造 bkdbmon 原子任务, isStopped 与 Run 中的判定保持一致
func newBkDbmonTestJob(t *testing.T, servers []ConfServerItem) *BkDbmonInstall {
	t.Helper()
	job := &BkDbmonInstall{
		runtime: newAtomredisTestRuntime(),
		params:  BkDbmonInstallParams{Servers: servers},
	}
	if err := job.checkIsStopped(); err != nil {
		t.Fatalf("checkIsStopped failed:%v", err)
	}
	return job
}

func TestBkDbmonInstallShellPrompt(t *testing.T) {
	tests := []struct {
		name    string
		servers []ConfServerItem
		want    string // 空表示提示符应被清理
	}{
		{
			name: "single master",
			servers: []ConfServerItem{
				{ServerIP: "1.1.1.1", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisMaster},
			},
			want: "master-1.1.1.1",
		},
		{
			name: "single slave",
			servers: []ConfServerItem{
				{ServerIP: "1.1.1.2", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisSlave},
			},
			want: "slave-1.1.1.2",
		},
		{
			name: "master and slave mixed",
			servers: []ConfServerItem{
				{ServerIP: "1.1.1.1", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisMaster},
				{ServerIP: "1.1.1.1", ServerPorts: []int{30001}, MetaRole: consts.MetaRoleRedisSlave},
			},
			want: "mixed-1.1.1.1",
		},
		{
			name: "predixy",
			servers: []ConfServerItem{
				{ServerIP: "1.1.1.1", ServerPorts: []int{50000}, MetaRole: consts.MetaRolePredixy},
			},
			want: "predixy-1.1.1.1",
		},
		{
			name: "twemproxy",
			servers: []ConfServerItem{
				{ServerIP: "1.1.1.2", ServerPorts: []int{50000}, MetaRole: consts.MetaRoleTwemproxy},
			},
			want: "twemproxy-1.1.1.2",
		},
		{
			name: "no active instance cleanup",
			servers: []ConfServerItem{
				{ServerIP: "1.1.1.1", ServerPorts: []int{}, MetaRole: consts.MetaRoleRedisMaster},
			},
			want: "",
		},
		{
			name:    "empty servers cleanup",
			servers: nil,
			want:    "",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			path := useTempShellPromptFile(t)
			// 预置旧提示符, 验证刷新/清理都能覆盖
			if err := consts.SetRedisShellPrompt("slave-1.1.1.1", true); err != nil {
				t.Fatalf("prepare old prompt failed:%v", err)
			}
			newBkDbmonTestJob(t, tt.servers).syncShellPrompt()
			if tt.want == "" {
				if _, err := os.Stat(path); !os.IsNotExist(err) {
					t.Fatalf("prompt file should be removed, stat err:%v", err)
				}
				return
			}
			content := readPromptFile(t, path)
			if !strings.Contains(content, "@"+tt.want+" ") {
				t.Fatalf("prompt label should be %s, content:%s", tt.want, content)
			}
		})
	}
}

func TestBkDbmonInstallShellPromptRoleTransition(t *testing.T) {
	path := useTempShellPromptFile(t)
	// 故障切换后角色从 slave 变成 master, 重装监控应把提示符纠正为 master
	slaveJob := newBkDbmonTestJob(t, []ConfServerItem{
		{ServerIP: "1.1.1.2", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisSlave},
	})
	slaveJob.syncShellPrompt()
	if content := readPromptFile(t, path); !strings.Contains(content, "@slave-1.1.1.2 ") {
		t.Fatalf("expect slave prompt, content:%s", content)
	}
	masterJob := newBkDbmonTestJob(t, []ConfServerItem{
		{ServerIP: "1.1.1.2", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisMaster},
	})
	masterJob.syncShellPrompt()
	if content := readPromptFile(t, path); !strings.Contains(content, "@master-1.1.1.2 ") {
		t.Fatalf("role transition should refresh prompt to master, content:%s", content)
	}
}

func TestBkDbmonInstallShellPromptSkipsMultipleIPs(t *testing.T) {
	path := useTempShellPromptFile(t)
	if err := consts.SetRedisShellPrompt("master-1.1.1.1", true); err != nil {
		t.Fatalf("prepare old prompt failed:%v", err)
	}
	// 多 IP 参数属于异常场景, 应保留原提示符不做修改
	job := newBkDbmonTestJob(t, []ConfServerItem{
		{ServerIP: "1.1.1.1", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisMaster},
		{ServerIP: "1.1.1.2", ServerPorts: []int{30000}, MetaRole: consts.MetaRoleRedisSlave},
	})
	job.syncShellPrompt()
	if content := readPromptFile(t, path); !strings.Contains(content, "@master-1.1.1.1 ") {
		t.Fatalf("multiple ip should keep old prompt, content:%s", content)
	}
}

func TestRedisInstallShellPromptEngineFallback(t *testing.T) {
	tests := []struct {
		dbType string
		ip     string
		want   string
	}{
		{dbType: consts.TendisTypeRedisInstance, ip: "1.1.1.1", want: "redis-1.1.1.1"},
		{dbType: consts.TendisTypeTendisSSDInsance, ip: "1.1.1.1", want: "tendisssd-1.1.1.1"},
		{dbType: consts.TendisTypeTendisplusInsance, ip: "1.1.1.2", want: "tendisplus-1.1.1.2"},
	}
	for _, tt := range tests {
		t.Run(tt.dbType, func(t *testing.T) {
			path := useTempShellPromptFile(t)
			job := &RedisInstall{
				runtime: newAtomredisTestRuntime(),
				params:  RedisInstallParams{IP: tt.ip, DbType: tt.dbType},
			}
			job.syncShellPrompt()
			content := readPromptFile(t, path)
			if !strings.Contains(content, "@"+tt.want+" ") {
				t.Fatalf("expect engine fallback label %s, content:%s", tt.want, content)
			}
		})
	}
}

func TestRedisInstallShellPromptKeepsExistingRolePrompt(t *testing.T) {
	path := useTempShellPromptFile(t)
	if err := consts.SetRedisShellPrompt("master-1.1.1.1", true); err != nil {
		t.Fatalf("prepare role prompt failed:%v", err)
	}
	// 追加部署时 redis_install 不含角色信息, 不得把已有角色提示符降级为引擎名
	job := &RedisInstall{
		runtime: newAtomredisTestRuntime(),
		params:  RedisInstallParams{IP: "1.1.1.1", DbType: consts.TendisTypeRedisInstance},
	}
	job.syncShellPrompt()
	if content := readPromptFile(t, path); !strings.Contains(content, "@master-1.1.1.1 ") {
		t.Fatalf("existing role prompt should be kept, content:%s", content)
	}
}

func TestRedisInstallShellPromptUnsupportedDbType(t *testing.T) {
	path := useTempShellPromptFile(t)
	job := &RedisInstall{
		runtime: newAtomredisTestRuntime(),
		params:  RedisInstallParams{IP: "1.1.1.1", DbType: "unknown_db_type"},
	}
	// 未知引擎类型只告警, 不写提示符, 也不阻断安装
	job.syncShellPrompt()
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("unsupported db_type should not create prompt, stat err:%v", err)
	}
}
