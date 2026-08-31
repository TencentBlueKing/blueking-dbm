package atomredis

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisVersionUpdateParams redis 版本更新参数
type RedisVersionUpdateParams struct {
	common.MediaPkg
	IP          string `json:"ip" validate:"required"`
	Ports       []int  `json:"ports" validate:"required"`
	Role        string `json:"role" validate:"required"` // redis_master or redis_slave
	ClusterType string `json:"cluster_type"`
	// FlushAfterUpgrade 为 true 时, 在 startRedis (新版本) 启动完成、AOF/RDB load 完毕后,
	// 立刻向实例发送 flushall (cleanall / flushalldisk) 清空数据集. 用于 old_master 升级:
	// 升级后会作为 new_slave 重做全量同步, 旧数据冗余.
	//
	// 之所以在 start 之后 flush (而不是 stop 之前):
	//   - RedisInstance 主从架构, switch act 内部已 SHUTDOWN 旧 master,
	//     升级 act 介入时实例已死, 没有"还活着的连接"可供 flush.
	//   - 在 start 之后 flush 同时覆盖 Twemproxy 与 RedisInstance 两种路径, 行为统一.
	//
	// 仅以下三种 cluster_type 启用:
	//   - TwemproxyRedisInstance
	//   - RedisInstance
	//   - TwemproxyTendisSSDInstance
	FlushAfterUpgrade bool `json:"flush_after_upgrade"`
	// PortConfConfigs 目标版本的配置项, key 为端口号字符串.
	// 缺省(或某端口缺失)时该端口不重建配置文件, 保持只换二进制的旧行为.
	PortConfConfigs map[string]RedisConfRenderItem `json:"port_conf_configs"`
	// SyncMasters key 为端口号字符串, value 形如 "1.1.1.2:30000":
	// 该端口升级后应作为哪台主库的从库.
	//
	// 用于 old_master 升级: 切换后它要作为 new_slave 跟随 new_master.
	// 重建配置时直接把 replicaof 连同 masterauth 一并写进去(见 ensureMasterAuthForReplica),
	// 进程带着主从关系起来, 上游因此不再需要一个独立的"建立主从关系"子流程,
	// 也不存在"起来了但还没建同步"的中间态.
	//
	// cluster 架构下不写配置文件(主从关系在 nodes.conf 里), 只作为拉起后的校验期望.
	SyncMasters map[string]string `json:"sync_masters"`
	// DiscardLocalDataOnRestart 为 true 时, 停机后把本地 RDB/AOF 挪走, 让新版本进程空载起来,
	// 数据由主库全量同步补回. 详见 redis_data_discard.go.
	DiscardLocalDataOnRestart bool `json:"discard_local_data_on_restart"`
	// SyncWaitTimeoutSeconds 拉起后等待 master_link_status=up 的超时, 0 表示用默认值.
	// 空载起进程时数据要整份重传, 大实例可能超过半小时, 由上游按实例规模给值.
	SyncWaitTimeoutSeconds int `json:"sync_wait_timeout_seconds"`
}

// syncMasterAddr 返回该端口升级后应跟随的主库 host/port, 上游没指定时返回空
func (p *RedisVersionUpdateParams) syncMasterAddr(port int) (host, portStr string, err error) {
	addr, ok := p.SyncMasters[strconv.Itoa(port)]
	if !ok || strings.TrimSpace(addr) == "" {
		return "", "", nil
	}
	host, portStr, err = net.SplitHostPort(strings.TrimSpace(addr))
	if err != nil {
		return "", "", fmt.Errorf("sync_masters[%d]=%q is not a valid addr,err:%v", port, addr, err)
	}
	return host, portStr, nil
}

// syncWaitDoNotSkipHint 进程已拉起但同步校验失败时附在错误上, 会进单据 ex_data.
// 跳过这个节点不会再跑 restore, cluster-replica-no-failover 会一直留着 yes.
const syncWaitDoNotSkipHint = "进程已拉起,请等待主从同步完成后重试本节点,不要直接跳过。" +
	"跳过不会再跑 restore,会留下 cluster-replica-no-failover=yes,故障时该节点不会被选主"

func wrapSyncWaitErr(err error) error {
	if err == nil {
		return nil
	}
	if strings.Contains(err.Error(), "不要直接跳过") {
		return err
	}
	if !strings.Contains(err.Error(), "master_link_status") {
		return err
	}
	return fmt.Errorf("%w; %s", err, syncWaitDoNotSkipHint)
}

// RedisVersionUpdate TODO
type RedisVersionUpdate struct {
	runtime          *jobruntime.JobGenericRuntime
	params           RedisVersionUpdateParams
	localPkgBaseName string
	// confBackupFiles port -> 本次重建配置前的备份文件, 供起不来时回滚
	confBackupFiles map[int]string
	// replSnapshots port -> 停机前的复制状态, 拉起后据此钉死"角色和主库都没变"
	replSnapshots map[int]replSnapshot
	// discardPorts port -> 本次是否空载起进程(挪走本地 RDB/AOF), 停机前一次算好
	discardPorts map[int]bool
	// discardedFiles port -> 已挪走的数据文件, 起不来时放回去, 同步好后删掉
	discardedFiles map[int][]discardedDataFile
	// settledPorts port -> 本次已经钉过复制状态并恢复过 failover 资格.
	// 重启循环里做完就记上, 末尾的兜底循环据此跳过, 否则同一个端口会被收尾两遍.
	settledPorts map[int]bool
	AddrMapCli   map[string]*myredis.RedisClient `json:"addr_map_cli"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisVersionUpdate)(nil)

// NewRedisVersionUpdate new
func NewRedisVersionUpdate() jobruntime.JobRunner {
	return &RedisVersionUpdate{}
}

// Init prepare run env
func (job *RedisVersionUpdate) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error("json.Unmarshal failed,err:%+v", err)
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("RedisVersionUpdate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisVersionUpdate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if len(job.params.Ports) == 0 {
		err = fmt.Errorf("RedisVersionUpdate Init ports(%+v) is empty", job.params.Ports)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	if job.params.ClusterType != "" && !knownRedisStorageClusterType(job.params.ClusterType) {
		err = fmt.Errorf("unknown cluster_type(%s)", job.params.ClusterType)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	job.confBackupFiles = make(map[int]string, len(job.params.Ports))
	job.replSnapshots = make(map[int]replSnapshot, len(job.params.Ports))
	job.discardPorts = make(map[int]bool, len(job.params.Ports))
	job.discardedFiles = make(map[int][]discardedDataFile, len(job.params.Ports))
	job.settledPorts = make(map[int]bool, len(job.params.Ports))
	return nil
}

// Name 原子任务名
func (job *RedisVersionUpdate) Name() string {
	return "redis_version_update"
}

// Run Command Run
func (job *RedisVersionUpdate) Run() (err error) {
	if job.params.Role == consts.MetaRoleRedisMaster && job.params.ClusterType == consts.TendisTypeRedisInstance {
		// 对RedisInstance + redis_master 升级,单独处理
		return job.upgradeRedisInstanceMaster()
	}
	// 本地redis连接测试. allInstsAbleToConnect 做的就是同一件事, 而且把 client 留了下来,
	// 不必先跑一遍 LocalRedisConnectTest 再连第二遍
	err = job.allInstsAbleToConnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()

	if job.params.Role != consts.MetaRoleRedisMaster && job.params.Role != consts.MetaRoleRedisSlave {
		err = fmt.Errorf("role:%s not support", job.params.Role)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	// 停机前记下复制状态, 拉起后据此钉死"角色和主库都没变"
	if err = job.captureAllReplSnapshots(); err != nil {
		return err
	}
	if err = job.precheckSyncMasters(); err != nil {
		return err
	}
	// 是否空载起进程也要在停机前算好: 判断依赖运行态(实例类型/主库健康), 停了就问不到了
	job.planLocalDataDiscard()
	err = job.getLocalRedisPkgBaseName()
	if err != nil {
		return err
	}
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error("%s", err)
		return err
	}
	err = job.checkRedisLocalPkgAndTargetPkgSameType()
	if err != nil {
		return err
	}
	// 配置重建发生在 stop 之后, 但校验要放在 stop 之前: 否则实例全停、软链已切,
	// 才发现配置有问题, 现场得人工拉起
	restartPorts, err := job.portsNeedRestart()
	if err != nil {
		return err
	}
	// 只检查还要重启的端口: 已升完、正在全量同步的从库 link 还是 down,
	// 以及 Twemproxy old_master 第一次跑完已经变成 slave, 都不能再用入口处的严格预检挡住重试.
	if err = job.precheckInstanceRoles(restartPorts); err != nil {
		return err
	}
	if err = job.precheckReplExpectation(restartPorts); err != nil {
		return err
	}
	if err = job.precheckConfRegen(restartPorts); err != nil {
		return err
	}
	pkgNeedsSwitch := job.localPkgBaseName != job.params.GePkgBaseName()
	if pkgNeedsSwitch {
		err = job.untarMedia()
		if err != nil {
			return err
		}
	}
	for _, port := range restartPorts {
		err = job.beforeStopRedis(port)
		if err != nil {
			return err
		}
		err = job.stopRedis(port)
		if err != nil {
			return err
		}
	}
	if pkgNeedsSwitch {
		err = job.updateFileLink()
		if err != nil {
			return err
		}
	}
	for _, port := range restartPorts {
		err = job.regenConfAndStartRedis(port)
		if err != nil {
			return err
		}
		if job.params.FlushAfterUpgrade {
			err = job.flushDataAfterStart(port)
			if err != nil {
				return err
			}
		}
	}
	// 已是目标版本的端口不会进上面的重启循环, 重试时在这里等同步并按运行态 restore
	if err = job.settleUnsettledPorts(); err != nil {
		return err
	}
	return nil
}

// portsNeedRestart 返回本次真正会被重启(因而需要重建配置)的端口.
//
// 软链还没指向目标版本时所有端口都要重启; 否则只有运行态版本还没切过来的端口需要,
// 已经在目标版本上的端口不会被 stop, 也就不该因为它的配置校验不过而失败.
func (job *RedisVersionUpdate) portsNeedRestart() ([]int, error) {
	if job.localPkgBaseName != job.params.GePkgBaseName() {
		return job.params.Ports, nil
	}
	ports := make([]int, 0, len(job.params.Ports))
	for _, port := range job.params.Ports {
		cli := job.AddrMapCli[net.JoinHostPort(job.params.IP, strconv.Itoa(port))]
		ok, err := job.isRedisRuntimeVersionOK(cli)
		if err != nil {
			return nil, err
		}
		if !ok {
			ports = append(ports, port)
		}
	}
	return ports, nil
}

// replExpectation 该端口重启后应达成的复制状态.
//
// 上游通过 sync_masters 指定了新主库时以它为准: old_master 升级后要作为 new_slave
// 跟随 new_master, 此时"和停机前一样"恰恰是错的, 拿停机前快照去校验会把正确结果判成失败.
// 没指定时退回停机前快照, 也就是"角色和主库都不许变".
func (job *RedisVersionUpdate) replExpectation(port int) replSnapshot {
	host, portStr, err := job.params.syncMasterAddr(port)
	if err != nil {
		// 参数格式问题在 precheckSyncMasters 里已经拦下, 这里只兜底
		job.runtime.Logger.Warn("%s", err)
		return job.replSnapshots[port]
	}
	return resolveReplExpectation(
		net.JoinHostPort(job.params.IP, strconv.Itoa(port)), host, portStr, job.replSnapshots[port])
}

// precheckSyncMasters 校验 sync_masters 参数本身可用, 停机前跑.
//
// 非 cluster 架构靠重建配置文件里的 replicaof 来建立主从关系, 所以没下发目标版本配置的端口
// 根本没有落地手段: 实例会作为一个孤立的 master 起来, 而上游已经不再有建同步的步骤了.
// 这种组合必须在停实例之前失败.
func (job *RedisVersionUpdate) precheckSyncMasters() error {
	if len(job.params.SyncMasters) == 0 {
		return nil
	}
	if job.params.FlushAfterUpgrade {
		// 实例带着 replicaof 起来, 数据由主库全量同步补回: 此时 flushall 既清不掉
		// (从库默认只读, 会被拒), 也没有要清的东西
		err := fmt.Errorf("sync_masters and flush_after_upgrade are mutually exclusive")
		job.runtime.Logger.Error("%s", err)
		return err
	}
	for _, port := range job.params.Ports {
		host, portStr, err := job.params.syncMasterAddr(port)
		if err != nil {
			job.runtime.Logger.Error("%s", err)
			return err
		}
		if host == "" {
			continue
		}
		if consts.IsClusterDbType(job.params.ClusterType) {
			// cluster 架构的主从关系在 nodes.conf 里, 这里只当拉起后的校验期望用
			continue
		}
		item, ok := job.params.PortConfConfigs[strconv.Itoa(port)]
		if !ok || len(item.ConfConfigs) == 0 {
			err = fmt.Errorf("port(%d) sync_masters requires target version conf to write replicaof %s %s, "+
				"but no conf delivered for this port", port, host, portStr)
			job.runtime.Logger.Error("%s", err)
			return err
		}
	}
	job.runtime.Logger.Info("sync_masters precheck passed:%+v", job.params.SyncMasters)
	return nil
}

// beforeStopRedis 停实例之前的最后一步.
//
// 空载起进程时, 本地那份数据马上就要被挪走, 再为它做一次 bgsave 纯属浪费;
// 顺手把 save 清空, 免得 stop-redis.sh 的 SHUTDOWN 卡在一次阻塞式 SAVE 上.
func (job *RedisVersionUpdate) beforeStopRedis(port int) error {
	if !job.discardingLocalData(port) {
		return job.checkAndBackupRedis(port)
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	job.runtime.Logger.Info("redis instance(%s) starts empty after upgrade,skip backup before stop", addr)
	cli := job.AddrMapCli[addr]
	if cli == nil {
		return nil
	}
	if _, err := cli.ConfigSet("save", ""); err != nil {
		// 失败不致命: dbconfig 里 cache 的 save 本来就是空, 真有存盘点也只是多花一次 SAVE 的时间
		job.runtime.Logger.Warn("redis instance(%s) config set save '' failed,shutdown may block on a save,err:%v",
			addr, err)
	}
	return nil
}

// captureAllReplSnapshots 在任何 stop 之前记下每个实例的复制状态
func (job *RedisVersionUpdate) captureAllReplSnapshots() error {
	for _, port := range job.params.Ports {
		addr := net.JoinHostPort(job.params.IP, strconv.Itoa(port))
		cli := job.AddrMapCli[addr]
		if cli == nil {
			err := fmt.Errorf("redis(%s) not connected,cannot capture repl snapshot before restart", addr)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		snap, err := captureReplSnapshot(cli)
		if err != nil {
			job.runtime.Logger.Error("%s", err)
			return err
		}
		job.replSnapshots[port] = snap
		job.runtime.Logger.Info("redis(%s) repl state before restart:role=%s,master=%q",
			addr, snap.role, snap.masterAddr())
	}
	return nil
}

// precheckReplExpectation 停机前校验磁盘配置文件里的主从关系符合预期.
//
// 放在停实例之前: 不一致时实例还都在跑, 现场是干净的.
// 这一条不依赖是否重建配置 —— 一份陈旧的 replicaof 只要指向的主还活着且同密码,
// 只换二进制的重启也会让实例悄悄跟错主, 而下一跳往往就是切主.
func (job *RedisVersionUpdate) precheckReplExpectation(ports []int) error {
	if len(ports) == 0 {
		return nil
	}
	for _, port := range ports {
		confFile, err := getRedisConfFileForRegen(port)
		if err != nil {
			// 老部署可能只有 instance.conf. 缺 redis.conf 时降级为只做拉起后断言,
			// 不让"只换二进制"的存量路径失败
			job.runtime.Logger.Warn("port(%d) skip conf level replication precheck,err:%v", port, err)
			continue
		}
		confBytes, err := os.ReadFile(confFile)
		if err != nil {
			err = fmt.Errorf("read redis conf(%s) failed,err:%v", confFile, err)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		if err = job.checkConfReplExpectation(port, string(confBytes)); err != nil {
			err = fmt.Errorf("port(%d) conf(%s) %v", port, confFile, err)
			job.runtime.Logger.Error("%s", err)
			return err
		}
	}
	job.runtime.Logger.Info("replication expectation precheck passed,ports:%+v", ports)
	return nil
}

// checkConfReplExpectation 校验一份配置文件里的主从关系符合预期.
//
// 有停机前快照时以运行态为准; 没抓到快照(实例已被上游 switch act 关掉)时,
// 退化成按元数据角色判断 —— master 的配置文件里不该有生效的 replicaof.
func (job *RedisVersionUpdate) checkConfReplExpectation(port int, confData string) error {
	if host, _, _ := job.params.syncMasterAddr(port); host != "" {
		// 这份配置马上会被整份重建, 里面的主从关系由 applyReplExpectationToConf 写定,
		// 磁盘上的旧内容不影响结果; 渲染结果由 checkRegenConfReplication 校验
		job.runtime.Logger.Info("port(%d) skip conf level replication precheck,replicaof will be regenerated", port)
		return nil
	}
	snap := job.replSnapshots[port]
	if snap.captured() {
		return snap.checkConfMatchesExpectation(confData, job.params.ClusterType)
	}
	if consts.IsClusterDbType(job.params.ClusterType) {
		// cluster 实例的配置文件里本来就没有 replicaof, 没什么可比的
		return nil
	}
	if job.params.Role != consts.MetaRoleRedisMaster {
		job.runtime.Logger.Warn(
			"port(%d) no repl snapshot and meta role is %s,skip conf level replication precheck",
			port, job.params.Role)
		return nil
	}
	if _, confTarget := effectiveReplicationOf(confData); confTarget != "" {
		return fmt.Errorf("meta role is %s, but conf file declares replication of %q, "+
			"restart would turn a master into a replica", job.params.Role, confTarget)
	}
	return nil
}

func (job *RedisVersionUpdate) upgradeRedisInstanceMaster() (err error) {
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	defer job.allInstDisconnect()

	err = job.getLocalRedisPkgBaseName()
	if err != nil {
		return err
	}
	err = job.params.Check()
	if err != nil {
		return err
	}
	err = job.checkRedisLocalPkgAndTargetPkgSameType()
	if err != nil {
		return err
	}
	// 实例此时多半已被 switch act 关掉, 无从判断运行态版本, 而后面所有端口都会重建配置,
	// 所以直接全量预校验, 避免解压、切软链之后才失败
	if err = job.precheckSyncMasters(); err != nil {
		return err
	}
	job.planLocalDataDiscard()
	if err = job.precheckReplExpectation(job.params.Ports); err != nil {
		return err
	}
	if err = job.precheckConfRegen(job.params.Ports); err != nil {
		return err
	}
	pkgNeedsSwitch := job.localPkgBaseName != job.params.GePkgBaseName()
	if pkgNeedsSwitch {
		// 解压 介质 到 /usr/local/
		err = job.untarMedia()
		if err != nil {
			return err
		}
		// 注: 走到这里时, switch act 内部的 tryShutdownMasterInstance 多半已把旧 master 关掉,
		// CheckPortIsInUse 大概率返回 false; 这里仍兜底处理 "万一还活着" 的情况.
		for _, port := range job.params.Ports {
			isAlive, probeErr := portInUse(job.params.IP, port)
			if probeErr != nil {
				return probeErr
			}
			if !isAlive {
				continue
			}
			err = job.stopRedis(port)
			if err != nil {
				return err
			}
		}
		// 更新 /usr/local/redis 软链接
		err = job.updateFileLink()
		if err != nil {
			return err
		}
	}
	for _, port := range job.params.Ports {
		runningTarget, runErr := job.runningOnTargetVersion(port)
		if runErr != nil {
			return runErr
		}
		if runningTarget {
			// 软链和运行版本都已到位: 不要再 regen/挪数据, 那会打断正在追的全量同步
			continue
		}
		inUse, probeErr := portInUse(job.params.IP, port)
		if probeErr != nil {
			return probeErr
		}
		if inUse {
			if err = job.ensurePortConnected(port); err != nil {
				return err
			}
			if err = job.beforeStopRedis(port); err != nil {
				return err
			}
			if err = job.stopRedis(port); err != nil {
				return err
			}
		}
		err = job.regenConfAndStartRedis(port)
		if err != nil {
			return err
		}
		if job.params.FlushAfterUpgrade {
			err = job.flushDataAfterStart(port)
			if err != nil {
				return err
			}
		}
	}
	if err = job.settleUnsettledPorts(); err != nil {
		return err
	}
	return nil
}

// localInstCount 本机实例个数. tendisplus 的 blockcache / write buffer 按实例数分摊,
// 用本次升级的端口数会在只升一部分端口时低估分母, 把每实例的 blockcache 算大.
// 与 RedisConfRefresh 保持同一口径; 数不出来(目录形态不常规)时回落到端口数.
func (job *RedisVersionUpdate) localInstCount() uint64 {
	if count := countLocalRedisInstDirs(); count > 0 {
		return count
	}
	return uint64(len(job.params.Ports))
}

// regenRequest 把版本升级任务的参数映射成一次重建请求的实例维度部分.
//
// 与 RedisConfRefresh.regenRequest 对照: 升级填目标介质、允许改拓扑(sync_masters)、
// 空载起进程时暂时禁掉 cluster failover; 刷新配置则用当前软链、保持停机前快照、不挪数据.
func (job *RedisVersionUpdate) regenRequest(port int) confRegenRequest {
	return confRegenRequest{
		IP:               job.params.IP,
		Port:             port,
		PkgBaseName:      job.params.GePkgBaseName(),
		ClusterType:      job.params.ClusterType,
		InstCount:        job.localInstCount(),
		Expect:           job.replExpectation(port),
		DiscardLocalData: job.discardingLocalData(port),
		Logger:           job.runtime.Logger,
	}
}

// buildRegenConfPlan 组装本端口的重建请求, 跑完渲染与校验.
//
// 返回 (nil, nil) 表示该端口无需重建, 保持"只换二进制"的旧行为.
func (job *RedisVersionUpdate) buildRegenConfPlan(port int) (*regenConfPlan, error) {
	item, ok := job.params.PortConfConfigs[strconv.Itoa(port)]
	return buildRegenPlan(job.regenRequest(port), item, ok)
}

// precheckConfRegen 在停实例、切软链之前先把目标配置渲染并校验一遍.
//
// 重建配置是在 stop 之后做的, 那时校验不过就地退出, 会留下一批停着的实例和
// 已经切走的软链, 需要人工拉起. 提前跑一遍同样的渲染与校验, 有问题时实例还都在跑.
func (job *RedisVersionUpdate) precheckConfRegen(ports []int) error {
	if len(ports) == 0 {
		return nil
	}
	checked := make([]int, 0, len(ports))
	for _, port := range ports {
		plan, err := job.buildRegenConfPlan(port)
		if err != nil {
			job.runtime.Logger.Error("%s", err)
			return err
		}
		if plan != nil {
			checked = append(checked, port)
		}
	}
	// 没下发目标配置的端口只换二进制, 压根不重建配置. 一律打 "precheck passed" 会让人
	// 以为校验过了, 而紧接着的日志又是 "skip conf regenerate", 前后看着矛盾
	if len(checked) == 0 {
		job.runtime.Logger.Info("no target version conf delivered for ports:%+v,nothing to precheck", ports)
		return nil
	}
	job.runtime.Logger.Info("conf regenerate precheck passed,ports:%+v", checked)
	return nil
}

// regenConfFile 用目标版本的 dbconfig 重建实例配置文件.
//
// PortConfConfigs 中没有该端口时直接返回 nil, 保持"只换二进制"的旧行为.
func (job *RedisVersionUpdate) regenConfFile(port int) (err error) {
	plan, err := job.buildRegenConfPlan(port)
	if err != nil {
		return err
	}
	if plan == nil {
		job.runtime.Logger.Info("port(%d) no target version conf delivered,skip conf regenerate", port)
		return nil
	}
	backupFile, err := writeRegenConfPlan(plan, port, job.runtime.Logger)
	if err != nil {
		return err
	}
	job.confBackupFiles[port] = backupFile
	return nil
}

// restoreRedisConfFile 回滚配置文件.
// 用目标版本配置起不来时, 把旧配置放回去再重试一次, 最差退化到旧行为.
func (job *RedisVersionUpdate) restoreRedisConfFile(port int) error {
	backupFile, ok := job.confBackupFiles[port]
	if !ok || backupFile == "" {
		return fmt.Errorf("port(%d) no conf backup to restore", port)
	}
	confFile, err := getRedisConfFileForRegen(port)
	if err != nil {
		return err
	}
	backupBytes, err := os.ReadFile(backupFile)
	if err != nil {
		return fmt.Errorf("read conf backup(%s) failed,err:%v", backupFile, err)
	}
	if err = writeRedisConfFile(confFile, backupBytes); err != nil {
		return fmt.Errorf("restore conf(%s) from %s failed,err:%v", confFile, backupFile, err)
	}
	delete(job.confBackupFiles, port)
	return nil
}

// regenConfAndStartRedis 重建目标版本配置文件、按需挪走本地数据后拉起实例.
//
// 新配置起不来时, 把旧配置和本地数据都放回去再试一次: 最差退化成"只换二进制"的旧行为,
// 而不是留下一个起不来、数据还被挪走了的实例.
func (job *RedisVersionUpdate) regenConfAndStartRedis(port int) (err error) {
	if err = job.regenConfFile(port); err != nil {
		return err
	}
	if err = job.moveAsideLocalData(port); err != nil {
		return err
	}
	err = job.startRedis(port)
	if err == nil {
		// startRedis 里已经等到复制链路 UP, 挪走的那份数据不再需要
		job.cleanupDiscardedLocalData(port)
		if err = job.restoreClusterFailoverPermission(port); err != nil {
			return err
		}
		job.markSettled(port)
		return nil
	}
	_, hasConfBackup := job.confBackupFiles[port]
	if !hasConfBackup && len(job.discardedFiles[port]) == 0 {
		// 既没重建配置也没挪数据, 没什么可回滚的
		return err
	}
	inUse, probeErr := portInUse(job.params.IP, port)
	if probeErr != nil {
		// 探测失败按"可能还活着"处理: 不回滚, 否则可能对运行中实例 RemoveAll
		job.runtime.Logger.Error("redis(%s:%d) check port in use failed,skip rollback,err:%v",
			job.params.IP, port, probeErr)
		return wrapSyncWaitErr(fmt.Errorf("%w; check port in use failed,err:%v", err, probeErr))
	}
	if inUse {
		// 进程已经起来了(失败在同步状态等后续检查), 回滚只会掩盖真实问题
		return wrapSyncWaitErr(err)
	}
	job.runtime.Logger.Warn("redis(%s:%d) start failed with regenerated conf,err:%v,restore old conf/data and retry",
		job.params.IP, port, err)
	if restoreErr := job.restoreDiscardedLocalData(port); restoreErr != nil {
		job.runtime.Logger.Error("redis(%s:%d) restore local data failed,err:%v", job.params.IP, port, restoreErr)
		return err
	}
	if hasConfBackup {
		if restoreErr := job.restoreRedisConfFile(port); restoreErr != nil {
			job.runtime.Logger.Error("redis(%s:%d) restore conf failed,err:%v", job.params.IP, port, restoreErr)
			return err
		}
	}
	return job.startRedis(port)
}

func (job *RedisVersionUpdate) getLocalRedisPkgBaseName() (err error) {
	job.localPkgBaseName, err = readLocalRedisPkgBaseName()
	if err != nil {
		job.runtime.Logger.Error("%s", err)
		return err
	}
	job.runtime.Logger.Info("before update,%s->%s",
		filepath.Join(consts.UsrLocal, "redis"), job.localPkgBaseName)
	return nil
}

// checkRedisLocalPkgAndTargetPkgSameType 检查reids本地包与目标包是同一类型,避免 cache redis 传的是 tendisplus 的包
func (job *RedisVersionUpdate) checkRedisLocalPkgAndTargetPkgSameType() (err error) {
	targetPkgName := job.params.GePkgBaseName()
	targetDbType := util.GetRedisDbTypeByPkgName(targetPkgName)
	localDbType := util.GetRedisDbTypeByPkgName(job.localPkgBaseName)
	if targetDbType != localDbType {
		err = fmt.Errorf("/usr/local/redis->%s cannot update to %s", job.localPkgBaseName, targetPkgName)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	return nil
}

// allInstsAbleToConnect 检查所有实例可连接
func (job *RedisVersionUpdate) allInstsAbleToConnect() (err error) {
	var addr string
	instsAddrs := make([]string, 0, len(job.params.Ports))
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	for _, port := range job.params.Ports {
		addr = fmt.Sprintf("%s:%d", job.params.IP, port)
		instsAddrs = append(instsAddrs, addr)
		cli, err := connectLocalRedis(addr, port, 5*time.Second)
		if err != nil {
			return err
		}
		// 把运行态配置刷回文件, 重启后才不会用一份陈旧配置起来.
		// 失败必须留痕: 正是它静默失败, 配置文件里的 replicaof 才会指向一台旧主
		if _, rewriteErr := cli.ConfigRewrite(); rewriteErr != nil {
			job.runtime.Logger.Warn("redis(%s) config rewrite failed,conf file may be stale,err:%v",
				addr, rewriteErr)
		}
		job.AddrMapCli[addr] = cli
	}
	job.runtime.Logger.Info("all redis instances able to connect,(%+v)", instsAddrs)
	return nil
}

// allInstDisconnect 所有实例断开连接
func (job *RedisVersionUpdate) allInstDisconnect() {
	for _, cli := range job.AddrMapCli {
		cli.Close()
	}
}

func (job *RedisVersionUpdate) isAllInstanceMaster(ports []int) (err error) {
	for _, port := range ports {
		addr := fmt.Sprintf("%s:%d", job.params.IP, port)
		cli := job.AddrMapCli[addr]
		if cli == nil {
			err = fmt.Errorf("redis instance(%s) not connected,cannot check master role", addr)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		repls, err := cli.Info("replication")
		if err != nil {
			return err
		}
		if repls["role"] != consts.RedisMasterRole {
			err = fmt.Errorf("redis instance(%s) is not master", cli.Addr)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		// 是否要检查 master 是否还有 slave?
	}
	return nil
}

func (job *RedisVersionUpdate) isAllInstanceSlave(ports []int) (err error) {
	var logTailNData string
	for _, port := range ports {
		addr := fmt.Sprintf("%s:%d", job.params.IP, port)
		cli := job.AddrMapCli[addr]
		if cli == nil {
			err = fmt.Errorf("redis instance(%s) not connected,cannot check slave role", addr)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		repls, err := cli.Info("replication")
		if err != nil {
			return err
		}
		if repls["role"] != consts.RedisSlaveRole {
			err = fmt.Errorf("redis instance(%s) is not slave", cli.Addr)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		if repls["master_link_status"] != consts.MasterLinkStatusUP {
			logTailNData, _ = cli.TailRedisLogFile(40)
			if strings.Contains(logTailNData, "Can't handle RDB format") {
				// RDB格式不兼容,忽略
				job.runtime.Logger.Warn(
					"redis instance(%s) master_link_status:%s is not UP, but RDB format is not compatible,ignore", cli.Addr,
					repls["master_link_status"])
				continue
			}
			err = fmt.Errorf("redis instance(%s) master_link_status:%s is not UP", cli.Addr, repls["master_link_status"])
			job.runtime.Logger.Error("%s", err)
			return err
		}
		master_last_io_seconds_ago, err := strconv.Atoi(repls["master_last_io_seconds_ago"])
		if err != nil {
			err = fmt.Errorf("redis instance(%s) master_last_io_seconds_ago:%s is not int", cli.Addr,
				repls["master_last_io_seconds_ago"])
			job.runtime.Logger.Error("%s", err)
			return err
		}
		if master_last_io_seconds_ago > 20 {
			err = fmt.Errorf("redis instance(%s) master_last_io_seconds_ago:%d is greater than 20", cli.Addr,
				master_last_io_seconds_ago)
			job.runtime.Logger.Error("%s", err)
			return err
		}
		job.runtime.Logger.Info(
			"redis instance(%s) is slave,master(%s:%s),master_link_status:%s,master_last_io_seconds_ago:%d",
			cli.Addr, repls["master_host"], repls["master_port"],
			repls["master_link_status"], master_last_io_seconds_ago)
	}
	return nil
}

// precheckInstanceRoles 只对还要重启的端口做升级前角色/同步健康检查.
func (job *RedisVersionUpdate) precheckInstanceRoles(ports []int) error {
	if len(ports) == 0 {
		return nil
	}
	switch job.params.Role {
	case consts.MetaRoleRedisMaster:
		return job.isAllInstanceMaster(ports)
	case consts.MetaRoleRedisSlave:
		return job.isAllInstanceSlave(ports)
	default:
		err := fmt.Errorf("role:%s not support", job.params.Role)
		job.runtime.Logger.Error("%s", err)
		return err
	}
}

// untarMedia 解压介质. 介质本身的校验由两个调用方在进来之前跑过 params.Check(), 这里不再重复
func (job *RedisVersionUpdate) untarMedia() (err error) {
	pkgAbsPath := job.params.GetAbsolutePath()
	untarCmd := fmt.Sprintf("tar -zxf %s -C %s", pkgAbsPath, consts.UsrLocal)
	job.runtime.Logger.Info("%s", untarCmd)
	_, err = util.RunBashCmd(untarCmd, "", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("untar %s success", pkgAbsPath)
	return nil
}

// updateFileLink 更新 /usr/local/redis 软链接
func (job *RedisVersionUpdate) updateFileLink() (err error) {
	pkgBaseName := job.params.GePkgBaseName()
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	_, err = os.Stat(redisSoftLink)
	if err == nil {
		// 删除 /usr/local/redis 软链接
		err = os.Remove(redisSoftLink)
		if err != nil {
			err = fmt.Errorf("remove redis soft link(%s) failed,err:%+v", redisSoftLink, err)
			job.runtime.Logger.Error("%s", err)
			return err
		}
	}
	// 创建 /usr/local/redis -> /usr/local/$pkgBaseName 软链接
	err = os.Symlink(filepath.Join(consts.UsrLocal, pkgBaseName), redisSoftLink)
	if err != nil {
		err = fmt.Errorf("os.Symlink %s -> %s fail,err:%s", redisSoftLink, filepath.Join(consts.UsrLocal, pkgBaseName), err)
		job.runtime.Logger.Error("%s", err)
		return
	}
	util.LocalDirChownMysql(redisSoftLink)
	util.LocalDirChownMysql(redisSoftLink + "/")
	job.runtime.Logger.Info("create softLink success,%s -> %s", redisSoftLink, filepath.Join(consts.UsrLocal, pkgBaseName))
	return nil
}

// checkAndBackupRedis 如果有必要先备份reids
func (job *RedisVersionUpdate) checkAndBackupRedis(port int) (err error) {
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	return backupCacheMasterBeforeStop(job.params.Role, addr, job.AddrMapCli[addr], job.runtime.Logger)
}

// flushDataAfterStart 在 startRedis 之后, 用于 old_master 升级:
// 升级后会作为 new_slave 重做全量同步
//
// 仅支持以下三种 cluster_type, 它们升级时依赖外部 (twemproxy 切换 / 主从对) 来重做全量同步:
//   - TwemproxyRedisInstance       (twemproxy + cache redis)
//   - RedisInstance                (cache redis 主从版)
//   - TwemproxyTendisSSDInstance   (twemproxy + TendisSSD)
//
// 不支持: 原生 RedisCluster / PredixyRedisCluster / 各类 Tendisplus / 单机版 TendisSSDInstance,
// 它们走自身 failover 协议或不需要 actuator 端 flush; 此处返回错误以暴露上游配置问题.
//
// 选用的命令:
//   - cache (cleanall, 4.0+ 追加 ASYNC 参数避免阻塞主线程)
//   - TendisSSD (flushalldisk)
//
// 调用前提: 调用方刚刚 startRedis 成功, 端口已 LISTEN; 实例可能仍在 AOF/RDB load 阶段
// (返回 LOADING). 函数内部会先 INFO persistence 等待 loading=0 再发 flush.
//
// 调用时机: 此时 old_master 已完成域名 / proxy 切换, 不再承载客户端流量, 也尚未 slaveof new_master,
// flush 不会向他处传播.
func (job *RedisVersionUpdate) flushDataAfterStart(port int) error {
	clusterType := job.params.ClusterType
	switch clusterType {
	case consts.TendisTypeTwemproxyRedisInstance,
		consts.TendisTypeTwemproxyTendisSSDInstance,
		consts.TendisTypeRedisInstance:
	default:
		return fmt.Errorf(
			"flush after upgrade: cluster_type(%s) not allowed; only %s / %s / %s are supported (port %d)",
			clusterType,
			consts.TendisTypeTwemproxyRedisInstance,
			consts.TendisTypeRedisInstance,
			consts.TendisTypeTwemproxyTendisSSDInstance,
			port)
	}

	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli, err := connectLocalRedis(addr, port, 10*time.Second)
	if err != nil {
		return fmt.Errorf("flush after upgrade: connect %s failed,err:%v", addr, err)
	}
	defer cli.Close()

	// 升级后第一次连上, 实例可能仍在 AOF / RDB load. 直接 flush 会被拒绝 (LOADING).
	// 30 分钟与 waitRestored 等其他长等待保持一致, 兜得住大 AOF.
	if err := job.waitForLoadingFinish(cli, 30*time.Minute); err != nil {
		return fmt.Errorf("flush after upgrade: %v", err)
	}
	if err := job.validateFlushAfterUpgradeSafety(cli); err != nil {
		return err
	}

	cmd, err := buildFlushAllCmd(clusterType, cli)
	if err != nil {
		return fmt.Errorf("flush after upgrade: build cmd for %s failed,err:%v", addr, err)
	}

	job.runtime.Logger.Info("flush after upgrade: addr=%s cmd=%v", addr, cmd)
	result, err := cli.DoCommand(cmd, 0)
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s cmd=%v err=%v", addr, cmd, err)
	}
	resultStr, ok := result.(string)
	if !ok || !strings.Contains(resultStr, "OK") {
		return fmt.Errorf("flush after upgrade: addr=%s cmd=%v result=%+v not OK", addr, cmd, result)
	}
	if err := job.checkFlushAfterUpgradeResult(cli); err != nil {
		return err
	}
	job.runtime.Logger.Info("flush after upgrade done: %s", addr)
	return nil
}

// validateFlushAfterUpgradeSafety 做最后一道 actuator 侧保护:
// 仅允许 old_master 升级 act 在实例已是 master 且没有 replica 连接时清档.
func (job *RedisVersionUpdate) validateFlushAfterUpgradeSafety(cli *myredis.RedisClient) error {
	if job.params.Role != consts.MetaRoleRedisMaster {
		return fmt.Errorf("flush after upgrade: addr=%s job role(%s) not allowed, expect %s",
			cli.Addr, job.params.Role, consts.MetaRoleRedisMaster)
	}
	repls, err := cli.Info("replication")
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s info replication failed,err:%v", cli.Addr, err)
	}
	role := repls["role"]
	if role != consts.RedisMasterRole {
		return fmt.Errorf("flush after upgrade: addr=%s redis role(%s) not allowed, expect %s",
			cli.Addr, role, consts.RedisMasterRole)
	}
	connectedSlavesStr, ok := repls["connected_slaves"]
	if !ok || connectedSlavesStr == "" {
		return fmt.Errorf("flush after upgrade: addr=%s connected_slaves missing in info replication:%+v",
			cli.Addr, repls)
	}
	connectedSlaves, err := strconv.Atoi(connectedSlavesStr)
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s connected_slaves(%s) invalid,err:%v",
			cli.Addr, connectedSlavesStr, err)
	}
	if connectedSlaves != 0 {
		return fmt.Errorf("flush after upgrade: addr=%s still has %d connected replicas, refuse to flush",
			cli.Addr, connectedSlaves)
	}
	job.runtime.Logger.Info("flush after upgrade safety check passed: addr=%s role=%s connected_slaves=%d",
		cli.Addr, role, connectedSlaves)
	return nil
}

// checkFlushAfterUpgradeResult 与 redis_flush_data.go::RandomKey 的检查保持一致:
// 清档后允许没有 key, 也允许 dbha agent 心跳 key.
func (job *RedisVersionUpdate) checkFlushAfterUpgradeResult(cli *myredis.RedisClient) error {
	key, err := cli.Randomkey()
	if err != nil {
		return fmt.Errorf("flush after upgrade: addr=%s randomkey check failed,err:%v", cli.Addr, err)
	}
	if key != "" && !strings.HasPrefix(key, "dbha:agent:") {
		return fmt.Errorf("flush after upgrade: addr=%s randomkey check failed,key=%s", cli.Addr, key)
	}
	job.runtime.Logger.Info("flush after upgrade result check passed: addr=%s randomkey=%s", cli.Addr, key)
	return nil
}

// waitForLoadingFinish 轮询 INFO persistence 直到 loading=0; 期间容忍 LOADING 错误.
// 用于 startRedis (升级到新版本) 后, 实例仍在加载老 AOF/RDB 时, 等待加载完成再发命令.
func (job *RedisVersionUpdate) waitForLoadingFinish(cli *myredis.RedisClient, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	const sleepInterval = 2 * time.Second
	logged := false
	for {
		info, err := cli.Info("persistence")
		if err != nil {
			// 加载阶段对部分命令也可能返回 LOADING; INFO 一般允许, 但兜底处理一下.
			if !strings.Contains(err.Error(), "LOADING") {
				return fmt.Errorf("wait for loading: addr=%s info persistence err=%v", cli.Addr, err)
			}
		} else if info["loading"] == "0" {
			if logged {
				job.runtime.Logger.Info("wait for loading done: addr=%s, info.loading=%s", cli.Addr, info["loading"])
			}
			return nil
		} else if info["loading"] == "" {
			// loading 字段缺失视为非 cache redis (TendisSSD 没有 in-memory load 阶段), 直接通过.
			job.runtime.Logger.Info("wait for loading: addr=%s loading field absent, assuming non-cache redis", cli.Addr)
			return nil
		} else {
			// 仅在第一次发现仍在 loading 时打日志, 避免轮询期间刷屏.
			if !logged {
				job.runtime.Logger.Info("wait for loading: addr=%s loading=%s eta=%ss",
					cli.Addr, info["loading"], info["loading_eta_seconds"])
				logged = true
			}
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("wait for loading: timeout(%v) addr=%s", timeout, cli.Addr)
		}
		time.Sleep(sleepInterval)
	}
}

// buildFlushAllCmd 选取对应 cluster_type 的 flushall 命令 (rename 后).
// cache 4.0+ 自动追加 ASYNC 以非阻塞清理 (与 redis_flush_data.go::FlushAll 行为一致).
func buildFlushAllCmd(clusterType string, cli *myredis.RedisClient) ([]string, error) {
	switch clusterType {
	case consts.TendisTypeTwemproxyRedisInstance, consts.TendisTypeRedisInstance:
		cmd := []string{consts.CacheFlushAllRename}
		if v, err := cli.GetTendisVersion(); err == nil && v != "" {
			majorStr := strings.SplitN(v, ".", 2)[0]
			if major, convErr := strconv.Atoi(majorStr); convErr == nil && major >= 4 {
				cmd = append(cmd, consts.ASYNC)
			}
		}
		return cmd, nil
	case consts.TendisTypeTwemproxyTendisSSDInstance:
		return []string{consts.SSDFlushAllRename}, nil
	default:
		return nil, fmt.Errorf("unsupported cluster_type(%s)", clusterType)
	}
}

func (job *RedisVersionUpdate) stopRedis(port int) (err error) {
	return stopRedisViaScript(job.params.IP, port, job.runtime.Logger)
}

func (job *RedisVersionUpdate) startRedis(port int) (err error) {
	cli, err := startRedisAndWaitRepl(job.params.IP, port, job.replExpectation(port),
		job.params.Role, syncWaitTimeoutOrDefault(job.params.SyncWaitTimeoutSeconds), job.runtime.Logger)
	if cli != nil {
		if job.AddrMapCli == nil {
			job.AddrMapCli = make(map[string]*myredis.RedisClient)
		}
		job.AddrMapCli[fmt.Sprintf("%s:%d", job.params.IP, port)] = cli
	}
	return wrapSyncWaitErr(err)
}

// markSettled 记下该端口已经收过尾, 末尾的兜底循环据此跳过
func (job *RedisVersionUpdate) markSettled(port int) {
	if job.settledPorts == nil {
		job.settledPorts = make(map[int]bool)
	}
	job.settledPorts[port] = true
}

// settleUnsettledPorts 给还没收过尾的端口钉复制状态并恢复 failover 资格.
//
// 需要它的是那些没进重启循环的端口: 软链和运行版本都已到位(重试场景), 或 old_master
// 升级里 runningOnTargetVersion 直接跳过的那些. 刚重启过的端口在 regenConfAndStartRedis
// 里已经收过尾, 再来一遍只是把同样的日志和 CONFIG GET 重打一次.
func (job *RedisVersionUpdate) settleUnsettledPorts() error {
	for _, port := range job.params.Ports {
		if job.settledPorts[port] {
			continue
		}
		if err := job.ensureInstanceSettled(port); err != nil {
			return err
		}
	}
	return nil
}

// ensureInstanceSettled 拉起后(或重试时进程已在目标版本上)钉死复制状态并按运行态 restore.
func (job *RedisVersionUpdate) ensureInstanceSettled(port int) error {
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	if err := job.ensurePortConnected(port); err != nil {
		return err
	}
	cli := job.AddrMapCli[addr]
	expect := job.replExpectation(port)
	if err := settleReplication(cli, expect, job.params.Role,
		syncWaitTimeoutOrDefault(job.params.SyncWaitTimeoutSeconds), job.runtime.Logger); err != nil {
		return wrapSyncWaitErr(err)
	}
	if err := job.restoreClusterFailoverPermission(port); err != nil {
		return err
	}
	job.markSettled(port)
	return nil
}

// runningOnTargetVersion 端口已占用且运行版本已是目标版本. 重试时据此跳过 stop/regen/挪数据.
func (job *RedisVersionUpdate) runningOnTargetVersion(port int) (bool, error) {
	inUse, err := portInUse(job.params.IP, port)
	if err != nil {
		return false, err
	}
	if !inUse {
		return false, nil
	}
	if err := job.ensurePortConnected(port); err != nil {
		return false, err
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	return job.isRedisRuntimeVersionOK(job.AddrMapCli[addr])
}

func (job *RedisVersionUpdate) ensurePortConnected(port int) error {
	if job.AddrMapCli == nil {
		job.AddrMapCli = make(map[string]*myredis.RedisClient)
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	if job.AddrMapCli[addr] != nil {
		return nil
	}
	cli, err := connectLocalRedis(addr, port, 5*time.Second)
	if err != nil {
		return err
	}
	job.AddrMapCli[addr] = cli
	return nil
}

func (job *RedisVersionUpdate) isRedisRuntimeVersionOK(cli *myredis.RedisClient) (ok bool, err error) {
	repls, err := cli.Info("server")
	if err != nil {
		return false, err
	}
	runtimeBaseVer, runtimeSubVer, err := util.VersionParse(repls["redis_version"])
	if err != nil {
		return false, err
	}
	pkgBaseVer, pkgSubVer, err := util.VersionParse(job.params.GePkgBaseName())
	if err != nil {
		return false, err
	}
	if runtimeBaseVer != pkgBaseVer || runtimeSubVer != pkgSubVer {
		return false, nil
	}
	return true, nil
}

// Retry times
func (job *RedisVersionUpdate) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisVersionUpdate) Rollback() error {
	return nil
}
