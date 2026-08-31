package atomredis

import (
	"fmt"
	"strings"
	"testing"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

func TestNewReplSnapshot(t *testing.T) {
	slave := newReplSnapshot("1.1.1.1:30000", map[string]string{
		"role":               consts.RedisSlaveRole,
		"master_host":        "1.1.1.2",
		"master_port":        "30000",
		"master_link_status": consts.MasterLinkStatusUP,
	})
	if !slave.captured() || !slave.isSlave() {
		t.Fatalf("slave snapshot = %+v", slave)
	}
	if got := slave.masterAddr(); got != "1.1.1.2:30000" {
		t.Errorf("masterAddr = %q, want 1.1.1.2:30000", got)
	}
	// 配置文件里是空格分隔的两段, 不是 host:port
	if got := slave.confReplTarget(); got != "1.1.1.2 30000" {
		t.Errorf("confReplTarget = %q, want \"1.1.1.2 30000\"", got)
	}

	master := newReplSnapshot("1.1.1.1:30000", map[string]string{"role": consts.RedisMasterRole})
	if !master.captured() || master.isSlave() {
		t.Fatalf("master snapshot = %+v", master)
	}
	if master.masterAddr() != "" || master.confReplTarget() != "" {
		t.Errorf("master snapshot should have no master, got %+v", master)
	}

	// 实例已被上游关掉时拿不到 INFO, 快照为空: 调用方据此退化, 不能当成 master
	var absent replSnapshot
	if absent.captured() {
		t.Error("zero value snapshot should not be treated as captured")
	}
}

func TestReplSnapshotCheckConfMatchesExpectation(t *testing.T) {
	slaveSnap := replSnapshot{
		addr: "1.1.1.1:30000", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30000",
	}
	masterSnap := replSnapshot{addr: "1.1.1.1:30000", role: consts.RedisMasterRole}

	cases := []struct {
		name        string
		snap        replSnapshot
		conf        string
		clusterType string
		wantErr     string
	}{
		{
			name: "conf matches runtime master",
			snap: slaveSnap,
			conf: "port 30000\nreplicaof 1.1.1.2 30000\n",
		},
		{
			name: "extra whitespace still matches",
			snap: slaveSnap,
			conf: "port 30000\nreplicaof 1.1.1.2  30000\n",
		},
		{
			// 最严重的一种: 指向另一台同密码、还活着的主, 文件层面完全看不出异常
			name:    "conf points at another live master",
			snap:    slaveSnap,
			conf:    "port 30000\nreplicaof 2.2.2.2 30000\n",
			wantErr: "wrong master",
		},
		{
			name:    "conf lost replication",
			snap:    slaveSnap,
			conf:    "port 30000\n",
			wantErr: "turn a replica into a master",
		},
		{
			// 按行序取最后一条: 前面那条正确的会被后面这条覆盖
			name:    "last replication line wins",
			snap:    slaveSnap,
			conf:    "port 30000\nreplicaof 1.1.1.2 30000\nslaveof 2.2.2.2 30000\n",
			wantErr: "wrong master",
		},
		{
			name:    "master conf declares replication",
			snap:    masterSnap,
			conf:    "port 30000\nreplicaof 1.1.1.2 30000\n",
			wantErr: "turn a master into a replica",
		},
		{
			name: "master conf without replication",
			snap: masterSnap,
			conf: "port 30000\n",
		},
		{
			// cluster_enabled 时 redis 的 config rewrite 不写 replicaof,
			// 这类实例的配置文件里本来就没有可比的东西
			name:        "cluster type skipped",
			snap:        slaveSnap,
			conf:        "port 30000\n",
			clusterType: consts.TendisTypePredixyTendisplusCluster,
		},
		{
			// 没抓到快照时无从比对, 交给调用方按元数据角色兜底
			name: "no snapshot",
			conf: "port 30000\nreplicaof 2.2.2.2 30000\n",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			clusterType := tc.clusterType
			if clusterType == "" {
				clusterType = consts.TendisTypeTwemproxyRedisInstance
			}
			err := tc.snap.checkConfMatchesExpectation(tc.conf, clusterType)
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

func TestReplExpectationPrefersSyncMaster(t *testing.T) {
	// old_master 升级后要跟随 new_master: 拿停机前的快照(它当时是主)去校验会把正确结果判成失败
	job := buildRegenJob("1.1.1.1", []int{30000})
	job.replSnapshots[30000] = replSnapshot{addr: "1.1.1.1:30000", role: consts.RedisMasterRole}
	job.params.SyncMasters = map[string]string{"30000": "1.1.1.2:30000"}

	expect := job.replExpectation(30000)
	if !expect.captured() || !expect.isSlave() {
		t.Fatalf("expectation = %+v, want a replica expectation", expect)
	}
	if got := expect.masterAddr(); got != "1.1.1.2:30000" {
		t.Errorf("masterAddr = %q, want 1.1.1.2:30000", got)
	}
	if got := expect.originPhrase("role"); got != "role expected after upgrade" {
		t.Errorf("originPhrase = %q", got)
	}

	// 没抓到快照也一样成立: 旧 master 多半已被切换 act 关掉了
	job.replSnapshots = map[int]replSnapshot{}
	if expect = job.replExpectation(30000); !expect.captured() {
		t.Errorf("expectation without snapshot = %+v, want a replica expectation", expect)
	}

	// 端口没在 sync_masters 里时退回停机前快照
	job.replSnapshots[30001] = replSnapshot{
		addr: "1.1.1.1:30001", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30001",
	}
	if expect = job.replExpectation(30001); expect.wanted {
		t.Errorf("port without sync master should keep the captured snapshot, got %+v", expect)
	}
}

func TestExpectSyncMasterCheckConf(t *testing.T) {
	expect := expectSyncMaster("1.1.1.1:30000", "1.1.1.2", "30000")

	if err := expect.checkConfMatchesExpectation(
		"port 30000\nreplicaof 1.1.1.2 30000\n", consts.TendisTypeTwemproxyRedisInstance); err != nil {
		t.Errorf("conf pointing at the new master rejected:%v", err)
	}
	// 最该拦住的: 渲染出来的 replicaof 指向了另一台同密码、还活着的主
	err := expect.checkConfMatchesExpectation(
		"port 30000\nreplicaof 3.3.3.3 30000\n", consts.TendisTypeTwemproxyRedisInstance)
	if err == nil || !strings.Contains(err.Error(), "must replicate from 1.1.1.2:30000 after upgrade") {
		t.Errorf("err = %v, want wrong-master error", err)
	}
	err = expect.checkConfMatchesExpectation("port 30000\n", consts.TendisTypeTwemproxyRedisInstance)
	if err == nil || !strings.Contains(err.Error(), "must replicate from") {
		t.Errorf("err = %v, want missing-replication error", err)
	}
	// cluster 架构的主从关系在 nodes.conf 里, 配置文件里没有可比的东西
	if err = expect.checkConfMatchesExpectation(
		"port 30000\n", consts.TendisTypePredixyRedisCluster); err != nil {
		t.Errorf("cluster type should be skipped:%v", err)
	}
}

func TestCheckConfReplExpectationWithoutSnapshot(t *testing.T) {
	// 旧 master 已被切换 act 关掉, 抓不到运行态: 至少要拦住"master 的配置被写成从库"
	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	job.params.Role = consts.MetaRoleRedisMaster

	err := job.checkConfReplExpectation(30000, "port 30000\nslaveof 1.1.1.2 30000\n")
	if err == nil || !strings.Contains(err.Error(), "turn a master into a replica") {
		t.Errorf("err = %v, want master-turned-replica error", err)
	}
	if err = job.checkConfReplExpectation(30000, "port 30000\n"); err != nil {
		t.Errorf("clean master conf rejected:%v", err)
	}

	// role=redis_slave 且没有快照时判断不了期望的主, 只能放过
	job.params.Role = consts.MetaRoleRedisSlave
	if err = job.checkConfReplExpectation(30000, "port 30000\nslaveof 1.1.1.2 30000\n"); err != nil {
		t.Errorf("slave without snapshot should be skipped:%v", err)
	}
}

func TestInfoReplicationRetry(t *testing.T) {
	n := 0
	got, err := infoReplicationRetry(func() (map[string]string, error) {
		n++
		if n < 3 {
			return nil, fmt.Errorf("timeout")
		}
		return map[string]string{"role": "slave"}, nil
	}, 3, 0)
	if err != nil {
		t.Fatalf("should succeed on third try:%v", err)
	}
	if got["role"] != "slave" || n != 3 {
		t.Errorf("calls=%d got=%v", n, got)
	}

	n = 0
	_, err = infoReplicationRetry(func() (map[string]string, error) {
		n++
		return nil, fmt.Errorf("timeout")
	}, 3, 0)
	if err == nil || n != 3 {
		t.Errorf("should fail after 3 attempts, calls=%d err=%v", n, err)
	}
}

func TestWrapSyncWaitErrOnInfoFailure(t *testing.T) {
	err := wrapSyncWaitErr(fmt.Errorf("addr=1.1.1.1:30000 info replication failed,master_link_status:unknown,err:timeout"))
	if err == nil || !strings.Contains(err.Error(), "不要直接跳过") {
		t.Errorf("err=%v, want skip hint", err)
	}
}
