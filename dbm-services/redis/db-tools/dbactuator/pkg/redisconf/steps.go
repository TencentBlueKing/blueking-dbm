package redisconf

import (
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// Step 一条有意改写: 在目标版本渲染结果之上做的、有名字的修改.
//
// 目标版本模板只有 dbconfig 那一层, 运行态才有的事实(主从关系、凭据、节点身份)和本次
// 任务的意图(跟随新主、空载起进程)都靠步骤补上. 每一步只管一件事, 顺序由调用方的列表决定.
// 新的历史兼容或新意图加一个步骤并写进对应列表, 不要往 Request 上加开关去分叉已有步骤.
type Step struct {
	Name  string
	apply func(req Request, old Directives, confData string) string
}

// Apply 对 confData 执行这一步, old 取自 req.OldConfData
func (s Step) Apply(req Request, confData string) string {
	return s.apply(req, ParseDirectives(req.OldConfData), confData)
}

var (
	// StepCarryOver 补回只存在于运行态、dbconfig 里没有的指令
	StepCarryOver = Step{Name: "carry-over", apply: func(req Request, old Directives, confData string) string {
		return appendCarryOverDirectives(confData, req.OldConfData, old)
	}}
	// StepCanonicalNodesFile cache cluster 的节点文件统一落在 dir/nodes.conf
	StepCanonicalNodesFile = Step{Name: "canonical-nodes-file", apply: Request.canonicalNodesFile}
	// StepReplicaOf 把上游指定的新主库写成 replicaof
	StepReplicaOf = Step{Name: "replicaof", apply: Request.applyReplicaOf}
	// StepClusterNoFailover 空载起进程期间禁止 cluster 节点被选为新主
	StepClusterNoFailover = Step{Name: "cluster-no-failover", apply: Request.applyClusterNoFailover}
	// StepAlignMasterAuth 改密码且主库已经换好时, masterauth 跟到新密码
	StepAlignMasterAuth = Step{Name: "align-masterauth", apply: Request.alignMasterAuthWithPassword}
	// StepMasterAuthForReplica 声明了从库身份的配置必须带一份能用的 masterauth
	StepMasterAuthForReplica = Step{Name: "masterauth-for-replica", apply: Request.ensureMasterAuthForReplica}
	// StepAppendonlyForReplica old_master 建成 new_slave 时开 AOF
	StepAppendonlyForReplica = Step{Name: "appendonly-for-replica", apply: Request.applyAppendonlyForReplica}
)

// UpgradeSteps 版本升级: 可以改拓扑(sync_masters)、可以空载起进程, 不改密码
var UpgradeSteps = []Step{
	StepCarryOver,
	StepCanonicalNodesFile,
	StepReplicaOf,
	StepClusterNoFailover,
	StepMasterAuthForReplica,
	StepAppendonlyForReplica,
}

// RefreshSteps 配置刷新: 拓扑保持停机前快照、不挪数据, 可以改密码
var RefreshSteps = []Step{
	StepCarryOver,
	StepCanonicalNodesFile,
	StepAlignMasterAuth,
	StepMasterAuthForReplica,
}

// carryOverDirectives 只存在于运行态、dbconfig 中没有的指令.
// 目标版本配置渲染完成后, 若渲染结果里没有这些指令, 需要从旧配置文件补回来.
//
//	masterauth: 丢了主从同步会认证失败
//
// 旧配置文件里也没有 masterauth 时这里无从抄起, 由 ensureMasterAuthForReplica 兜底.
//
// replicaof/slaveof 不在这里: 它们是同一指令的两种写法, 必须当成一个整体补写,
// 逐名补会写出两条指向不同主库的行, 见 appendCarryOverDirectives.
var carryOverDirectives = []string{"masterauth"}

// appendCarryOverDirectives 把只存在于运行态的指令补到渲染结果末尾
func appendCarryOverDirectives(confData string, oldConfData string, oldDirectives Directives) string {
	newDirectives := ParseDirectives(confData)
	appended := strings.Builder{}
	for _, name := range carryOverDirectives {
		if newDirectives.Has(name) {
			continue
		}
		value := oldDirectives.LastValue(name)
		if value == "" || strings.EqualFold(value, "no one") {
			continue
		}
		appended.WriteString(name)
		appended.WriteByte(' ')
		appended.WriteString(value)
		appended.WriteByte('\n')
	}
	// 主从关系整体补一条: 只要渲染结果里已经有任意一种写法就不再追加, 否则
	// 会同时写出 replicaof 和 slaveof 两行, 而 redis 只认最后一行, 等于随机挑了个主库
	if _, newRepl := EffectiveReplicationOf(confData); newRepl == "" {
		if oldName, oldValue := EffectiveReplicationOf(oldConfData); oldValue != "" {
			appended.WriteString(oldName) // 沿用旧文件的写法: redis 5.0 以下不认 replicaof
			appended.WriteByte(' ')
			appended.WriteString(oldValue)
			appended.WriteByte('\n')
		}
	}
	if appended.Len() == 0 {
		return confData
	}
	if !strings.HasSuffix(confData, "\n") {
		confData += "\n"
	}
	return confData + appended.String()
}

// canonicalNodesFile 去掉渲染结果里的 cluster-config-file, 节点文件回到默认的 dir/nodes.conf.
//
// 节点身份不能随模板丢: 旧配置若用 cluster-config-file 指向了别的文件, 文件本身由
// Plan 的 NodesMove 在停机后复制到 nodes.conf, 见 planNodesFileMove. 这里只负责让新配置
// 不再声明它 —— dbconfig 里即便写着 cluster-config-file nodes.conf, 也和缺省等价.
func (req Request) canonicalNodesFile(old Directives, confData string) string {
	if !hasNodesFile(req.ClusterType) {
		return confData
	}
	if !ParseDirectives(confData).Has(clusterConfigFileDirective) && !old.Has(clusterConfigFileDirective) {
		return confData
	}
	if old.Has(clusterConfigFileDirective) {
		req.Logger.Info("port(%d) old conf declares %s %s,regenerated conf drops it for the default %s",
			req.Port, clusterConfigFileDirective, old.LastValue(clusterConfigFileDirective), defaultNodesFile)
	}
	return StripDirectives(confData, []string{clusterConfigFileDirective})
}

// applyReplicaOf 把"升级后应达成的主从关系"写进配置文件.
//
// old_master 升级后要作为 new_slave 跟随 new_master. 与其起来之后再单独发一次 replicaof,
// 不如让它带着 replicaof 起来: 少一个"进程已经起来、但还没建立同步"的中间态,
// 上游也就不再需要一个独立的建同步子流程.
//
// cluster 架构不写 replicaof: 主从关系由 nodes.conf 维护, redis 的 config rewrite 也不写它.
func (req Request) applyReplicaOf(_ Directives, confData string) string {
	if consts.IsClusterDbType(req.ClusterType) || !req.Expect.Wanted {
		return confData
	}
	name := "slaveof"
	if UsesReplicaSpelling(req.PkgBaseName) {
		name = "replicaof"
	}
	confData = StripDirectives(confData, ReplicationDirectiveNames)
	req.Logger.Info("port(%d) conf will replicate from %s after upgrade", req.Port, req.Expect.MasterAddr())
	return AppendDirective(confData, name, req.Expect.ConfReplTarget())
}

// applyClusterNoFailover 空载起进程期间禁止本节点被选为新主.
//
// cluster 架构自带自动 failover: 一个刚被清空、还在全量同步的从库若此时被选上,
// 它负责的那些 slot 会连带数据一起变空, 而且没有任何报错.
// 同步完成后由调用方按运行态改回去.
func (req Request) applyClusterNoFailover(_ Directives, confData string) string {
	if !consts.IsClusterDbType(req.ClusterType) || !req.DiscardLocalData {
		return confData
	}
	name := "cluster-slave-no-failover"
	if UsesReplicaSpelling(req.PkgBaseName) {
		name = "cluster-replica-no-failover"
	}
	confData = StripDirectives(confData, ClusterNoFailoverDirectiveNames)
	req.Logger.Info("port(%d) conf sets %s yes while syncing from scratch", req.Port, name)
	return AppendDirective(confData, name, "yes")
}

// alignMasterAuthWithPassword 改密码时把 masterauth 一并挪到新密码上.
//
// 只在上游探到主库确实已经在用新密码时才做(MasterAuthFollowsPassword). 渲染自己看不见对端,
// 判断不了主库改到哪一步了; 提前挪过去, 从库下次重连就会拿新密码去 AUTH 一台还是旧密码的主库.
//
// ensureMasterAuthForReplica 只管"声明了从库身份"的实例, 这里连主库也要管: 主库配置里同样
// 可能留着一条 masterauth(carry-over 抄来的, 或它曾经当过从库), 不换掉的话这台主库下次被切成
// 从库时就会拿旧密码去 AUTH.
func (req Request) alignMasterAuthWithPassword(_ Directives, confData string) string {
	if !req.MasterAuthFollowsPassword || consts.IsClusterDbType(req.ClusterType) {
		return confData
	}
	directives := ParseDirectives(confData)
	if !directives.Has("masterauth") {
		// 本来就没有凭据可挪. 该不该凭空加一条由 ensureMasterAuthForReplica 按从库身份决定
		return confData
	}
	// 沿用渲染结果里 requirepass 的原文(含引号): 两处同源同写法, 下一次比对才不会
	// 因为引号差异显得像变更
	rawPass := directives.LastValue("requirepass")
	if Unquote(rawPass) == Unquote(directives.LastValue("masterauth")) {
		return confData
	}
	req.Logger.Info("port(%d) conf moves masterauth onto the new password,the master already runs it", req.Port)
	confData = StripDirectives(confData, []string{"masterauth"})
	return AppendDirective(confData, "masterauth", rawPass)
}

// ensureMasterAuthForReplica 保证"声明了从库身份"的配置文件带着一份能用的 masterauth.
//
// 只看"这份配置是不是声明了从库身份", 不看那条 replicaof 是谁写进去的: old_slave 升级时
// config rewrite 静默失败过的现场同样会缺 masterauth, 那是同一个洞的另一半.
//
// cluster 架构不碰: 主从关系在 nodes.conf 里, 切换时 redis_switch 的 trySetMasterAuth 与
// redis_cluster_failover 的 allClusterMastersConfSetMasterauth 已经 config set + rewrite 过,
// carry-over 抄得到; 而且 cluster 端口未必下发目标版本配置, 在这里补也覆盖不全, 不如维持单一来源.
//
// 改密码时同样不特殊照顾: 已有的 masterauth 一律留着不动. 渲染只看得见本机, 判断不了
// 对端主库改到哪一步了, 换早了从库下次重连就 AUTH 失败. 该不该跟到新密码由
// StepAlignMasterAuth 按调用方的探测结论决定.
func (req Request) ensureMasterAuthForReplica(_ Directives, confData string) string {
	if consts.IsClusterDbType(req.ClusterType) {
		return confData
	}
	if _, replTarget := EffectiveReplicationOf(confData); replTarget == "" {
		return confData
	}
	directives := ParseDirectives(confData)
	// 沿用渲染结果里 requirepass 的原文(含引号): 两处同源同写法, 下一次比对才不会
	// 因为引号差异显得像变更
	rawPass := directives.LastValue("requirepass")
	password := Unquote(rawPass)
	if password == "" {
		return confData // 无密码集群, 写一条 masterauth "" 没有意义
	}
	// config rewrite 对空密码实例写出的是 masterauth "", 指令在但取值是空的,
	// 所以要按去引号后的值判断, 不能只看指令存不存在
	current := Unquote(directives.LastValue("masterauth"))
	if current == password {
		return confData
	}
	if current != "" && !req.Expect.Wanted {
		// 本次不改变它跟谁, 那条凭据就轮不到这里做主
		req.Logger.Warn("port(%d) conf declares replication but its masterauth differs from requirepass,left as is",
			req.Port)
		return confData
	}
	if current != "" {
		// old_master 曾经当过从库, 留下的 masterauth 指向旧密码, 而它马上要跟随新主
		req.Logger.Info("port(%d) conf replaces a stale masterauth with requirepass", req.Port)
	} else {
		req.Logger.Info("port(%d) conf gets masterauth so replication can authenticate", req.Port)
	}
	confData = StripDirectives(confData, []string{"masterauth"})
	return AppendDirective(confData, "masterauth", rawPass)
}

// applyAppendonlyForReplica 只在版本升级把 old_master 建成 new_slave 时开 AOF.
//
// dbconfig 只有 plat/app/cluster 一层, appendonly 默认是 master 口径 no.
// 以前靠 replicaof 原子任务 CONFIG SET; 升级改成把 replicaof 写进配置文件之后,
// 那次 SET 不再跑, 从库 conf 里就留下 no.
//
// 不能看到 replicaof 就写 yes: old_slave 升级时 conf 里本来就有 replicaof,
// 但紧接着可能被切成 new_master, 这里写 yes 会让它带着 AOF 升主.
// 用 Expect.Wanted 区分 "sync_masters 指定的新拓扑"(new-slave) 和
// "停机前快照"(old-slave 角色不变).
//
// 非 cache (Tendisplus/SSD) 不碰: CreateReplicaREL 本来就不会给它们改 appendonly.
// libB2RedisModule 必须关 AOF, 再写 yes 会盖掉 BuildTemplate 的 appendonly no.
func (req Request) applyAppendonlyForReplica(_ Directives, confData string) string {
	if req.ClusterType != "" && !consts.IsRedisInstanceDbType(req.ClusterType) {
		return confData
	}
	if confHasB2Module(confData) {
		return confData
	}
	if !req.Expect.Wanted || !req.Expect.IsSlave() {
		return confData
	}
	current := strings.ToLower(Unquote(ParseDirectives(confData).LastValue("appendonly")))
	if confTruthy(current) {
		return confData
	}
	req.Logger.Info("port(%d) conf sets appendonly yes so new slave persists via aof", req.Port)
	confData = StripDirectives(confData, []string{"appendonly"})
	return AppendDirective(confData, "appendonly", "yes")
}
