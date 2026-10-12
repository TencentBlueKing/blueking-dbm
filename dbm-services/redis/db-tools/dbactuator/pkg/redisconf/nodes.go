package redisconf

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

const (
	clusterConfigFileDirective = "cluster-config-file"
	defaultNodesFile           = "nodes.conf"
)

// hasNodesFile 节点身份是否存放在 nodes 文件里. tendisplus cluster 的身份在 rocksdb 里, 不归这里管
func hasNodesFile(clusterType string) bool {
	return consts.IsClusterDbType(clusterType) && consts.IsRedisInstanceDbType(clusterType)
}

// nodesFilePath redis 按这份配置会读写的节点文件.
//
// redis 没有扫描逻辑: cluster-config-file 缺省为 nodes.conf, 相对路径按进程 cwd 解析,
// 而 dir 指令在加载配置时就 chdir 过去了, 所以等价于相对 dir.
func nodesFilePath(directives Directives) string {
	name := Unquote(directives.LastValue(clusterConfigFileDirective))
	if name == "" {
		name = defaultNodesFile
	}
	if filepath.IsAbs(name) {
		return filepath.Clean(name)
	}
	return filepath.Join(Unquote(directives.LastValue("dir")), name)
}

// readNodesFileMyself 读节点文件里 myself 那一行的 node id.
//
// 不用 myredis.DecodeClusterNodes: 它要求地址带 @cport, redis 3.x 写的节点文件没有.
func readNodesFileMyself(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	for _, line := range strings.Split(string(data), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 3 || fields[0] == "vars" {
			continue
		}
		for _, flag := range strings.Split(fields[2], ",") {
			if flag == "myself" {
				return fields[0], nil
			}
		}
	}
	return "", fmt.Errorf("%s has no myself line", path)
}

// planNodesFileMove 新旧配置指向的节点文件不同时, 规划把节点身份带过去.
//
// 节点文件就是节点身份: redis 起来找不到它会生成一个新 node id, 以孤立的空 master 加入,
// 原来的主从关系和 slot 都不再认它. 所以旧文件读不出 myself 时宁可不重建.
func planNodesFileMove(req Request, oldDirs, newDirs Directives) (*NodesFileMove, error) {
	if !hasNodesFile(req.ClusterType) {
		return nil, nil
	}
	from, to := nodesFilePath(oldDirs), nodesFilePath(newDirs)
	if SamePathValue(from, to) {
		return nil, nil
	}
	nodeID, err := readNodesFileMyself(from)
	if err != nil {
		return nil, fmt.Errorf("port(%d) old conf uses nodes file %s but its node id cannot be read,"+
			"regenerating would make the instance a new cluster node,err:%v", req.Port, from, err)
	}
	req.Logger.Info("port(%d) nodes file moves from %s to %s,node id %s", req.Port, from, to, nodeID)
	return &NodesFileMove{From: from, To: to, NodeID: nodeID}, nil
}

// CheckNodesFileIdentity 要迁移节点文件时, 确认那份文件就是运行中进程的身份. 停机之前跑.
//
// 文件里的 myself 与运行态不一致, 说明进程用的根本不是它(有人手工改过配置或文件),
// 照着它迁过去, 拉起后一样会变成另一个节点. runningNodeID 为空(实例没在跑)时只能信文件.
func CheckNodesFileIdentity(plan *Plan, runningNodeID string, log *logger.Logger) error {
	if plan == nil || plan.NodesMove == nil {
		return nil
	}
	move := plan.NodesMove
	if runningNodeID == "" {
		log.Warn("port(%d) no running node id to compare,trust nodes file %s (node id %s)",
			plan.Port, move.From, move.NodeID)
		return nil
	}
	if runningNodeID != move.NodeID {
		return fmt.Errorf("port(%d) running node id is %s but nodes file %s holds %s,refuse to migrate it",
			plan.Port, runningNodeID, move.From, move.NodeID)
	}
	return nil
}

// NodesFileMove 把节点文件复制到新配置会读的位置. 源文件先留在原处供 Undo 退回,
// 进程带着新位置的文件起好之后由 Finalize 删掉.
//
// 必须停机后做: redis 4/6 原地重写节点文件, 进程还在跑时复制出去的是一份随时会过期的快照,
// 其中的 epoch 落后于集群, 起来后会被当成旧消息.
type NodesFileMove struct {
	From   string
	To     string
	NodeID string

	copied bool
	orphan string
}

func (m *NodesFileMove) String() string {
	return fmt.Sprintf("move nodes file %s -> %s", m.From, m.To)
}

// NeedsStopped 见类型说明
func (m *NodesFileMove) NeedsStopped() bool { return true }

// Apply 复制节点文件. 目标位置已是一模一样的内容时什么都不做(重试场景); 否则挪开留证据:
// 别的 node id 多半是上一次没带上身份起来生成的孤立节点; 同一个 node id 但内容不同,
// 是更早以前留下的旧快照, epoch、slot 归属都过期了, 以停机那一刻的 From 为准.
func (m *NodesFileMove) Apply(log *logger.Logger) error {
	if util.FileExists(m.To) {
		existing, err := readNodesFileMyself(m.To)
		if err == nil && existing == m.NodeID {
			if same, _ := filesEqual(m.From, m.To); same {
				log.Info("nodes file %s already holds node id %s", m.To, m.NodeID)
				return nil
			}
		}
		orphan := m.To + ".orphan." + time.Now().Format(consts.FilenameTimeLayout) + ".bak"
		if err = os.Rename(m.To, orphan); err != nil {
			return fmt.Errorf("move aside %s to %s failed,err:%v", m.To, orphan, err)
		}
		m.orphan = orphan
		if existing == m.NodeID {
			log.Warn("nodes file %s holds node id %s but differs from %s,stale snapshot moved aside to %s",
				m.To, existing, m.From, orphan)
		} else {
			log.Warn("nodes file %s (node id %q) moved aside to %s,it is not this instance's identity",
				m.To, existing, orphan)
		}
	}
	if err := copyFileAtomic(m.From, m.To); err != nil {
		if m.orphan != "" {
			if restoreErr := os.Rename(m.orphan, m.To); restoreErr == nil {
				m.orphan = ""
			}
		}
		return err
	}
	m.copied = true
	log.Info("nodes file copied %s -> %s,node id %s", m.From, m.To, m.NodeID)
	return nil
}

// Undo 删掉复制出来的文件, 挪开的那份放回去
func (m *NodesFileMove) Undo(log *logger.Logger) error {
	if m.copied {
		if err := os.Remove(m.To); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("remove copied nodes file %s failed,err:%v", m.To, err)
		}
		m.copied = false
		log.Info("copied nodes file %s removed", m.To)
	}
	if m.orphan != "" {
		if err := os.Rename(m.orphan, m.To); err != nil {
			return fmt.Errorf("restore %s from %s failed,err:%v", m.To, m.orphan, err)
		}
		log.Info("nodes file %s restored from %s", m.To, m.orphan)
		m.orphan = ""
	}
	return nil
}

// Finalize 进程起好之后删掉源文件.
//
// 起来之后进程只读写新位置, 源文件是停机那一刻的快照, epoch 只会越来越落后; 留着它,
// 有人照着旧配置备份手工回滚时会带着过期的集群视图起来. 新位置的身份对不上时不删, 留作排查.
func (m *NodesFileMove) Finalize(log *logger.Logger) {
	current, err := readNodesFileMyself(m.To)
	if err != nil || current != m.NodeID {
		log.Warn("nodes file %s holds node id %q (err:%v),want %s,keep %s for investigation",
			m.To, current, err, m.NodeID, m.From)
		return
	}
	if err = os.Remove(m.From); err != nil && !os.IsNotExist(err) {
		log.Warn("remove legacy nodes file %s failed,err:%v", m.From, err)
		return
	}
	log.Info("legacy nodes file %s removed,node identity now lives in %s", m.From, m.To)
}

func filesEqual(a, b string) (bool, error) {
	dataA, err := os.ReadFile(a)
	if err != nil {
		return false, err
	}
	dataB, err := os.ReadFile(b)
	if err != nil {
		return false, err
	}
	return bytes.Equal(dataA, dataB), nil
}

// copyFileAtomic 先写临时文件再 rename, 权限沿用源文件, 属主改成 mysql
func copyFileAtomic(from, to string) error {
	info, err := os.Stat(from)
	if err != nil {
		return fmt.Errorf("stat %s failed,err:%v", from, err)
	}
	data, err := os.ReadFile(from)
	if err != nil {
		return fmt.Errorf("read %s failed,err:%v", from, err)
	}
	tmp := to + ".tmp"
	if err = os.WriteFile(tmp, data, info.Mode().Perm()); err != nil {
		return fmt.Errorf("write %s failed,err:%v", tmp, err)
	}
	if err = os.Chmod(tmp, info.Mode().Perm()); err != nil {
		_ = os.Remove(tmp)
		return fmt.Errorf("chmod %s failed,err:%v", tmp, err)
	}
	if err = os.Rename(tmp, to); err != nil {
		_ = os.Remove(tmp)
		return fmt.Errorf("rename %s to %s failed,err:%v", tmp, to, err)
	}
	return ChownMysql(to)
}
