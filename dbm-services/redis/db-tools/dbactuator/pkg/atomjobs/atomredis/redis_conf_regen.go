package atomredis

import (
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisConfRenderItem 单个端口的目标版本配置, 由 dbm 侧按集群算好后下发.
//
// 主从版架构下同一台机器的端口可能分属不同集群, 各自域名/dbconfig 不同,
// 所以按端口下发而不是按主机下发.
type RedisConfRenderItem struct {
	ConfConfigs       map[string]string `json:"conf_configs"`
	Databases         int               `json:"databases"`
	LoadModulesDetail []LoadModuleItem  `json:"load_modules_detail"`
}

// confDirectives 配置文件中 指令名(小写) -> 该指令出现的所有取值(按文件顺序)
type confDirectives map[string][]string

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

// parseRedisConfDirectives 解析 redis 配置文件.
//
// 只做 "取出某指令的取值" 用途, 不能用它把配置文件还原成 map 再和 dbconfig 逐 key 比较:
// rename-command / client-output-buffer-limit / save 这类指令在文件中是多行的,
// 而在 dbconfig 里是一个配置项(值内嵌换行), 两者形状不同。
func parseRedisConfDirectives(confData string) confDirectives {
	directives := make(confDirectives)
	for _, line := range strings.Split(confData, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.SplitN(line, " ", 2)
		key := strings.ToLower(strings.TrimSpace(fields[0]))
		value := ""
		if len(fields) > 1 {
			value = strings.TrimSpace(fields[1])
		}
		directives[key] = append(directives[key], value)
	}
	return directives
}

// lastValue 取指令最后一次出现的值; config rewrite 会追加写, 以最后一次为准
func (d confDirectives) lastValue(key string) string {
	values := d[key]
	if len(values) == 0 {
		return ""
	}
	return values[len(values)-1]
}

func (d confDirectives) has(key string) bool {
	return len(d[key]) > 0
}

// replicationDirectiveNames replicaof/slaveof: 同一指令在不同版本下的两种写法
var replicationDirectiveNames = []string{"replicaof", "slaveof"}

// clusterNoFailoverDirectiveNames "禁止本节点被选为新主"在不同版本下的两种写法
var clusterNoFailoverDirectiveNames = []string{"cluster-replica-no-failover", "cluster-slave-no-failover"}

// replicaSpellingSinceVersion replica 系列写法(replicaof / cluster-replica-*)从 redis 5.0 开始才有
const replicaSpellingSinceVersion = 5000000

// usesReplicaSpelling 目标版本是否认 replica 系列写法.
//
// 解析不出版本时按"不认"处理: slave 系列写法所有版本都认, 反之会让实例起不来.
// tendisplus / TendisSSD 基于 4.x 以下内核, 解析出来的主版本也落在这一侧.
func usesReplicaSpelling(pkgBaseName string) bool {
	baseVer, _, err := util.VersionParse(pkgBaseName)
	if err != nil {
		return false
	}
	return baseVer >= replicaSpellingSinceVersion
}

// stripConfDirectives 删掉配置文件里所有名为 names 之一的生效行, 注释行原样保留.
//
// 用于"覆盖一条配置项": 只往末尾追加的话, redis 行为是对的(以最后一条为准),
// 但文件里会同时留着两条指向不同主库的 replicaof, 之后任何人或任何工具读它都会读错.
func stripConfDirectives(confData string, names []string) string {
	lines := strings.Split(confData, "\n")
	kept := make([]string, 0, len(lines))
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && !strings.HasPrefix(trimmed, "#") {
			fields := strings.SplitN(trimmed, " ", 2)
			if slices.Contains(names, strings.ToLower(strings.TrimSpace(fields[0]))) {
				continue
			}
		}
		kept = append(kept, line)
	}
	return strings.Join(kept, "\n")
}

// appendConfDirective 在配置文件末尾写一条配置项
func appendConfDirective(confData, name, value string) string {
	if confData != "" && !strings.HasSuffix(confData, "\n") {
		confData += "\n"
	}
	return confData + name + " " + value + "\n"
}

// effectiveReplicationOf 返回配置文件中最后生效的 replicaof/slaveof 取值,
// 没有主从关系时返回空.
//
// slaveof 与 replicaof 是同一指令的两种写法, redis 以文件中最后一次出现为准,
// 所以必须按行序判断: 旧配置文件可能同时有 redis_replicaof 原子任务追加的 slaveof
// 和之后 config rewrite 写的 replicaof, 按指令名优先级取值会和 redis 的实际行为相反,
// 也就看不出实例其实跟了另一台主.
//
// 返回的 name 是文件里原本用的写法, 补写时必须沿用: redis 5.0 以下不认 replicaof.
func effectiveReplicationOf(confData string) (name string, value string) {
	for _, line := range strings.Split(confData, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.SplitN(line, " ", 2)
		lineName := strings.ToLower(strings.TrimSpace(fields[0]))
		if !slices.Contains(replicationDirectiveNames, lineName) {
			continue
		}
		lineValue := ""
		if len(fields) > 1 {
			lineValue = strings.TrimSpace(fields[1])
		}
		// slaveof no one 是"取消主从", 和没有这条指令等价, 但它同样会覆盖前面的取值
		if lineValue == "" || strings.EqualFold(lineValue, "no one") {
			name, value = "", ""
			continue
		}
		name, value = lineName, lineValue
	}
	return name, value
}

// diskLoadModules 从旧配置文件的 loadmodule 行还原 module 列表.
// 用于 dbm 侧没有下发 module 信息时兜底, 避免升级后实例少加载 module.
func diskLoadModules(directives confDirectives) []LoadModuleItem {
	items := make([]LoadModuleItem, 0, len(directives["loadmodule"]))
	for _, soPath := range directives["loadmodule"] {
		soPath = strings.TrimSpace(soPath)
		if soPath == "" {
			continue
		}
		items = append(items, LoadModuleItem{SoFile: filepath.Base(soPath)})
	}
	return items
}

// confRegenRequest 一次配置文件重建所需的全部事实.
//
// 显式携带而不是从原子任务参数里现读: 重建配置这件事本身与具体原子任务无关.
// 每个任务自己的 regenRequest 负责映射; 渲染 + 校验链路只认这一组事实.
type confRegenRequest struct {
	IP   string
	Port int
	// PkgBaseName 实例即将运行的版本包名, 形如 redis-6.2.7.
	//
	// 版本升级填目标介质包名 (MediaPkg.GePkgBaseName); 不换二进制的任务填
	// /usr/local/redis 软链当前指向的包名 (readLocalRedisPkgBaseName 的做法).
	// 它决定写 replicaof 还是 slaveof、cluster-replica-* 还是 cluster-slave-*,
	// 填错实例直接起不来.
	PkgBaseName string
	ClusterType string
	// InstCount 本机实例个数, tendisplus 的 blockcache / write buffer 按实例数分摊
	InstCount uint64
	// Item 目标版本的配置项, 由 dbm 侧按集群算好后下发
	Item RedisConfRenderItem
	// Expect 重建后这个实例应达成的复制状态, 取值见 replSnapshot
	Expect replSnapshot
	// DiscardLocalData 本次是否空载起进程; cluster 架构据此决定要不要暂时禁掉自动 failover
	DiscardLocalData bool
	// TargetPassword 本次要改成的密码. nil 表示不改密码, 沿用磁盘上的 requirepass.
	//
	// 非 nil 时它才是 {{password}} 的取值, 且允许与磁盘不同 —— 这是唯一一条能让
	// requirepass 变化的通道. 空串是合法目标(无密码集群), 所以必须用指针区分
	// "没下发" 和 "下发了空密码".
	TargetPassword *string
	// MasterAuthFollowsPassword 改密码时是否把 masterauth 一并挪到新密码上.
	//
	// 由调用方探过主库之后置位(见 RedisConfRefresh.resolveMasterAuthTargets): 只有主库确实
	// 已经在用新密码才为 true. 渲染自己看不见对端, 判断不了主库改到哪一步了, 所以默认 false
	// 也就是"凭据原样留着" —— 现存链路不会当场断, 大不了下一趟再跟上.
	MasterAuthFollowsPassword bool
	// ConfFile / OldConfData 磁盘上的现状, 由 loadRegenInput 读好后填入.
	//
	// 文件 IO 留在调用方: 渲染与校验因此是纯函数, 调用方也能自己决定从哪读
	ConfFile    string
	OldConfData string
	Logger      *logger.Logger
}

// regenConfPlan 渲染并校验通过、但还没落盘的一次配置重建
type regenConfPlan struct {
	confFile    string
	oldConfData string
	confData    string
}

// loadRegenInput 读取待重建端口在磁盘上的现状
func loadRegenInput(port int) (confFile string, oldConfData string, err error) {
	confFile, err = getRedisConfFileForRegen(port)
	if err != nil {
		return "", "", err
	}
	oldBytes, err := os.ReadFile(confFile)
	if err != nil {
		return "", "", fmt.Errorf("read redis conf(%s) failed,err:%v", confFile, err)
	}
	return confFile, string(oldBytes), nil
}

// buildRegenPlan 组装一次重建请求并跑完渲染与校验.
//
// 该端口没有下发目标配置时返回 (nil, nil), 是否算错误由调用方决定:
// 版本升级保持"只换二进制"的旧行为; 配置刷新在 Init 已保证每端口都有配置.
func buildRegenPlan(req confRegenRequest, item RedisConfRenderItem, delivered bool) (*regenConfPlan, error) {
	if !delivered || len(item.ConfConfigs) == 0 {
		return nil, nil
	}
	confFile, oldConfData, err := loadRegenInput(req.Port)
	if err != nil {
		return nil, err
	}
	req.Item = item
	req.ConfFile = confFile
	req.OldConfData = oldConfData
	return req.buildPlan()
}

// buildPlan 渲染目标版本配置并校验, 不写任何文件.
//
// 做法是 "以目标版本渲染结果为基准, 再把只存在于运行态的取值搬过来",
// 而不是拿旧文件做逐 key 覆盖 —— 见 parseRedisConfDirectives 的说明.
// 目标版本已经删掉的指令因此自然消失, 这正是新版本进程起不来的根因所在.
func (req confRegenRequest) buildPlan() (*regenConfPlan, error) {
	oldDirectives := parseRedisConfDirectives(req.OldConfData)
	confData, err := req.renderTargetConf(oldDirectives)
	if err != nil {
		return nil, err
	}
	if err = req.validateRegenConf(confData, oldDirectives); err != nil {
		return nil, err
	}
	return &regenConfPlan{confFile: req.ConfFile, oldConfData: req.OldConfData, confData: confData}, nil
}

// writeRegenConfPlan 把已校验过的渲染结果落盘, 先备份旧文件.
// 备份路径打进日志, 调用方需要回滚时自己记; 本函数不负责回滚.
func writeRegenConfPlan(plan *regenConfPlan, port int, log *logger.Logger) (backupFile string, err error) {
	log.Info("port(%d) conf regenerate diff:\n%s",
		port, diffRedisConfDirectives(plan.oldConfData, plan.confData))
	backupFile, err = backupRedisConfFile(plan.confFile, []byte(plan.oldConfData))
	if err != nil {
		return "", err
	}
	if err = writeRedisConfFile(plan.confFile, []byte(plan.confData)); err != nil {
		return "", err
	}
	log.Info("port(%d) conf regenerated,conf:%s,backup:%s", port, plan.confFile, backupFile)
	return backupFile, nil
}

// getRedisConfFileForRegen 定位待重建的配置文件.
//
// 只认 redis.conf: instance.conf 是老部署方式留下的, config rewrite 写的是 redis.conf,
// 重建 instance.conf 既无意义也有风险.
func getRedisConfFileForRegen(port int) (string, error) {
	confFile := filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(port), "redis.conf")
	if !util.FileExists(confFile) {
		return "", fmt.Errorf("redis conf(%s) not exists", confFile)
	}
	return confFile, nil
}

// instDirForRegen 决定渲染时 {{redis_data_dir}} 用哪个写法.
//
// 以旧配置里 dir 已经生效的写法为准, 而不是 consts.GetRedisDataDir() 的探测结果:
// 探测只要看到 /data1/redis 就返回 /data1, 而 /data1 可能只是 /data 的软链,
// 于是重建后 dir 从 /data/redis/30000/data 变成 /data1/redis/30000/data,
// 看起来像把数据目录搬了家(校验会拦), logfile/pidfile 也会跟着换写法.
func (req confRegenRequest) instDirForRegen(oldDirectives confDirectives) string {
	fallback := filepath.Dir(req.ConfFile)
	oldDir := unquoteConfValue(oldDirectives.lastValue("dir"))
	if oldDir == "" || !filepath.IsAbs(oldDir) {
		return fallback
	}
	// dir 形如 /data/redis/30000/data (cache) 或 /data/redis/30000/data/db (tendisplus),
	// 截到 /redis/<port> 即实例目录
	marker := "/redis/" + strconv.Itoa(req.Port)
	cleaned := filepath.Clean(oldDir)
	idx := strings.LastIndex(cleaned, marker)
	if idx < 0 {
		req.Logger.Warn("port(%d) old conf dir(%s) not under %s,use %s as inst dir",
			req.Port, oldDir, marker, fallback)
		return fallback
	}
	instDir := cleaned[:idx+len(marker)]
	if instDir != fallback {
		req.Logger.Info("port(%d) keep inst dir %s from old conf(conf file located at %s)",
			req.Port, instDir, fallback)
	}
	return instDir
}

// renderedPassword 渲染时 {{password}} 该用的取值.
//
// 默认以磁盘配置为准: 与密码服务取值不一致时, 用磁盘值才不会在升级过程中把认证和主从同步搞坏.
// 只有上游显式下发了目标密码(改密码单据)才用它 —— 这是唯一一条能让 requirepass 变化的通道.
func (req confRegenRequest) renderedPassword(oldDirectives confDirectives) string {
	if req.TargetPassword != nil {
		return *req.TargetPassword
	}
	return unquoteConfValue(oldDirectives.lastValue("requirepass"))
}

// passwordChanging 本次是否真的会把 requirepass 从磁盘上的取值改掉.
//
// 下发的目标密码与磁盘一致时不算改密码: 那些"改密码才放行"的分支应保持保守行为.
func (req confRegenRequest) passwordChanging(oldDirectives confDirectives) bool {
	if req.TargetPassword == nil {
		return false
	}
	return *req.TargetPassword != unquoteConfValue(oldDirectives.lastValue("requirepass"))
}

// renderTargetConf 渲染目标版本配置, 并补回只存在于运行态的指令
func (req confRegenRequest) renderTargetConf(oldDirectives confDirectives) (string, error) {
	instDir := req.instDirForRegen(oldDirectives)
	password := req.renderedPassword(oldDirectives)
	modules := req.Item.LoadModulesDetail
	if len(modules) == 0 {
		modules = diskLoadModules(oldDirectives)
		if len(modules) > 0 {
			req.Logger.Warn("port(%d) no module delivered,fallback to %d module(s) found in old conf",
				req.Port, len(modules))
		}
	}
	databases := req.Item.Databases
	if databases <= 0 {
		if old, parseErr := strconv.Atoi(unquoteConfValue(oldDirectives.lastValue("databases"))); parseErr == nil && old > 0 {
			databases = old
		} else {
			databases = 2
		}
	}
	tmpl := BuildRedisConfTemplate(req.Item.ConfConfigs, modules, req.PkgBaseName)
	renderValues, err := RedisConfRenderParams{
		IP:        req.IP,
		Port:      req.Port,
		Password:  password,
		Databases: databases,
		InstDir:   instDir,
		DbType:    req.ClusterType,
		// maxmemory 由 dbmon 动态设置并被 config rewrite 落盘, 必须沿用磁盘上的值,
		// 否则升级后实例内存上限被清零
		MaxMemory: oldDirectives.lastValue("maxmemory"),
		InstCount: req.InstCount,
	}.Resolve()
	if err != nil {
		return "", err
	}
	confData := RenderRedisConfData(tmpl, renderValues)
	confData = appendCarryOverDirectives(confData, req.OldConfData, oldDirectives)
	confData = req.applyReplExpectationToConf(confData)
	confData = req.alignMasterAuthWithPassword(confData)
	return req.ensureMasterAuthForReplica(confData), nil
}

// alignMasterAuthWithPassword 改密码时把 masterauth 一并挪到新密码上.
//
// 只在上游探到主库确实已经在用新密码时才做(MasterAuthFollowsPassword). 渲染自己看不见对端,
// 判断不了主库改到哪一步了; 提前挪过去, 从库下次重连就会拿新密码去 AUTH 一台还是旧密码的主库.
//
// ensureMasterAuthForReplica 只管"声明了从库身份"的实例, 这里连主库也要管: 主库配置里同样
// 可能留着一条 masterauth(carry-over 抄来的, 或它曾经当过从库), 不换掉的话这台主库下次被切成
// 从库时就会拿旧密码去 AUTH.
func (req confRegenRequest) alignMasterAuthWithPassword(confData string) string {
	if !req.MasterAuthFollowsPassword || consts.IsClusterDbType(req.ClusterType) {
		return confData
	}
	directives := parseRedisConfDirectives(confData)
	if !directives.has("masterauth") {
		// 本来就没有凭据可挪. 该不该凭空加一条由 ensureMasterAuthForReplica 按从库身份决定
		return confData
	}
	// 沿用渲染结果里 requirepass 的原文(含引号): 两处同源同写法, 下一次比对才不会
	// 因为引号差异显得像变更
	rawPass := directives.lastValue("requirepass")
	if unquoteConfValue(rawPass) == unquoteConfValue(directives.lastValue("masterauth")) {
		return confData
	}
	req.Logger.Info("port(%d) conf moves masterauth onto the new password,the master already runs it", req.Port)
	confData = stripConfDirectives(confData, []string{"masterauth"})
	return appendConfDirective(confData, "masterauth", rawPass)
}

// applyReplExpectationToConf 把"升级后应达成的主从关系"写进配置文件.
//
// old_master 升级后要作为 new_slave 跟随 new_master. 与其起来之后再单独发一次 replicaof,
// 不如让它带着 replicaof 起来: 少一个"进程已经起来、但还没建立同步"的中间态,
// 上游也就不再需要一个独立的建同步子流程.
//
// cluster 架构不写 replicaof: 主从关系由 nodes.conf 维护, redis 的 config rewrite 也不写它.
func (req confRegenRequest) applyReplExpectationToConf(confData string) string {
	if consts.IsClusterDbType(req.ClusterType) {
		return req.applyClusterNoFailoverToConf(confData)
	}
	if !req.Expect.wanted {
		return confData
	}
	name := "slaveof"
	if usesReplicaSpelling(req.PkgBaseName) {
		name = "replicaof"
	}
	confData = stripConfDirectives(confData, replicationDirectiveNames)
	req.Logger.Info("port(%d) conf will replicate from %s after upgrade", req.Port, req.Expect.masterAddr())
	return appendConfDirective(confData, name, req.Expect.confReplTarget())
}

// applyClusterNoFailoverToConf 空载起进程期间禁止本节点被选为新主.
//
// cluster 架构自带自动 failover: 一个刚被清空、还在全量同步的从库若此时被选上,
// 它负责的那些 slot 会连带数据一起变空, 而且没有任何报错.
// 同步完成后由 restoreClusterFailoverPermission 改回去.
func (req confRegenRequest) applyClusterNoFailoverToConf(confData string) string {
	if !req.DiscardLocalData {
		return confData
	}
	name := "cluster-slave-no-failover"
	if usesReplicaSpelling(req.PkgBaseName) {
		name = "cluster-replica-no-failover"
	}
	confData = stripConfDirectives(confData, clusterNoFailoverDirectiveNames)
	req.Logger.Info("port(%d) conf sets %s yes while syncing from scratch", req.Port, name)
	return appendConfDirective(confData, name, "yes")
}

// ensureMasterAuthForReplica 保证"声明了从库身份"的配置文件带着一份能用的 masterauth.
//
// 只看"这份配置是不是声明了从库身份", 不看那条 replicaof 是谁写进去的: old_slave 升级时
// config rewrite 静默失败过的现场同样会缺 masterauth, 那是同一个洞的另一半.
//
// cluster 架构不碰: 主从关系在 nodes.conf 里, 切换时 redis_switch 的 trySetMasterAuth 与
// redis_cluster_failover 的 allClusterMastersConfSetMasterauth 已经 config set + rewrite 过,
// carry-over 抄得到; 而且 cluster 端口未必下发目标版本配置(见 precheckSyncMasters),
// 在这里补也覆盖不全, 不如维持单一来源.
//
// 改密码时同样不特殊照顾: 已有的 masterauth 一律留着不动. 渲染只看得见本机, 判断不了
// 对端主库改到哪一步了, 换早了从库下次重连就 AUTH 失败. 该不该跟到新密码由
// followMasterAuth 在运行时探过主库之后决定.
func (req confRegenRequest) ensureMasterAuthForReplica(confData string) string {
	if consts.IsClusterDbType(req.ClusterType) {
		return confData
	}
	if _, replTarget := effectiveReplicationOf(confData); replTarget == "" {
		return confData
	}
	directives := parseRedisConfDirectives(confData)
	// 沿用渲染结果里 requirepass 的原文(含引号): 两处同源同写法, 下一次比对才不会
	// 因为引号差异显得像变更
	rawPass := directives.lastValue("requirepass")
	password := unquoteConfValue(rawPass)
	if password == "" {
		return confData // 无密码集群, 写一条 masterauth "" 没有意义
	}
	// config rewrite 对空密码实例写出的是 masterauth "", 指令在但取值是空的,
	// 所以要按去引号后的值判断, 不能只看指令存不存在
	current := unquoteConfValue(directives.lastValue("masterauth"))
	if current == password {
		return confData
	}
	if current != "" && !req.Expect.wanted {
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
	confData = stripConfDirectives(confData, []string{"masterauth"})
	return appendConfDirective(confData, "masterauth", rawPass)
}

// unquoteConfValue 去掉 config rewrite 给字符串取值加的引号
func unquoteConfValue(value string) string {
	value = strings.TrimPrefix(value, "\"")
	return strings.TrimSuffix(value, "\"")
}

// resolvePathSymlinks 解析路径中的软链, 用于判断两个写法不同的路径是否落在同一处.
// 路径本身还不存在时逐级向上找到存在的祖先, 再把剩余部分拼回去.
func resolvePathSymlinks(path string) string {
	path = filepath.Clean(path)
	if resolved, err := filepath.EvalSymlinks(path); err == nil {
		return resolved
	}
	parent, rest := path, ""
	for {
		next := filepath.Dir(parent)
		if next == parent {
			return path
		}
		rest = filepath.Join(filepath.Base(parent), rest)
		parent = next
		if resolved, err := filepath.EvalSymlinks(parent); err == nil {
			return filepath.Join(resolved, rest)
		}
	}
}

// samePathValue 判断配置文件里两个路径取值是否指向同一位置.
//
// 要同时容忍两件事: config rewrite 给取值加的引号, 以及 /data1 -> /data 这类软链.
// 同一个目录的两种写法不能被当成 "把数据目录搬走了".
func samePathValue(a, b string) bool {
	a = unquoteConfValue(strings.TrimSpace(a))
	b = unquoteConfValue(strings.TrimSpace(b))
	if a == b {
		return true
	}
	if a == "" || b == "" {
		return false
	}
	if filepath.Clean(a) == filepath.Clean(b) {
		return true
	}
	return resolvePathSymlinks(a) == resolvePathSymlinks(b)
}

// appendCarryOverDirectives 把只存在于运行态的指令补到渲染结果末尾
func appendCarryOverDirectives(confData string, oldConfData string, oldDirectives confDirectives) string {
	newDirectives := parseRedisConfDirectives(confData)
	appended := strings.Builder{}
	for _, name := range carryOverDirectives {
		if newDirectives.has(name) {
			continue
		}
		value := oldDirectives.lastValue(name)
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
	if _, newRepl := effectiveReplicationOf(confData); newRepl == "" {
		if oldName, oldValue := effectiveReplicationOf(oldConfData); oldValue != "" {
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

// validateRegenConf 写入前的兜底校验; 任一项不过就不写配置文件, 直接报错.
// 调用方会在停实例之前先跑一遍 buildPlan, 所以正常情况下报错时实例还都在跑.
func (req confRegenRequest) validateRegenConf(confData string, oldDirectives confDirectives) error {
	port, confFile := req.Port, req.ConfFile
	if err := CheckUnresolvedPlaceholder(confData); err != nil {
		return fmt.Errorf("port(%d) conf(%s) %v", port, confFile, err)
	}
	newDirectives := parseRedisConfDirectives(confData)

	// 必备指令: 缺 port/dir 说明下发的不是完整一份配置(同版本升级、版本降级场景
	// dbm 侧只继承 maxmemory 这类少量配置项), 拿它重建只会写出一份空壳配置
	for _, name := range []string{"port", "dir"} {
		if !newDirectives.has(name) {
			return fmt.Errorf(
				"port(%d) regenerated conf missing directive %q,delivered conf is not a complete redis.conf",
				port, name)
		}
	}
	if newDirectives.lastValue("port") != strconv.Itoa(port) {
		return fmt.Errorf("port(%d) regenerated conf port=%q mismatch",
			port, newDirectives.lastValue("port"))
	}
	// 密码默认不允许变化(空密码实例也算): 变了就连不上, 主从也会认证失败.
	//
	// 按"指令缺失等同于空密码"对称比较, 不能只在旧文件有 requirepass 时才比:
	// 旧文件没有而目标版本配置引入一个, 同样会让 proxy / dbmon / dbha 连不上,
	// 而重启后的实例自己用新配置里的密码, 表面上一切正常.
	//
	// 上游显式下发目标密码时改为另一套口径: 渲染结果必须正好带着那个密码,
	// 与磁盘不同是本次的意图. 仍然要比 —— 拦的是"下发了改密码, 却没渲染进去".
	oldPass := unquoteConfValue(oldDirectives.lastValue("requirepass"))
	newPass := unquoteConfValue(newDirectives.lastValue("requirepass"))
	if req.TargetPassword != nil {
		if newPass != *req.TargetPassword {
			return fmt.Errorf(
				"port(%d) regenerated conf requirepass does not match the delivered target password", port)
		}
		if newPass != oldPass {
			req.Logger.Info("port(%d) regenerated conf changes requirepass to the delivered target", port)
		}
	} else {
		switch {
		case oldPass != "" && !newDirectives.has("requirepass"):
			return fmt.Errorf("port(%d) regenerated conf lost requirepass", port)
		case oldPass != newPass:
			return fmt.Errorf("port(%d) regenerated conf would change requirepass", port)
		}
	}
	// masterauth 变了主从同步会认证失败.
	oldMasterAuth := unquoteConfValue(oldDirectives.lastValue("masterauth"))
	newMasterAuth := unquoteConfValue(newDirectives.lastValue("masterauth"))
	// ensureMasterAuthForReplica 兜底写入的取值就是 requirepass. 与"目标版本配置自己
	// 引入了另一个凭据"区分开: 两者该有的处置不一样
	authFromRequirepass := newMasterAuth != "" && newMasterAuth == newPass
	switch {
	// 改密码时 masterauth 该是什么, 完全由探测结论说了算: 跟错任何一边, 从库下次重连都会
	// AUTH 失败. restart 模式尤其要拦住 —— 这份渲染结果会直接落盘, 实例带着它重连
	case req.MasterAuthFollowsPassword && oldMasterAuth != "":
		if newMasterAuth != newPass {
			return fmt.Errorf("port(%d) regenerated conf should have moved masterauth onto the new"+
				" password because the master already runs it,but left it behind", port)
		}
		req.Logger.Info("port(%d) regenerated conf moves masterauth onto the new password", port)
	case req.passwordChanging(oldDirectives) && oldMasterAuth != "" && newMasterAuth != oldMasterAuth:
		return fmt.Errorf("port(%d) regenerated conf moved masterauth while the master is not on the"+
			" new password yet", port)
	case req.passwordChanging(oldDirectives) && oldMasterAuth != "":
		req.Logger.Info("port(%d) regenerated conf keeps masterauth on the old password,"+
			" the master has not been changed yet", port)
	case oldMasterAuth != "" && oldMasterAuth != newMasterAuth:
		if !authFromRequirepass || !req.Expect.wanted {
			return fmt.Errorf("port(%d) regenerated conf would change masterauth", port)
		}
		// 旧文件留下的是一条指向旧密码的陈旧凭据, 而这个实例马上要作为从库跟随新主
		req.Logger.Info("port(%d) regenerated conf replaces a stale masterauth with requirepass", port)
	case oldMasterAuth == "" && newMasterAuth != "" && !authFromRequirepass:
		req.Logger.Warn("port(%d) regenerated conf introduces masterauth which old conf(%s) had none",
			port, confFile)
	}
	// 声明了从库身份就必须带着能用的凭据: 缺了主从同步会卡在 AUTH 上, 而进程是好的,
	// 只能等 waitRestored 超时才暴露. cluster 的凭据不在配置文件里, 不参与.
	if !consts.IsClusterDbType(req.ClusterType) && newPass != "" && newMasterAuth == "" {
		if _, replTarget := effectiveReplicationOf(confData); replTarget != "" {
			return fmt.Errorf("port(%d) regenerated conf declares replication of %q but has no masterauth",
				port, replTarget)
		}
	}
	// 数据目录不允许被改写; /data1 -> /data 这类软链下的两种写法算同一目录
	oldDir, newDir := oldDirectives.lastValue("dir"), newDirectives.lastValue("dir")
	if !samePathValue(oldDir, newDir) {
		return fmt.Errorf("port(%d) regenerated conf would move dir from %q to %q", port, oldDir, newDir)
	}
	if err := req.checkRegenConfBind(newDirectives, oldDirectives); err != nil {
		return err
	}
	// 主从关系不允许丢失或被改写
	if err := req.checkRegenConfReplication(confData); err != nil {
		return err
	}
	if err := req.checkRegenConfDatabases(newDirectives, oldDirectives); err != nil {
		return err
	}
	// module 不允许丢失, 且 so 文件必须存在
	if len(oldDirectives["loadmodule"]) > 0 && len(newDirectives["loadmodule"]) == 0 {
		return fmt.Errorf("port(%d) regenerated conf lost all %d loadmodule(s)",
			port, len(oldDirectives["loadmodule"]))
	}
	for _, soPath := range newDirectives["loadmodule"] {
		if !util.FileExists(soPath) {
			return fmt.Errorf("port(%d) regenerated conf loadmodule(%s) not exists", port, soPath)
		}
	}
	return nil
}

// bindAddrSet 解析 bind 取值里的地址集合.
//
// 顺序与引号都不算差异. redis 的 "bind -::1" 里前缀 '-' 只表示该地址绑不上也不算启动失败,
// 说的还是同一个地址, 所以按地址本身归一.
func bindAddrSet(value string) map[string]bool {
	addrs := make(map[string]bool)
	for _, token := range strings.Fields(unquoteConfValue(strings.TrimSpace(value))) {
		addr := strings.TrimPrefix(unquoteConfValue(token), "-")
		if addr == "" {
			continue
		}
		addrs[addr] = true
	}
	return addrs
}

// checkRegenConfBind 校验重建结果没有丢掉 bind 里原有的地址.
//
// bind 的取值来自 payload 的 IP, 不从磁盘抄, 所以下发一个陈旧 IP、或模板里写死
// 0.0.0.0, 都会静默改掉实例绑的地址: 前者让实例绑不上本机地址直接起不来,
// 后者把实例对外全开.
//
// 只查"有没有丢", 不要求集合相等: 早期实例磁盘上可能只有 bind <ip>, 而目标模板是
// <ip> 127.0.0.1, 按相等来比会让这些主机的升级凭空失败.
func (req confRegenRequest) checkRegenConfBind(newDirectives, oldDirectives confDirectives) error {
	if !oldDirectives.has("bind") {
		req.Logger.Warn("port(%d) old conf(%s) has no bind directive,skip bind check", req.Port, req.ConfFile)
		return nil
	}
	oldBind, newBind := oldDirectives.lastValue("bind"), newDirectives.lastValue("bind")
	if !newDirectives.has("bind") {
		// 没有 bind 的 redis 监听全部网卡, 比原来那份显式绑定严格更差
		return fmt.Errorf("port(%d) regenerated conf has no bind while old conf(%s) binds %q,"+
			"the instance would listen on all interfaces", req.Port, req.ConfFile, oldBind)
	}
	newAddrs, oldAddrs := bindAddrSet(newBind), bindAddrSet(oldBind)
	missing := make([]string, 0, len(oldAddrs))
	for addr := range oldAddrs {
		if !newAddrs[addr] {
			missing = append(missing, addr)
		}
	}
	if len(missing) == 0 {
		return nil
	}
	slices.Sort(missing)
	return fmt.Errorf("port(%d) regenerated conf bind %q drops address(es) %v declared in %q",
		req.Port, newBind, missing, oldBind)
}

// checkRegenConfReplication 校验重建结果里的主从关系.
//
// 两道闸:
//  1. 与期望一致 —— 这是最紧的一道, 校验的是即将写下去的内容. 期望默认是停机前的运行态,
//     能拦住"文件里的 replicaof 指向另一台还活着的同密码主"这类新旧文件比对看不出的错误;
//     上游指定了新主库时, 期望换成新拓扑, 校验的是我们自己刚渲染进去的那条 replicaof
//  2. 两者都没有时退化为新旧文件比对, 至少保证主从关系没被目标版本配置弄丢
func (req confRegenRequest) checkRegenConfReplication(confData string) error {
	newName, newValue := effectiveReplicationOf(confData)
	if req.Expect.captured() {
		if err := req.Expect.checkConfMatchesExpectation(confData, req.ClusterType); err != nil {
			return fmt.Errorf("port(%d) regenerated conf %v", req.Port, err)
		}
		return nil
	}
	if oldName, oldValue := effectiveReplicationOf(req.OldConfData); oldValue != "" && newValue != oldValue {
		return fmt.Errorf("port(%d) regenerated conf lost replication: old %s %q, new %s %q",
			req.Port, oldName, oldValue, newName, newValue)
	}
	return nil
}

// backupRedisConfFile 备份旧配置文件, 返回备份路径
func backupRedisConfFile(confFile string, confBytes []byte) (string, error) {
	fileInfo, err := os.Stat(confFile)
	if err != nil {
		return "", fmt.Errorf("stat conf(%s) failed,err:%v", confFile, err)
	}
	backupFile := confFile + "." + time.Now().Format(consts.FilenameTimeLayout) + ".bak"
	if err = os.WriteFile(backupFile, confBytes, fileInfo.Mode().Perm()); err != nil {
		return "", fmt.Errorf("backup conf(%s) to %s failed,err:%v", confFile, backupFile, err)
	}
	if err = chownMysqlOrErr(backupFile); err != nil {
		return "", err
	}
	return backupFile, nil
}

// checkRegenConfDatabases 新值不得小于旧值. parse 失败则跳过, 不误杀.
func (req confRegenRequest) checkRegenConfDatabases(newDirectives, oldDirectives confDirectives) error {
	oldVal, oldErr := strconv.Atoi(unquoteConfValue(oldDirectives.lastValue("databases")))
	newVal, newErr := strconv.Atoi(unquoteConfValue(newDirectives.lastValue("databases")))
	if oldErr != nil || newErr != nil || oldVal <= 0 || newVal <= 0 {
		return nil
	}
	if newVal < oldVal {
		return fmt.Errorf("port(%d) regenerated conf would shrink databases from %d to %d",
			req.Port, oldVal, newVal)
	}
	return nil
}
