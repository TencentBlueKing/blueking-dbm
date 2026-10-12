package atomredis

import (
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/redisconf"
)

// 本文件是"重启实例前后钉死复制状态"的通用件, 不绑定具体原子任务:
// 任何会重建配置文件再重启实例的原子任务都该在停机前 captureReplSnapshot,
// 拉起后 settleReplication, 否则一份改错的配置只要还能同步上就会被当成成功.

// defaultSyncWaitTimeout 未指定 sync_wait_timeout_seconds 时的等待上限
const defaultSyncWaitTimeout = 30 * time.Minute

// syncWaitTimeoutOrDefault 把 sync_wait_timeout_seconds 参数换成等待时长, 0 表示用默认值
func syncWaitTimeoutOrDefault(seconds int) time.Duration {
	if seconds > 0 {
		return time.Duration(seconds) * time.Second
	}
	return defaultSyncWaitTimeout
}

// replSnapshot 实例重启前后应该满足的复制状态, 见 redisconf.ReplState
type replSnapshot = redisconf.ReplState

// captureReplSnapshot 读 INFO replication 记下当前复制状态.
// cache cluster 顺带记下 node id, 拉起后据此确认节点身份没丢
func captureReplSnapshot(cli *myredis.RedisClient, clusterType string) (replSnapshot, error) {
	repls, err := cli.Info("replication")
	if err != nil {
		return replSnapshot{}, fmt.Errorf("addr=%s info replication failed,err:%v", cli.Addr, err)
	}
	snap := redisconf.NewReplState(cli.Addr, repls)
	if !consts.IsClusterDbType(clusterType) || !consts.IsRedisInstanceDbType(clusterType) {
		return snap, nil
	}
	if snap.NodeID, err = clusterMyID(cli); err != nil {
		return replSnapshot{}, err
	}
	return snap, nil
}

// clusterMyID 运行态的 cluster 节点 id
func clusterMyID(cli *myredis.RedisClient) (string, error) {
	myself, err := cli.GetMyself()
	if err != nil {
		return "", fmt.Errorf("addr=%s get cluster myself failed,err:%v", cli.Addr, err)
	}
	if myself == nil || myself.NodeID == "" {
		return "", fmt.Errorf("addr=%s cluster nodes has no myself", cli.Addr)
	}
	return myself.NodeID, nil
}

// assertNodeIDUnchanged 拉起后的节点身份必须是停机前那个.
//
// 节点文件没带过来时 redis 会生成新 id、以孤立的空 master 起来, 复制关系和 slot 都不再认它,
// 而角色检查只看得到"是个 master", 必须在那之前拦下.
func assertNodeIDUnchanged(cli *myredis.RedisClient, want string) error {
	got, err := clusterMyID(cli)
	if err != nil {
		return err
	}
	if got != want {
		return fmt.Errorf("addr=%s cluster node id is %s after restart, want %s before restart,"+
			"the instance lost its cluster identity", cli.Addr, got, want)
	}
	return nil
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
func waitRestored(s replSnapshot, cli *myredis.RedisClient, timeout time.Duration, log *logger.Logger) error {
	if !s.Captured() {
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
		if role := repls["role"]; role != s.Role {
			return fmt.Errorf("addr=%s role=%s after restart, want %s(%s)",
				cli.Addr, role, s.Role, s.OriginPhrase("role"))
		}
		if !s.IsSlave() {
			log.Info("redis instance(%s) still master after restart", cli.Addr)
			return nil
		}
		if got := redisconf.NewReplState(cli.Addr, repls); got.MasterAddr() != s.MasterAddr() {
			return fmt.Errorf("addr=%s replicates from %s after restart, want %s(%s)",
				cli.Addr, got.MasterAddr(), s.MasterAddr(), s.OriginPhrase("master"))
		}
		linkStatus = repls["master_link_status"]
		if linkStatus == "" {
			linkStatus = "unknown"
		}
		if linkStatus == consts.MasterLinkStatusUP {
			log.Info("redis instance(%s) is slave of %s after restart,master_link_status:%s",
				cli.Addr, s.MasterAddr(), linkStatus)
			return nil
		}
		if time.Now().After(deadline) {
			break
		}
		log.Info("redis instance(%s) master(%s) master_link_status:%s,wait %s then retry",
			cli.Addr, s.MasterAddr(), linkStatus, interval)
		time.Sleep(interval)
	}
	return fmt.Errorf("cost %d seconds, addr=%s master(%s) master_link_status:%s is not %s",
		int(timeout.Seconds()), cli.Addr, s.MasterAddr(), linkStatus, consts.MasterLinkStatusUP)
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

// settleReplication 实例拉起后钉死节点身份与复制状态: 抓到停机前快照时按快照等恢复,
// 没抓到时(实例可能早被上游关掉)退化为断言角色与元数据一致.
func settleReplication(cli *myredis.RedisClient, expect replSnapshot, metaRole string,
	timeout time.Duration, log *logger.Logger) error {
	if !expect.Captured() {
		log.Warn("redis(%s) no repl snapshot,assert meta role(%s) instead", cli.Addr, metaRole)
		if err := assertRoleMatchesMetaRole(cli, metaRole); err != nil {
			log.Error("%s", err)
			return err
		}
		return nil
	}
	if expect.NodeID != "" {
		if err := assertNodeIDUnchanged(cli, expect.NodeID); err != nil {
			log.Error("%s", err)
			return err
		}
	}
	if err := waitRestored(expect, cli, timeout, log); err != nil {
		log.Error("%s", err)
		return err
	}
	return nil
}
