package atomredis

import (
	"fmt"
	"net"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// 本文件是"重启实例前后钉死复制状态"的通用件, 不绑定具体原子任务:
// 任何会重建配置文件再重启实例的原子任务都该在停机前 captureReplSnapshot,
// 拉起后 waitRestored, 否则一份改错的配置只要还能同步上就会被当成成功.

// defaultSyncWaitTimeout 未指定 sync_wait_timeout_seconds 时的等待上限
const defaultSyncWaitTimeout = 30 * time.Minute

// syncWaitTimeoutOrDefault 把 sync_wait_timeout_seconds 参数换成等待时长, 0 表示用默认值
func syncWaitTimeoutOrDefault(seconds int) time.Duration {
	if seconds > 0 {
		return time.Duration(seconds) * time.Second
	}
	return defaultSyncWaitTimeout
}

// replSnapshot 实例重启前后应该满足的复制状态.
//
// 两个来源:
//   - 停机前的运行态 INFO (captureReplSnapshot): 期望是"角色和主库都不许变"
//   - 上游 sync_masters 指定的新主库 (expectSyncMaster): 期望是"重启后跟随这台新主库"
//
// 默认只信运行态 INFO, 不信配置文件: 配置文件可能是陈旧的(config rewrite 静默失败过),
// 而"从库跟到了另一台同密码、还活着的主"这种错误在文件层面完全看不出来 ——
// 新旧文件比对一致、拉起后链路也 UP, 任务成功, 下一步切主就把错数据推上去了.
type replSnapshot struct {
	addr       string
	role       string // master / slave, 空表示没抓到快照
	masterHost string
	masterPort string
	// wanted 为 true 时, 上面几项不是停机前抓到的运行态, 而是上游指定的目标拓扑.
	// old_master 升级后要作为 new_slave 跟随 new_master, 此时"和停机前一样"恰恰是错的.
	// 只影响报错文案, 让现场一眼看出是哪一种期望没被满足.
	wanted bool
}

// expectSyncMaster 构造"重启后应跟随 masterHost:masterPort" 这一期望
func expectSyncMaster(addr, masterHost, masterPort string) replSnapshot {
	return replSnapshot{
		addr:       addr,
		role:       consts.RedisSlaveRole,
		masterHost: masterHost,
		masterPort: masterPort,
		wanted:     true,
	}
}

// resolveReplExpectation 在"上游指定的新拓扑"与"停机前的运行态"之间选出本次的期望.
//
// 指定了新主库(masterHost 非空)时以它为准: old_master 重启后要作为 new_slave 跟随
// new_master, 此时"和停机前一样"恰恰是错的, 拿停机前快照去校验会把正确结果判成失败.
// 没指定时退回停机前快照, 也就是"角色和主库都不许变".
func resolveReplExpectation(addr, masterHost, masterPort string, snapshot replSnapshot) replSnapshot {
	if masterHost == "" {
		return snapshot
	}
	return expectSyncMaster(addr, masterHost, masterPort)
}

// originPhrase 报错文案里说明这份期望的来源, noun 形如 "role" / "master"
func (s replSnapshot) originPhrase(noun string) string {
	if s.wanted {
		return noun + " expected after upgrade"
	}
	return noun + " before restart"
}

// captureReplSnapshot 读 INFO replication 记下当前复制状态
func captureReplSnapshot(cli *myredis.RedisClient) (replSnapshot, error) {
	repls, err := cli.Info("replication")
	if err != nil {
		return replSnapshot{}, fmt.Errorf("addr=%s info replication failed,err:%v", cli.Addr, err)
	}
	return newReplSnapshot(cli.Addr, repls), nil
}

// newReplSnapshot 从 INFO replication 的结果构造快照
func newReplSnapshot(addr string, repls map[string]string) replSnapshot {
	snap := replSnapshot{addr: addr, role: repls["role"]}
	if snap.isSlave() {
		snap.masterHost = repls["master_host"]
		snap.masterPort = repls["master_port"]
	}
	return snap
}

// captured 是否抓到过快照. 实例已经被上游关掉(如切换 act 已 SHUTDOWN 旧 master)时抓不到
func (s replSnapshot) captured() bool {
	return s.role != ""
}

func (s replSnapshot) isSlave() bool {
	return s.role == consts.RedisSlaveRole
}

// masterAddr role=slave 时的 master 地址, 形如 1.1.1.2:30000
func (s replSnapshot) masterAddr() string {
	if !s.isSlave() {
		return ""
	}
	return net.JoinHostPort(s.masterHost, s.masterPort)
}

// confReplTarget 期望在配置文件 replicaof/slaveof 后面看到的取值, 形如 "1.1.1.2 30000"
func (s replSnapshot) confReplTarget() string {
	if !s.isSlave() {
		return ""
	}
	return s.masterHost + " " + s.masterPort
}

// checkConfMatchesExpectation 校验配置文件写的主从关系与期望一致.
//
// 这是最该拦住的一类事故: 文件里的 replicaof 指向另一台同密码、还活着的主时,
// 新旧文件比对看不出异常, 拉起后链路也 UP, 但实例已经跟错主.
// 停机前调用, 不一致就终止, 此时实例还都在跑, 现场是干净的.
//
// cluster 类型直接放过: cluster_enabled 时 redis 的 config rewrite 不写 replicaof,
// 主从关系由 cluster 元数据维护, 配置文件里本来就没有可比的东西.
func (s replSnapshot) checkConfMatchesExpectation(confData, clusterType string) error {
	if !s.captured() || consts.IsClusterDbType(clusterType) {
		return nil
	}
	_, confTarget := effectiveReplicationOf(confData)
	want := s.confReplTarget()
	if sameReplTarget(confTarget, want) {
		return nil
	}
	if s.wanted {
		// 期望来自上游指定的新主库, 而这份配置是本任务自己渲染的: 不一致说明渲染逻辑有问题
		return fmt.Errorf("addr=%s must replicate from %s after upgrade, but conf file declares %q",
			s.addr, s.masterAddr(), confTarget)
	}
	if want == "" {
		return fmt.Errorf("addr=%s is master at runtime, but conf file declares replication of %q, "+
			"restart would turn a master into a replica", s.addr, confTarget)
	}
	if confTarget == "" {
		return fmt.Errorf("addr=%s replicates from %s at runtime, but conf file declares no replication, "+
			"restart would turn a replica into a master", s.addr, want)
	}
	return fmt.Errorf("addr=%s replicates from %s at runtime, but conf file declares %q, "+
		"restart would attach the instance to a wrong master", s.addr, want, confTarget)
}

// sameReplTarget 比较两个 "ip port" 取值, 容忍多余空白
func sameReplTarget(a, b string) bool {
	return strings.Join(strings.Fields(a), " ") == strings.Join(strings.Fields(b), " ")
}

// infoReplicationAttempts 每一轮 INFO 失败时当场连试次数
const infoReplicationAttempts = 3

func infoReplicationRetry(get func() (map[string]string, error), attempts int, pause time.Duration) (
	map[string]string, error,
) {
	var last map[string]string
	var lastErr error
	for i := 0; i < attempts; i++ {
		last, lastErr = get()
		if lastErr == nil {
			return last, nil
		}
		if i+1 < attempts && pause > 0 {
			time.Sleep(pause)
		}
	}
	return last, lastErr
}

// waitRestored 拉起后钉死复制状态: 角色和主库必须是期望的那个 —— 默认是停机前那个,
// 上游指定了新主库时则是那台新主库.
//
// 角色或主库不对时立刻失败, 不等待: 这两项由配置文件(或 cluster 元数据)决定, 不会自己变回去,
// 等下去只是把一次必然失败的升级拖满 timeout.
// 只有 master_link_status 值得轮询 —— 全量同步期间它本来就是 down.
func (s replSnapshot) waitRestored(cli *myredis.RedisClient, timeout time.Duration, log *logger.Logger) error {
	if !s.captured() {
		return fmt.Errorf("addr=%s no repl snapshot captured before restart", cli.Addr)
	}
	deadline := time.Now().Add(timeout)
	const interval = 2 * time.Second
	linkStatus := "unknown"
	for {
		repls, err := infoReplicationRetry(func() (map[string]string, error) {
			return cli.Info("replication")
		}, infoReplicationAttempts, time.Second)
		if err != nil {
			return fmt.Errorf("addr=%s info replication failed,master_link_status:%s,err:%v",
				cli.Addr, linkStatus, err)
		}
		if role := repls["role"]; role != s.role {
			return fmt.Errorf("addr=%s role=%s after restart, want %s(%s)",
				cli.Addr, role, s.role, s.originPhrase("role"))
		}
		if !s.isSlave() {
			log.Info("redis instance(%s) still master after restart", cli.Addr)
			return nil
		}
		if got := newReplSnapshot(cli.Addr, repls); got.masterAddr() != s.masterAddr() {
			return fmt.Errorf("addr=%s replicates from %s after restart, want %s(%s)",
				cli.Addr, got.masterAddr(), s.masterAddr(), s.originPhrase("master"))
		}
		linkStatus = repls["master_link_status"]
		if linkStatus == "" {
			linkStatus = "unknown"
		}
		if linkStatus == consts.MasterLinkStatusUP {
			log.Info("redis instance(%s) is slave of %s after restart,master_link_status:%s",
				cli.Addr, s.masterAddr(), linkStatus)
			return nil
		}
		if time.Now().After(deadline) {
			break
		}
		log.Info("redis instance(%s) master(%s) master_link_status:%s,wait %s then retry",
			cli.Addr, s.masterAddr(), linkStatus, interval)
		time.Sleep(interval)
	}
	return fmt.Errorf("cost %d seconds, addr=%s master(%s) master_link_status:%s is not %s",
		int(timeout.Seconds()), cli.Addr, s.masterAddr(), linkStatus, consts.MasterLinkStatusUP)
}

// assertRoleMatchesMetaRole 没抓到停机前快照时的兜底: 至少断言实例角色和元数据角色一致.
//
// 用于实例已被上游关掉、拿不到运行态快照的场景(如切换 act 已 SHUTDOWN 旧 master).
// 拦的是"master 的配置被写成从库"这类事故 —— 它自己起不来倒好, 起来了才危险.
func assertRoleMatchesMetaRole(cli *myredis.RedisClient, metaRole string) error {
	wantRole := ""
	switch metaRole {
	case consts.MetaRoleRedisMaster:
		wantRole = consts.RedisMasterRole
	case consts.MetaRoleRedisSlave:
		wantRole = consts.RedisSlaveRole
	default:
		return fmt.Errorf("addr=%s unknown meta role(%s)", cli.Addr, metaRole)
	}
	repls, err := cli.Info("replication")
	if err != nil {
		return fmt.Errorf("addr=%s info replication failed,err:%v", cli.Addr, err)
	}
	if role := repls["role"]; role != wantRole {
		return fmt.Errorf("addr=%s role=%s after restart, want %s(meta role %s)",
			cli.Addr, role, wantRole, metaRole)
	}
	return nil
}

// settleReplication 实例拉起后钉死复制状态: 抓到停机前快照时按快照等恢复,
// 没抓到时(实例可能早被上游关掉)退化为断言角色与元数据一致.
func settleReplication(cli *myredis.RedisClient, expect replSnapshot, metaRole string,
	timeout time.Duration, log *logger.Logger) error {
	if !expect.captured() {
		log.Warn("redis(%s) no repl snapshot,assert meta role(%s) instead", cli.Addr, metaRole)
		if err := assertRoleMatchesMetaRole(cli, metaRole); err != nil {
			log.Error("%s", err)
			return err
		}
		return nil
	}
	if err := expect.waitRestored(cli, timeout, log); err != nil {
		log.Error("%s", err)
		return err
	}
	return nil
}
