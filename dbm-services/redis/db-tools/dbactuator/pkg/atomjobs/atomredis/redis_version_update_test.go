package atomredis

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// TestLocalInstCountIgnoresShutdownDirs blockcache 的分母只数活着的实例目录.
//
// 分母是本机实例数, 取值 = 总内存 * 0.43 / 实例数: 少数了每实例就算大, 整机可能 OOM;
// 多数了只是偏保守. 所以宁可多数, 但已经下线的实例不能算进来 —— shutdown 会把 <port>
// 改名成 shutdown_<port>_<时间戳>, "目录名必须是纯数字" 这条筛选正好把它们挡在外面.
func TestLocalInstCountIgnoresShutdownDirs(t *testing.T) {
	dataDir := t.TempDir()
	t.Setenv("REDIS_DATA_DIR", dataDir)
	redisDir := filepath.Join(dataDir, "redis")
	for _, name := range []string{
		"30000", "30001", "30002",
		"shutdown_30003_20240101120000", // RedisShutdown.BackupDir 留下的
		"shutdown_30004",                // 人工挪走的
		"dbmon",                         // 同级的其它目录
	} {
		if err := os.MkdirAll(filepath.Join(redisDir, name), 0755); err != nil {
			t.Fatal(err)
		}
	}
	// 名字是数字的普通文件也不算实例
	if err := os.WriteFile(filepath.Join(redisDir, "30005"), nil, 0644); err != nil {
		t.Fatal(err)
	}

	if got := countLocalRedisInstDirs(); got != 3 {
		t.Errorf("countLocalRedisInstDirs = %d, want 3 live instance dirs", got)
	}
	// 只升级其中一个端口时, 分母仍是本机实例数, 而不是 len(ports)
	if got := buildRegenJob("1.1.1.1", []int{30000}).localInstCount(); got != 3 {
		t.Errorf("localInstCount = %d, want 3 instead of len(ports)", got)
	}

	// 目录形态不常规、一个都数不出来时回落到端口数: 否则 instCount=0 会让 blockcache 按 1 个实例算
	t.Setenv("REDIS_DATA_DIR", t.TempDir())
	if got := buildRegenJob("1.1.1.1", []int{30000, 30001}).localInstCount(); got != 2 {
		t.Errorf("localInstCount = %d, want the port count as fallback", got)
	}
}

// TestSettleUnsettledPortsSkipsAlreadySettled 兜底循环只处理没进过重启循环的端口.
//
// 之前它对所有端口都跑一遍, 刚重启完的端口在 regenConfAndStartRedis 里已经钉过复制、
// 恢复过 failover 资格, 于是 "is slave of ... after restart" 和 "cluster-*-no-failover=no"
// 每个端口都在日志里出现两次.
func TestSettleUnsettledPortsSkipsAlreadySettled(t *testing.T) {
	// 没有真实实例: 一旦真去收尾, connectLocalRedis 会因为读不到该端口的配置文件而报错,
	// 错误里带着端口号, 正好用来判断它动了哪些端口
	t.Setenv("REDIS_DATA_DIR", t.TempDir())
	job := buildRegenJob("1.1.1.1", []int{30000, 30001})

	job.markSettled(30000)
	job.markSettled(30001)
	if err := job.settleUnsettledPorts(); err != nil {
		t.Errorf("every port already settled,expected no work,err:%v", err)
	}

	job.settledPorts = map[int]bool{30000: true}
	err := job.settleUnsettledPorts()
	if err == nil {
		t.Fatal("the unsettled port should still be settled")
	}
	if strings.Contains(err.Error(), "30000") {
		t.Errorf("already settled port was touched again,err:%v", err)
	}
	if !strings.Contains(err.Error(), "30001") {
		t.Errorf("err = %v, want it to be about port 30001", err)
	}
}

func TestPrecheckSyncMasters(t *testing.T) {
	deliveredConf := map[string]RedisConfRenderItem{
		"30000": {ConfConfigs: map[string]string{"port": "{{port}}"}},
	}
	cases := []struct {
		name        string
		clusterType string
		syncMasters map[string]string
		confConfigs map[string]RedisConfRenderItem
		flush       bool
		wantErr     string
	}{
		{
			name:        "conf delivered",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			syncMasters: map[string]string{"30000": "1.1.1.2:30000"},
			confConfigs: deliveredConf,
		},
		{
			// 非 cluster 架构靠重建配置里的 replicaof 建立主从关系: 没下发配置就没有落地手段,
			// 实例会作为一个孤立的 master 起来, 而上游已经不再有建同步的步骤了
			name:        "no conf delivered",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			syncMasters: map[string]string{"30000": "1.1.1.2:30000"},
			wantErr:     "no conf delivered",
		},
		{
			// cluster 架构的主从关系在 nodes.conf 里, sync_masters 只当拉起后的校验期望
			name:        "cluster type needs no conf",
			clusterType: consts.TendisTypePredixyRedisCluster,
			syncMasters: map[string]string{"30000": "1.1.1.2:30000"},
		},
		{
			name:        "malformed addr",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			syncMasters: map[string]string{"30000": "1.1.1.2"},
			confConfigs: deliveredConf,
			wantErr:     "not a valid addr",
		},
		{
			// 实例带着 replicaof 起来后是只读从库, flushall 既清不掉也没有要清的东西
			name:        "flush after upgrade conflicts",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			syncMasters: map[string]string{"30000": "1.1.1.2:30000"},
			confConfigs: deliveredConf,
			flush:       true,
			wantErr:     "mutually exclusive",
		},
		{
			name:        "no sync masters",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			flush:       true,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			job := buildRegenJob("1.1.1.1", []int{30000})
			job.params.ClusterType = tc.clusterType
			job.params.SyncMasters = tc.syncMasters
			job.params.PortConfConfigs = tc.confConfigs
			job.params.FlushAfterUpgrade = tc.flush

			err := job.precheckSyncMasters()
			if tc.wantErr == "" {
				if err != nil {
					t.Fatalf("unexpected err:%v", err)
				}
				return
			}
			if err == nil {
				t.Fatalf("expected error containing %q, got nil", tc.wantErr)
			}
			if !strings.Contains(err.Error(), tc.wantErr) {
				t.Errorf("err = %v, want it to contain %q", err, tc.wantErr)
			}
		})
	}
}

func TestSyncWaitTimeout(t *testing.T) {
	if got := syncWaitTimeoutOrDefault(0); got != defaultSyncWaitTimeout {
		t.Errorf("syncWaitTimeoutOrDefault(0) = %v, want the default %v", got, defaultSyncWaitTimeout)
	}
	// 空载起进程后要等主库把数据整份传回来, 大实例远超默认的 30 分钟
	if got := syncWaitTimeoutOrDefault(6 * 3600); got != 6*time.Hour {
		t.Errorf("syncWaitTimeoutOrDefault(6h) = %v, want 6h", got)
	}
}

func TestWrapSyncWaitErr(t *testing.T) {
	syncErr := fmt.Errorf("cost 10 seconds, addr=1.1.1.1:30000 master(1.1.1.2:30000) master_link_status:down is not up")
	got := wrapSyncWaitErr(syncErr)
	if got == nil {
		t.Fatal("wrapSyncWaitErr returned nil")
	}
	if !strings.Contains(got.Error(), "不要直接跳过") {
		t.Errorf("wrapped err = %v, want it to contain 不要直接跳过", got)
	}
	if !strings.Contains(got.Error(), "重试本节点") {
		t.Errorf("wrapped err = %v, want it to contain 重试本节点", got)
	}
	if wrapSyncWaitErr(got) != got {
		t.Error("wrapSyncWaitErr should be idempotent once the skip hint is present")
	}

	other := fmt.Errorf("redis instance(1.1.1.1:30000) is not master")
	if wrapSyncWaitErr(other) != other {
		t.Errorf("non-sync errors should pass through unchanged, got %v", wrapSyncWaitErr(other))
	}
	if wrapSyncWaitErr(nil) != nil {
		t.Error("nil should stay nil")
	}
}
