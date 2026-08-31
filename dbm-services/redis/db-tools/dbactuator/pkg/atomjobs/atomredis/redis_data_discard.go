package atomredis

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// 空载起进程: 版本升级重启前把本地 RDB/AOF 挪走, 让新版本进程从空数据集起来, 数据由主库同步补回.
//
// 为什么可以不要本地那份数据: 实例重启后与主库做的是全量同步 —— AOF 里没有 replid/offset,
// dbmon 留下的 dump.rdb 又太旧, 复制积压缓冲区覆盖不到, 部分重同步谈不成.
// 既然数据无论如何都要从主库重传一遍, 启动时加载本地那份就是纯浪费: 大实例要多花几分钟,
// 加载完还会被全量同步整个丢掉.
//
// 为什么只对 cache 生效:
//   - TendisSSD 的从库只能靠"主库全备 + tendisssd_dr_restore"重建, 单发 slaveof 只接增量 binlog,
//     数据挪走就再也回不来
//   - Tendisplus 数据本就在磁盘上, 重启不需要加载进内存(本来就快), 挪走只换来一次昂贵的
//     rocksdb 全量同步; 且 TendisplusCluster 的 slot/epoch 就存在数据目录里, 挪走等于丢掉节点身份
//
// 挪走而不是删除: 新版本进程起不来时要能退回"带着原数据、用旧配置重启"的老行为.

// localDataFileEntry 一个可能存在的本地数据文件/目录: 配置项名 + 该配置项缺省值
type localDataFileEntry struct {
	confName   string
	defaultVal string
}

// localDataFileEntries 需要挪走的本地数据文件/目录.
//
// appenddirname 是 redis 7 才有的: AOF 从单文件变成了目录, 跨大版本升级时新旧配置用的
// 不是同一套名字, 所以两套都要覆盖.
var localDataFileEntries = []localDataFileEntry{
	{"dbfilename", "dump.rdb"},
	{"appendfilename", "appendonly.aof"},
	{"appenddirname", "appendonlydir"},
}

// discardedDataFile 一份被挪走的数据文件/目录
type discardedDataFile struct {
	origin string
	moved  string
}

// discardingLocalData 该端口本次是否空载起进程
func (job *RedisVersionUpdate) discardingLocalData(port int) bool {
	return job.discardPorts[port]
}

// planLocalDataDiscard 停机前决定哪些端口可以空载起进程.
//
// 必须在停实例之前算: 判断依赖运行态(实例真实类型、主库是否健康), 停了就问不到了.
// 不满足条件时退回"带着本地数据重启"的老行为而不是报错 —— 老行为只是慢, 不会错.
func (job *RedisVersionUpdate) planLocalDataDiscard() {
	if !job.params.DiscardLocalDataOnRestart {
		return
	}
	for _, port := range job.params.Ports {
		expect := job.replExpectation(port)
		if reason := job.whyKeepLocalData(port, expect); reason != "" {
			job.runtime.Logger.Warn("port(%d) keeps its local data on restart:%s", port, reason)
			continue
		}
		job.discardPorts[port] = true
		job.runtime.Logger.Info("port(%d) will start with an empty dataset and full sync from %s",
			port, expect.masterAddr())
	}
}

// whyKeepLocalData 返回不能空载起进程的原因, 空字符串表示可以
func (job *RedisVersionUpdate) whyKeepLocalData(port int, expect replSnapshot) string {
	if !consts.IsRedisInstanceDbType(job.params.ClusterType) {
		return fmt.Sprintf("cluster_type(%s) is not cache", job.params.ClusterType)
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli := job.AddrMapCli[addr]
	if cli == nil {
		if connected, connErr := job.tryConnectForRuntimeType(addr, port); connErr != nil {
			job.runtime.Logger.Warn(
				"port(%d) runtime db type unverified, instance not running, trust cluster_type(%s),err:%v",
				port, job.params.ClusterType, connErr)
		} else {
			cli = connected
		}
	}
	if cli != nil {
		// 元数据说是 cache, 机器上跑的却是 tendisplus/TendisSSD: 以运行态为准
		dbType, err := cli.GetTendisType()
		if err != nil {
			return fmt.Sprintf("get runtime db type failed:%v", err)
		}
		if dbType != consts.TendisTypeRedisInstance {
			return fmt.Sprintf("runtime db type is %s,not cache", dbType)
		}
	}
	if !expect.isSlave() {
		return "instance is not expected to replicate from anyone after restart"
	}
	if err := job.checkSyncMasterHealthy(port, expect.masterAddr()); err != nil {
		return err.Error()
	}
	return ""
}

// tryConnectForRuntimeType 空载判定时补一次运行态探测. 不用 WithRetry: 已停的实例应马上失败.
func (job *RedisVersionUpdate) tryConnectForRuntimeType(addr string, port int) (*myredis.RedisClient, error) {
	password, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return nil, err
	}
	cli, err := myredis.NewRedisClient(addr, password, 0, consts.TendisTypeRedisInstance, 2*time.Second)
	if err != nil {
		return nil, err
	}
	if job.AddrMapCli == nil {
		job.AddrMapCli = make(map[string]*myredis.RedisClient)
	}
	job.AddrMapCli[addr] = cli
	return cli, nil
}

// checkSyncMasterHealthy 确认那台主库现在活着、而且确实是 master.
//
// 数据挪走之后全集群就只剩主库这一份了: 主库连不上, 或它自己也已经是个从库时,
// 空载起进程等于把数据丢掉.
func (job *RedisVersionUpdate) checkSyncMasterHealthy(port int, masterAddr string) error {
	passwd, err := myredis.GetRedisPasswdFromConfFile(port)
	if err != nil {
		return fmt.Errorf("get password from conf file failed:%v", err)
	}
	cli, err := myredis.NewRedisClient(masterAddr, passwd, 0, consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return fmt.Errorf("connect master(%s) failed:%v", masterAddr, err)
	}
	defer cli.Close()
	repls, err := cli.Info("replication")
	if err != nil {
		return fmt.Errorf("master(%s) info replication failed:%v", masterAddr, err)
	}
	if role := repls["role"]; role != consts.RedisMasterRole {
		return fmt.Errorf("master(%s) role is %s", masterAddr, role)
	}
	return nil
}

// localDataFileNames 本地数据文件/目录的名字, 以及它们所在的数据目录.
//
// 名字从配置文件里取而不是写死: 取错了等于没挪走, 进程照样会把旧数据加载起来.
// 重建配置之后新旧两份配置都要看 —— 跨大版本升级时它们用的可能不是同一套名字.
func (job *RedisVersionUpdate) localDataFileNames(port int) (dataDir string, names []string, err error) {
	confFile, err := getRedisConfFileForRegen(port)
	if err != nil {
		return "", nil, err
	}
	confFiles := []string{confFile}
	if backupFile, ok := job.confBackupFiles[port]; ok {
		confFiles = append(confFiles, backupFile)
	}
	nameSet := make(map[string]struct{}, len(localDataFileEntries))
	for _, file := range confFiles {
		data, readErr := os.ReadFile(file)
		if readErr != nil {
			return "", nil, fmt.Errorf("read conf(%s) failed,err:%v", file, readErr)
		}
		directives := parseRedisConfDirectives(string(data))
		if dataDir == "" {
			dataDir = unquoteConfValue(directives.lastValue("dir"))
		}
		for _, entry := range localDataFileEntries {
			name := unquoteConfValue(directives.lastValue(entry.confName))
			if name == "" {
				name = entry.defaultVal
			}
			// 只认单层文件名: 带路径的取值挪起来可能碰到数据目录之外的东西
			if name != filepath.Base(name) || name == "." || name == ".." {
				job.runtime.Logger.Warn("port(%d) skip suspicious %s value %q", port, entry.confName, name)
				continue
			}
			nameSet[name] = struct{}{}
		}
	}
	if dataDir == "" {
		return "", nil, fmt.Errorf("port(%d) conf(%s) has no dir directive", port, confFile)
	}
	for name := range nameSet {
		names = append(names, name)
	}
	sort.Strings(names)
	return dataDir, names, nil
}

// moveAsideLocalData 把本地 RDB/AOF 改名挪开, 停实例之后、拉起之前调用.
//
// 只动数据文件: nodes.conf 是 cluster 的节点身份, redis.conf 是刚重建好的配置, 都不能碰.
func (job *RedisVersionUpdate) moveAsideLocalData(port int) error {
	if !job.discardingLocalData(port) {
		return nil
	}
	dataDir, names, err := job.localDataFileNames(port)
	if err != nil {
		job.runtime.Logger.Error("%s", err)
		return err
	}
	suffix := ".upgrade_bak_" + time.Now().Format(consts.FilenameTimeLayout)
	for _, name := range names {
		origin := filepath.Join(dataDir, name)
		if !util.FileExists(origin) {
			continue
		}
		moved := origin + suffix
		if err = os.Rename(origin, moved); err != nil {
			err = fmt.Errorf("port(%d) move aside %s failed,err:%v", port, origin, err)
			job.runtime.Logger.Error("%s", err)
			// 已挪走的要放回去, 否则实例会带着半套数据起来
			if restoreErr := job.restoreDiscardedLocalData(port); restoreErr != nil {
				job.runtime.Logger.Error("port(%d) restore local data failed,err:%v", port, restoreErr)
			}
			return err
		}
		job.discardedFiles[port] = append(job.discardedFiles[port], discardedDataFile{origin: origin, moved: moved})
		job.runtime.Logger.Info("port(%d) moved aside %s -> %s", port, origin, filepath.Base(moved))
	}
	if len(job.discardedFiles[port]) == 0 {
		job.runtime.Logger.Info("port(%d) no local data file found in %s,nothing to move aside", port, dataDir)
	}
	return nil
}

// restoreDiscardedLocalData 把挪走的数据放回去, 新版本进程起不来时用
func (job *RedisVersionUpdate) restoreDiscardedLocalData(port int) error {
	moved := job.discardedFiles[port]
	for idx := len(moved) - 1; idx >= 0; idx-- {
		item := moved[idx]
		// 上一次启动尝试可能已经写出了同名的新文件, 先清掉再放回原来那份
		if util.FileExists(item.origin) {
			if err := os.RemoveAll(item.origin); err != nil {
				return fmt.Errorf("port(%d) remove %s failed,err:%v", port, item.origin, err)
			}
		}
		if err := os.Rename(item.moved, item.origin); err != nil {
			return fmt.Errorf("port(%d) restore %s failed,err:%v", port, item.origin, err)
		}
		job.runtime.Logger.Info("port(%d) restored %s", port, item.origin)
	}
	delete(job.discardedFiles, port)
	return nil
}

// cleanupDiscardedLocalData 同步完成后删掉挪走的那份数据.
//
// 删不掉不算升级失败: 数据已经从主库同步回来了, 留下的只是一份占磁盘的旧文件.
func (job *RedisVersionUpdate) cleanupDiscardedLocalData(port int) {
	for _, item := range job.discardedFiles[port] {
		if err := os.RemoveAll(item.moved); err != nil {
			job.runtime.Logger.Warn("port(%d) remove %s failed,err:%v", port, item.moved, err)
			continue
		}
		job.runtime.Logger.Info("port(%d) removed %s", port, item.moved)
	}
	delete(job.discardedFiles, port)
}

// restoreClusterFailoverPermission 同步完成后恢复本节点被选为新主的资格.
//
// 空载起进程期间由 applyClusterNoFailoverToConf 禁掉了自动 failover: 一个刚被清空、
// 还在全量同步的从库若此时被选上, 它负责的 slot 会连带数据一起变空, 而且没有任何报错.
// 现在数据已经追齐, 必须改回去 —— 留着不改, 这个节点在往后每一次真实故障里都不会顶上.
func (job *RedisVersionUpdate) restoreClusterFailoverPermission(port int) error {
	if !consts.IsClusterDbType(job.params.ClusterType) {
		return nil
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli := job.AddrMapCli[addr]
	if cli == nil {
		err := fmt.Errorf("redis(%s) no client to reset cluster-*-no-failover", addr)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	confName, val, err := clusterNoFailoverFromRuntime(cli)
	if err != nil {
		err = fmt.Errorf("redis(%s) config get cluster-*-no-failover failed,err:%v", addr, err)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	if val != "yes" {
		// 绝大多数端口本来就是 no, 每个都打一行只是把真正做了恢复的那几行淹掉
		job.runtime.Logger.Debug("redis(%s) cluster-*-no-failover=%s,no restore needed", addr, val)
		return nil
	}
	if _, err := cli.ConfigSet(confName, "no"); err != nil {
		err = fmt.Errorf("redis(%s) config set %s no failed,err:%v", addr, confName, err)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	// 只 config set 的话, 下次重启又会从配置文件里读回 yes
	if _, err := cli.ConfigRewrite(); err != nil {
		err = fmt.Errorf("redis(%s) config rewrite after resetting %s failed,err:%v", addr, confName, err)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	job.runtime.Logger.Info("redis(%s) %s reset to no", addr, confName)
	return nil
}

// clusterNoFailoverFromRuntime 读运行态里生效的 cluster-*-no-failover.
// 两种拼写都问一遍, 优先返回值为 yes 的那条; 都没有则 name/val 为空.
func clusterNoFailoverFromRuntime(cli *myredis.RedisClient) (name, val string, err error) {
	var lastErr error
	foundName, foundVal := "", ""
	for _, confName := range clusterNoFailoverDirectiveNames {
		got, getErr := cli.ConfigGet(confName)
		if getErr != nil {
			lastErr = getErr
			continue
		}
		cur := unquoteConfValue(got[confName])
		if cur == "yes" {
			return confName, cur, nil
		}
		if cur != "" && foundName == "" {
			foundName, foundVal = confName, cur
		}
	}
	if foundName != "" {
		return foundName, foundVal, nil
	}
	return "", "", lastErr
}
