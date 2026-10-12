package redisconf

import (
	"fmt"
	"net"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// ReplState 实例重启前后应该满足的复制状态.
//
// 两个来源:
//   - 停机前的运行态 INFO (NewReplState): 期望是"角色和主库都不许变"
//   - 上游 sync_masters 指定的新主库 (ExpectSyncMaster): 期望是"重启后跟随这台新主库"
//
// 默认只信运行态 INFO, 不信配置文件: 配置文件可能是陈旧的(config rewrite 静默失败过),
// 而"从库跟到了另一台同密码、还活着的主"这种错误在文件层面完全看不出来 ——
// 新旧文件比对一致、拉起后链路也 UP, 任务成功, 下一步切主就把错数据推上去了.
type ReplState struct {
	Addr       string
	Role       string // master / slave, 空表示没抓到快照
	MasterHost string
	MasterPort string
	// Wanted 为 true 时, 上面几项不是停机前抓到的运行态, 而是上游指定的目标拓扑.
	// old_master 升级后要作为 new_slave 跟随 new_master, 此时"和停机前一样"恰恰是错的.
	// 只影响报错文案, 让现场一眼看出是哪一种期望没被满足.
	Wanted bool
	// NodeID 停机前运行态的 cluster 节点 id, 只有 cache cluster 才有.
	// 拓扑可以按上游意图改, 节点身份不行: 换了 id 就是另一个节点, 原来的主从关系和 slot 都不再认它
	NodeID string
}

// NewReplState 从 INFO replication 的结果构造快照
func NewReplState(addr string, repls map[string]string) ReplState {
	snap := ReplState{Addr: addr, Role: repls["role"]}
	if snap.IsSlave() {
		snap.MasterHost = repls["master_host"]
		snap.MasterPort = repls["master_port"]
	}
	return snap
}

// ExpectSyncMaster 构造"重启后应跟随 masterHost:masterPort" 这一期望
func ExpectSyncMaster(addr, masterHost, masterPort string) ReplState {
	return ReplState{
		Addr:       addr,
		Role:       consts.RedisSlaveRole,
		MasterHost: masterHost,
		MasterPort: masterPort,
		Wanted:     true,
	}
}

// ResolveReplExpectation 在"上游指定的新拓扑"与"停机前的运行态"之间选出本次的期望.
//
// 指定了新主库(masterHost 非空)时以它为准: old_master 重启后要作为 new_slave 跟随
// new_master, 此时"和停机前一样"恰恰是错的, 拿停机前快照去校验会把正确结果判成失败.
// 没指定时退回停机前快照, 也就是"角色和主库都不许变". 节点身份两种情况都沿用快照.
func ResolveReplExpectation(addr, masterHost, masterPort string, snapshot ReplState) ReplState {
	if masterHost == "" {
		return snapshot
	}
	expect := ExpectSyncMaster(addr, masterHost, masterPort)
	expect.NodeID = snapshot.NodeID
	return expect
}

// OriginPhrase 报错文案里说明这份期望的来源, noun 形如 "role" / "master"
func (s ReplState) OriginPhrase(noun string) string {
	if s.Wanted {
		return noun + " expected after upgrade"
	}
	return noun + " before restart"
}

// Captured 是否抓到过快照. 实例已经被上游关掉(如切换 act 已 SHUTDOWN 旧 master)时抓不到
func (s ReplState) Captured() bool {
	return s.Role != ""
}

// IsSlave 期望的角色是否为从库
func (s ReplState) IsSlave() bool {
	return s.Role == consts.RedisSlaveRole
}

// MasterAddr role=slave 时的 master 地址, 形如 1.1.1.2:30000
func (s ReplState) MasterAddr() string {
	if !s.IsSlave() {
		return ""
	}
	return net.JoinHostPort(s.MasterHost, s.MasterPort)
}

// ConfReplTarget 期望在配置文件 replicaof/slaveof 后面看到的取值, 形如 "1.1.1.2 30000"
func (s ReplState) ConfReplTarget() string {
	if !s.IsSlave() {
		return ""
	}
	return s.MasterHost + " " + s.MasterPort
}

// CheckConfMatchesExpectation 校验配置文件写的主从关系与期望一致.
//
// 这是最该拦住的一类事故: 文件里的 replicaof 指向另一台同密码、还活着的主时,
// 新旧文件比对看不出异常, 拉起后链路也 UP, 但实例已经跟错主.
// 停机前调用, 不一致就终止, 此时实例还都在跑, 现场是干净的.
//
// cluster 类型直接放过: cluster_enabled 时 redis 的 config rewrite 不写 replicaof,
// 主从关系由 cluster 元数据维护, 配置文件里本来就没有可比的东西.
func (s ReplState) CheckConfMatchesExpectation(confData, clusterType string) error {
	if !s.Captured() || consts.IsClusterDbType(clusterType) {
		return nil
	}
	_, confTarget := EffectiveReplicationOf(confData)
	want := s.ConfReplTarget()
	if sameReplTarget(confTarget, want) {
		return nil
	}
	if s.Wanted {
		// 期望来自上游指定的新主库, 而这份配置是本任务自己渲染的: 不一致说明渲染逻辑有问题
		return fmt.Errorf("addr=%s must replicate from %s after upgrade, but conf file declares %q",
			s.Addr, s.MasterAddr(), confTarget)
	}
	if want == "" {
		return fmt.Errorf("addr=%s is master at runtime, but conf file declares replication of %q, "+
			"restart would turn a master into a replica", s.Addr, confTarget)
	}
	if confTarget == "" {
		return fmt.Errorf("addr=%s replicates from %s at runtime, but conf file declares no replication, "+
			"restart would turn a replica into a master", s.Addr, want)
	}
	return fmt.Errorf("addr=%s replicates from %s at runtime, but conf file declares %q, "+
		"restart would attach the instance to a wrong master", s.Addr, want, confTarget)
}

// sameReplTarget 比较两个 "ip port" 取值, 容忍多余空白
func sameReplTarget(a, b string) bool {
	return strings.Join(strings.Fields(a), " ") == strings.Join(strings.Fields(b), " ")
}
