package redisconf

import (
	"fmt"
	"path/filepath"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
)

// RenderItem 单个端口的目标版本配置, 由 dbm 侧按集群算好后下发.
//
// 主从版架构下同一台机器的端口可能分属不同集群, 各自域名/dbconfig 不同,
// 所以按端口下发而不是按主机下发.
type RenderItem struct {
	ConfConfigs       map[string]string `json:"conf_configs"`
	Databases         int               `json:"databases"`
	LoadModulesDetail []LoadModuleItem  `json:"load_modules_detail"`
}

// Request 一次配置文件重建所需的全部事实.
//
// 显式携带而不是从原子任务参数里现读: 重建配置这件事本身与具体原子任务无关.
// 每个任务自己负责映射; 渲染 + 改写 + 校验链路只认这一组事实.
type Request struct {
	IP   string
	Port int
	// PkgBaseName 实例即将运行的版本包名, 形如 redis-6.2.7.
	//
	// 版本升级填目标介质包名; 不换二进制的任务填 /usr/local/redis 软链当前指向的包名.
	// 它决定写 replicaof 还是 slaveof、cluster-replica-* 还是 cluster-slave-*,
	// 填错实例直接起不来.
	PkgBaseName string
	ClusterType string
	// InstCount 本机实例个数, tendisplus 的 blockcache / write buffer 按实例数分摊
	InstCount uint64
	// Item 目标版本的配置项, 由 dbm 侧按集群算好后下发
	Item RenderItem
	// Steps 渲染之后依次执行的改写, 由调用方按任务性质选 UpgradeSteps / RefreshSteps
	Steps []Step
	// Expect 重建后这个实例应达成的复制状态, 取值见 ReplState
	Expect ReplState
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
	// 由调用方探过主库之后置位: 只有主库确实已经在用新密码才为 true. 渲染自己看不见对端,
	// 判断不了主库改到哪一步了, 所以默认 false 也就是"凭据原样留着" —— 现存链路不会当场断,
	// 大不了下一趟再跟上.
	MasterAuthFollowsPassword bool
	// ConfFile / OldConfData 磁盘上的现状, 由 LoadAndPlan 读好后填入.
	//
	// OldConfData 是展开 include 之后、redis 实际加载的那份文本, 渲染与校验只认它;
	// RawOldConfData 是磁盘原文, 只用于备份和回滚. IncludedFiles 是原文 include 过的文件.
	//
	// 文件 IO 留在调用方: 渲染与校验因此是纯函数, 调用方也能自己决定从哪读
	ConfFile       string
	OldConfData    string
	RawOldConfData string
	IncludedFiles  []string
	Logger         *logger.Logger
}

// LoadAndPlan 读出端口在磁盘上的生效配置, 组装重建请求并跑完渲染、改写与校验.
//
// 该端口没有下发目标配置时返回 (nil, nil), 是否算错误由调用方决定:
// 版本升级保持"只换二进制"的旧行为; 配置刷新在 Init 已保证每端口都有配置.
func LoadAndPlan(req Request, item RenderItem, delivered bool) (*Plan, error) {
	if !delivered || len(item.ConfConfigs) == 0 {
		return nil, nil
	}
	eff, err := LoadEffective(req.Port)
	if err != nil {
		return nil, err
	}
	req.Item = item
	req.ConfFile = eff.File
	req.OldConfData = eff.Expanded
	req.RawOldConfData = eff.Raw
	req.IncludedFiles = eff.Includes
	if len(eff.Includes) > 0 {
		req.Logger.Info("port(%d) conf(%s) includes %v,regenerate from the expanded conf",
			req.Port, eff.File, eff.Includes)
	}
	return req.Plan()
}

// Plan 渲染目标版本配置并校验, 不写任何文件.
//
// 做法是 "以目标版本渲染结果为基准, 再把只存在于运行态的取值搬过来",
// 而不是拿旧文件做逐 key 覆盖 —— 见 ParseDirectives 的说明.
// 目标版本已经删掉的指令因此自然消失, 这正是新版本进程起不来的根因所在.
func (req Request) Plan() (*Plan, error) {
	confData, err := req.Render()
	if err != nil {
		return nil, err
	}
	if err = req.Validate(confData); err != nil {
		return nil, err
	}
	nodesMove, err := planNodesFileMove(req, ParseDirectives(req.OldConfData), ParseDirectives(confData))
	if err != nil {
		return nil, err
	}
	return &Plan{
		Port:       req.Port,
		ConfFile:   req.ConfFile,
		OldConf:    req.OldConfData,
		RawOldConf: req.RawOldConfData,
		Includes:   req.IncludedFiles,
		NewConf:    confData,
		NodesMove:  nodesMove,
	}, nil
}

// Render 渲染目标版本配置, 再依次执行 Steps
func (req Request) Render() (string, error) {
	if len(req.Steps) == 0 {
		return "", fmt.Errorf("port(%d) conf regenerate request has no rewrite steps", req.Port)
	}
	oldDirectives := ParseDirectives(req.OldConfData)
	confData, err := req.renderTemplate(oldDirectives)
	if err != nil {
		return "", err
	}
	for _, step := range req.Steps {
		confData = step.apply(req, oldDirectives, confData)
	}
	return confData, nil
}

// renderTemplate 用目标版本模板渲染, 占位符取值以磁盘上的运行态事实为准
func (req Request) renderTemplate(oldDirectives Directives) (string, error) {
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
		if old, parseErr := strconv.Atoi(Unquote(oldDirectives.LastValue("databases"))); parseErr == nil && old > 0 {
			databases = old
		} else {
			databases = 2
		}
	}
	tmpl := BuildTemplate(req.Item.ConfConfigs, modules, req.PkgBaseName)
	renderValues, err := RenderParams{
		IP:        req.IP,
		Port:      req.Port,
		Password:  req.renderedPassword(oldDirectives),
		Databases: databases,
		InstDir:   req.instDir(oldDirectives),
		DbType:    req.ClusterType,
		// maxmemory 由 dbmon 动态设置并被 config rewrite 落盘, 必须沿用磁盘上的值,
		// 否则升级后实例内存上限被清零
		MaxMemory: oldDirectives.LastValue("maxmemory"),
		InstCount: req.InstCount,
	}.Resolve()
	if err != nil {
		return "", err
	}
	return RenderData(tmpl, renderValues), nil
}

// InstDir 渲染时 {{redis_data_dir}} 用的实例目录
func (req Request) InstDir() string {
	return req.instDir(ParseDirectives(req.OldConfData))
}

// instDir 决定渲染时 {{redis_data_dir}} 用哪个写法.
//
// 以旧配置里 dir 已经生效的写法为准, 而不是 consts.GetRedisDataDir() 的探测结果:
// 探测只要看到 /data1/redis 就返回 /data1, 而 /data1 可能只是 /data 的软链,
// 于是重建后 dir 从 /data/redis/30000/data 变成 /data1/redis/30000/data,
// 看起来像把数据目录搬了家(校验会拦), logfile/pidfile 也会跟着换写法.
func (req Request) instDir(oldDirectives Directives) string {
	fallback := filepath.Dir(req.ConfFile)
	oldDir := Unquote(oldDirectives.LastValue("dir"))
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
func (req Request) renderedPassword(oldDirectives Directives) string {
	if req.TargetPassword != nil {
		return *req.TargetPassword
	}
	return Unquote(oldDirectives.LastValue("requirepass"))
}

// passwordChanging 本次是否真的会把 requirepass 从磁盘上的取值改掉.
//
// 下发的目标密码与磁盘一致时不算改密码: 那些"改密码才放行"的分支应保持保守行为.
func (req Request) passwordChanging(oldDirectives Directives) bool {
	if req.TargetPassword == nil {
		return false
	}
	return *req.TargetPassword != Unquote(oldDirectives.LastValue("requirepass"))
}
