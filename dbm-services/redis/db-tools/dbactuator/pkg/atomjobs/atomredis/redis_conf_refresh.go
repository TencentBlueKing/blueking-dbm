package atomredis

import (
	"encoding/json"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

const (
	// ApplyModeConfFile 只把渲染结果写到 redis.conf, 不碰运行态
	ApplyModeConfFile = "conf_file"
	// ApplyModeConfigSet 只 CONFIG SET 运行态可改的项, 不写文件
	ApplyModeConfigSet = "config_set"
	// ApplyModeRestart 写文件并重启, 让进程带着新配置起来
	ApplyModeRestart = "restart"
)

// RedisConfRefreshParams redis 实例配置刷新参数
type RedisConfRefreshParams struct {
	IP          string `json:"ip" validate:"required"`
	Ports       []int  `json:"ports" validate:"required"`
	Role        string `json:"role" validate:"required"` // redis_master or redis_slave
	ClusterType string `json:"cluster_type" validate:"required"`
	// ApplyMode 见 ApplyModeConfFile / ApplyModeConfigSet / ApplyModeRestart
	ApplyMode string `json:"apply_mode" validate:"required,oneof=conf_file config_set restart"`
	// PortConfConfigs 下发的配置模板, 是这次刷新的权威来源. 请求的每个端口都必须有完整一份.
	PortConfConfigs map[string]RedisConfRenderItem `json:"port_conf_configs" validate:"required"`
	// PortTargetPasswords key 为端口号字符串, value 为该端口要改成的密码.
	//
	// 缺省时 requirepass 以磁盘为准, 变化即失败(默认行为). 给了某个端口才允许改它的密码.
	// masterauth 不跟着走, 由 followMasterAuth 探过主库之后单独决定.
	// 空串是合法目标(无密码集群), 所以判断"是否改密码"只看 key 在不在, 不能看值是否为空.
	//
	// 不支持 apply_mode=conf_file, 原因见 checkTargetPasswords.
	PortTargetPasswords map[string]string `json:"port_target_passwords"`
	// SyncWaitTimeoutSeconds 重启后等待 master_link_status=up 的超时, 0 表示用默认值.
	SyncWaitTimeoutSeconds int `json:"sync_wait_timeout_seconds"`
}

// targetPassword 该端口本次要改成的密码; 第二个返回值表示上游是否下发了改密码
func (p *RedisConfRefreshParams) targetPassword(port int) (string, bool) {
	pass, ok := p.PortTargetPasswords[strconv.Itoa(port)]
	return pass, ok
}

// RedisConfRefresh 按下游模板刷新本机实例配置
type RedisConfRefresh struct {
	runtime          *jobruntime.JobGenericRuntime
	params           RedisConfRefreshParams
	localPkgBaseName string
	instCount        uint64
	addrMapCli       map[string]*myredis.RedisClient
	replSnapshots    map[int]replSnapshot
	// masterAuthFollow 每个改密码端口的探测结论: true 表示主库确实已经在用目标密码,
	// 本机的 masterauth 应该跟上. 不在里面表示维持磁盘现状. 见 resolveMasterAuthTargets
	masterAuthFollow map[int]bool
}

var _ jobruntime.JobRunner = (*RedisConfRefresh)(nil)

// NewRedisConfRefresh new
func NewRedisConfRefresh() jobruntime.JobRunner {
	return &RedisConfRefresh{}
}

// Init prepare run env
func (job *RedisConfRefresh) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error("json.Unmarshal failed,err:%+v", err)
		return err
	}
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("RedisConfRefresh Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisConfRefresh Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if len(job.params.Ports) == 0 {
		err = fmt.Errorf("RedisConfRefresh Init ports(%+v) is empty", job.params.Ports)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	switch job.params.Role {
	case consts.MetaRoleRedisMaster, consts.MetaRoleRedisSlave:
	default:
		err = fmt.Errorf("role:%s not support", job.params.Role)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	for _, port := range job.params.Ports {
		item, ok := job.params.PortConfConfigs[strconv.Itoa(port)]
		if !ok || len(item.ConfConfigs) == 0 {
			err = fmt.Errorf("port(%d) missing from port_conf_configs", port)
			job.runtime.Logger.Error("%s", err)
			return err
		}
	}
	if err = job.checkTargetPasswords(); err != nil {
		return err
	}
	if !knownRedisStorageClusterType(job.params.ClusterType) {
		err = fmt.Errorf("unknown cluster_type(%s)", job.params.ClusterType)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	job.addrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	job.replSnapshots = make(map[int]replSnapshot, len(job.params.Ports))
	job.masterAuthFollow = make(map[int]bool, len(job.params.PortTargetPasswords))
	return nil
}

// checkTargetPasswords 校验改密码参数本身可用, 停机、写盘之前跑.
//
// conf_file 拒绝改密码: 只写文件不碰运行态, 会留下"文件新密码 / 进程旧密码"的窗口, 而
// dbmon、proxy、dbha 都从文件读密码, 这段时间里它们全都连不上实例.
//
// config_set 与 restart 都支持, 两者的暴露面不一样:
//   - config_set 不打断已建立的复制链路(链路早认证过了, masterauth 只在下次重连时才用到),
//     所以能对 master / slave 并行改. 代价是 masterauth 若判断错了当场看不出来, 要等到
//     未来某次重连才爆
//   - restart 一定会重连, masterauth 错了 settleReplication 当场等不到链路, 任务直接失败.
//     暴露得早, 但破坏性大, 而且探测到实例起来这段窗口比 config_set 长得多, 期间主库若被
//     并行改掉就会踩空. 上游要负责这段时间内不动主库
func (job *RedisConfRefresh) checkTargetPasswords() error {
	if len(job.params.PortTargetPasswords) == 0 {
		return nil
	}
	if job.params.ApplyMode == ApplyModeConfFile {
		err := fmt.Errorf("port_target_passwords requires apply_mode=%s or %s,got %s",
			ApplyModeConfigSet, ApplyModeRestart, job.params.ApplyMode)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	requested := make(map[string]bool, len(job.params.Ports))
	for _, port := range job.params.Ports {
		requested[strconv.Itoa(port)] = true
	}
	for portStr := range job.params.PortTargetPasswords {
		if !requested[portStr] {
			err := fmt.Errorf("port_target_passwords has port(%s) which is not in ports(%+v)",
				portStr, job.params.Ports)
			job.runtime.Logger.Error("%s", err)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisConfRefresh) Name() string {
	return "redis_conf_refresh"
}

// Run Command Run
func (job *RedisConfRefresh) Run() (err error) {
	job.localPkgBaseName, err = readLocalRedisPkgBaseName()
	if err != nil {
		job.runtime.Logger.Error("%s", err)
		return err
	}
	job.runtime.Logger.Info("local redis pkg:%s", job.localPkgBaseName)
	job.instCount = countLocalRedisInstDirs()
	if job.instCount == 0 {
		job.instCount = uint64(len(job.params.Ports))
	}

	if err = job.connectInstances(); err != nil {
		return err
	}
	defer job.allInstDisconnect()

	if err = job.captureSnapshots(); err != nil {
		return err
	}
	// 必须在渲染之前: restart 模式下 masterauth 是随渲染结果一起写进文件的
	job.resolveMasterAuthTargets()

	plans := make(map[int]*regenConfPlan, len(job.params.Ports))
	for _, port := range job.params.Ports {
		plan, buildErr := job.buildPortPlan(port)
		if buildErr != nil {
			job.runtime.Logger.Error("%s", buildErr)
			return buildErr
		}
		plans[port] = plan
	}

	switch job.params.ApplyMode {
	case ApplyModeConfFile:
		return job.applyConfFile(plans)
	case ApplyModeConfigSet:
		return job.applyConfigSetMode(plans)
	case ApplyModeRestart:
		return job.applyRestart(plans)
	default:
		return fmt.Errorf("unknown apply_mode:%s", job.params.ApplyMode)
	}
}

func (job *RedisConfRefresh) addrOf(port int) string {
	return net.JoinHostPort(job.params.IP, strconv.Itoa(port))
}

// regenRequest 把刷新任务的参数映射成一次重建请求. 期望永远是停机前快照, 不改拓扑.
func (job *RedisConfRefresh) regenRequest(port int) confRegenRequest {
	req := confRegenRequest{
		IP:               job.params.IP,
		Port:             port,
		PkgBaseName:      job.localPkgBaseName,
		ClusterType:      job.params.ClusterType,
		InstCount:        job.instCount,
		Expect:           job.replSnapshots[port],
		DiscardLocalData: false,
		Logger:           job.runtime.Logger,
	}
	if pass, ok := job.params.targetPassword(port); ok {
		req.TargetPassword = &pass
		req.MasterAuthFollowsPassword = job.masterAuthFollow[port]
	}
	return req
}

// resolveMasterAuthTargets 渲染之前先把每个改密码端口的 masterauth 结论探出来.
//
// 改密码是跨机器的, 一次 act 只改得动本机这几个端口, 主从两边必然有先后. 从库的 masterauth
// 只在下次重连主库时才用得上, 所以现存链路怎么改都不会当场断; 真正的代价在重连那一刻,
// 而那时凭据错了就再也连不上. 于是两个方向的错都要避免:
//   - 主库还没改就跟过去: 从库拿新密码去 AUTH 旧密码的主库, 重连必失败
//   - 主库已经改了却不跟: 从库拿旧密码去 AUTH 新密码的主库, 一样失败
//
// 光看本机分不出这两种, 所以直接拨一下主库. 探不动(网络不通、主库挂了)一律按"还没改"处理:
// 现存链路还活着, 保持现状至少不会更糟.
//
// 两个模式共用这一次结论, 但用法不同: config_set 拿它决定要不要 CONFIG SET,
// restart 拿它决定渲染进配置文件的 masterauth 是哪个. 探测本身不会让任务失败.
func (job *RedisConfRefresh) resolveMasterAuthTargets() {
	// cluster 的凭据由 redis_switch / redis_cluster_failover 统一管, 不在这里插一手
	if consts.IsClusterDbType(job.params.ClusterType) {
		return
	}
	for _, port := range job.params.Ports {
		newPass, ok := job.params.targetPassword(port)
		if !ok {
			continue
		}
		job.masterAuthFollow[port] = job.masterOnTargetPassword(port, newPass)
	}
}

// masterOnTargetPassword 本端口的主库是不是已经在用目标密码了
func (job *RedisConfRefresh) masterOnTargetPassword(port int, newPassword string) bool {
	addr := job.addrOf(port)
	// 按运行态判角色, 不按 payload 的 role: 切换过后 payload 可能已经对不上了
	snap := job.replSnapshots[port]
	if !snap.isSlave() {
		// 主库没有 masterauth 要跟; 实例没在跑时也抓不到快照, 那种现场同样维持现状
		return false
	}
	masterAddr := net.JoinHostPort(snap.masterHost, snap.masterPort)
	accepted, err := masterAcceptsPassword(masterAddr, newPassword)
	switch {
	case err != nil:
		job.runtime.Logger.Warn("redis(%s) cannot reach its master(%s) to check the password,"+
			" masterauth left as is,err:%v", addr, masterAddr, err)
		return false
	case !accepted:
		job.runtime.Logger.Warn("redis(%s) master(%s) is not on the target password yet,"+
			" masterauth left as is. run this act again on %s once the master is changed,"+
			" otherwise replication breaks on the next reconnect", addr, masterAddr, addr)
		return false
	}
	job.runtime.Logger.Info("redis(%s) master(%s) already runs the target password,masterauth will follow",
		addr, masterAddr)
	return true
}

func (job *RedisConfRefresh) buildPortPlan(port int) (*regenConfPlan, error) {
	item, ok := job.params.PortConfConfigs[strconv.Itoa(port)]
	plan, err := buildRegenPlan(job.regenRequest(port), item, ok)
	if err != nil {
		return nil, err
	}
	if plan == nil {
		return nil, fmt.Errorf("port(%d) missing from port_conf_configs", port)
	}
	return plan, nil
}

func (job *RedisConfRefresh) connectInstances() error {
	requireRunning := job.params.ApplyMode == ApplyModeConfigSet
	for _, port := range job.params.Ports {
		addr := job.addrOf(port)
		inUse, err := portInUse(job.params.IP, port)
		if err != nil {
			return err
		}
		if !inUse {
			if requireRunning {
				err := fmt.Errorf("redis(%s) is not running,config_set requires a live process", addr)
				job.runtime.Logger.Error("%s", err)
				return err
			}
			job.runtime.Logger.Warn("redis(%s) is not running,skip connect", addr)
			continue
		}
		cli, err := connectLocalRedis(addr, port, 5*time.Second)
		if err != nil {
			if requireRunning || job.params.ApplyMode == ApplyModeRestart {
				// 端口占用却连不上: restart 再 start 会撞端口, 必须在这里失败
				return err
			}
			job.runtime.Logger.Warn("redis(%s) connect failed,err:%v", addr, err)
			continue
		}
		if _, rewriteErr := cli.ConfigRewrite(); rewriteErr != nil {
			job.runtime.Logger.Warn("redis(%s) config rewrite failed,conf file may be stale,err:%v",
				addr, rewriteErr)
		}
		job.addrMapCli[addr] = cli
	}
	return nil
}

func (job *RedisConfRefresh) captureSnapshots() error {
	for _, port := range job.params.Ports {
		addr := job.addrOf(port)
		cli := job.addrMapCli[addr]
		if cli == nil {
			job.runtime.Logger.Warn("redis(%s) not connected,skip repl snapshot", addr)
			continue
		}
		snap, err := captureReplSnapshot(cli)
		if err != nil {
			job.runtime.Logger.Error("%s", err)
			return err
		}
		job.replSnapshots[port] = snap
		job.runtime.Logger.Info("redis(%s) repl state:role=%s,master=%q",
			addr, snap.role, snap.masterAddr())
	}
	return nil
}

func (job *RedisConfRefresh) allInstDisconnect() {
	for _, cli := range job.addrMapCli {
		cli.Close()
	}
}

func (job *RedisConfRefresh) applyConfFile(plans map[int]*regenConfPlan) error {
	for _, port := range job.params.Ports {
		if err := job.writePlanIfChanged(port, plans[port]); err != nil {
			return err
		}
	}
	return nil
}

func (job *RedisConfRefresh) writePlanIfChanged(port int, plan *regenConfPlan) error {
	if confDirectivesEqual(plan.oldConfData, plan.confData) {
		job.runtime.Logger.Info("port(%d) conf already matches rendered plan,skip write", port)
		return nil
	}
	backupFile, err := writeRegenConfPlan(plan, port, job.runtime.Logger)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("port(%d) conf written,backup:%s (restore is manual if start later fails)",
		port, backupFile)
	return nil
}

func (job *RedisConfRefresh) applyConfigSetMode(plans map[int]*regenConfPlan) error {
	// 改密码排在最前: 之后的比对都用新密码的连接进行, requirepass 也就不再是一条差异
	if err := job.applyPasswordChanges(); err != nil {
		return err
	}
	for _, port := range job.params.Ports {
		addr := job.addrOf(port)
		cli := job.addrMapCli[addr]
		if cli == nil {
			return fmt.Errorf("redis(%s) not connected,cannot config_set", addr)
		}
		if err := applyConfigSet(cli, plans[port].confData, job.runtime.Logger); err != nil {
			job.runtime.Logger.Error("port(%d) %v", port, err)
			return err
		}
	}
	return nil
}

// applyPasswordChanges 在不重启的前提下改掉下发了目标密码的那些端口.
func (job *RedisConfRefresh) applyPasswordChanges() error {
	for _, port := range job.params.Ports {
		newPass, ok := job.params.targetPassword(port)
		if !ok {
			continue
		}
		if err := job.applyPasswordChangePort(port, newPass); err != nil {
			job.runtime.Logger.Error("%s", err)
			return err
		}
	}
	return nil
}

// applyPasswordChangePort 改一个实例的密码: masterauth -> requirepass -> CONFIG REWRITE
// -> 用新密码重连.
//
// masterauth 与 requirepass 各自判断该不该动, 不共用一个"已经改过了"的早退. 主库先于从库
// 改完的现场里, 从库这一趟会改掉 requirepass 却跳过 masterauth, 只有再跑一次才补得上;
// 两者绑在一起判断的话, 第二趟会因为 requirepass 已经到位而整个跳过.
//
// 必须 rewrite: config_set 模式本来不写文件, 但密码只 SET 不落盘, 下次重启就回退成旧密码,
// 而那时 dbmon / proxy / dbha 手上已经是新密码了. 这是本模式唯一会写配置文件的动作.
func (job *RedisConfRefresh) applyPasswordChangePort(port int, newPassword string) error {
	addr := job.addrOf(port)
	cli := job.addrMapCli[addr]
	if cli == nil {
		return fmt.Errorf("redis(%s) not connected,cannot change password", addr)
	}
	authChanged, err := job.followMasterAuth(cli, port, newPassword)
	if err != nil {
		return err
	}
	got, err := cli.ConfigGet("requirepass")
	if err != nil {
		return fmt.Errorf("redis(%s) config get requirepass failed,err:%v", addr, err)
	}
	runtimePass, _ := confRuntimeLookup(got, "requirepass")
	passChanged := unquoteConfValue(runtimePass) != newPassword
	if !authChanged && !passChanged {
		job.runtime.Logger.Info("redis(%s) already runs with the target password,skip change", addr)
		return nil
	}
	if passChanged {
		if _, err = cli.ConfigSet("requirepass", newPassword); err != nil {
			return fmt.Errorf("redis(%s) config set requirepass failed,err:%v", addr, err)
		}
	}
	if _, err = cli.ConfigRewrite(); err != nil {
		return fmt.Errorf("redis(%s) config rewrite after password change failed,err:%v", addr, err)
	}
	if !passChanged {
		job.runtime.Logger.Info("redis(%s) masterauth caught up with the master,requirepass was already current", addr)
		return nil
	}
	// 手上这个 client 还揣着旧密码, 连接池新开的连接会 AUTH 失败, 换成新密码的
	cli.Close()
	delete(job.addrMapCli, addr)
	newCli, err := connectLocalRedis(addr, port, 10*time.Second)
	if err != nil {
		return fmt.Errorf("redis(%s) reconnect with the new password failed,err:%v", addr, err)
	}
	job.addrMapCli[addr] = newCli
	job.runtime.Logger.Info("redis(%s) password changed and persisted to conf file", addr)
	return nil
}

// followMasterAuth 按 resolveMasterAuthTargets 探好的结论, 把运行态的 masterauth 跟到新密码.
//
// 结论是"还不能跟"时原样留着, 这台从库也就欠了一次修复: 上游按"先改从库再切换"的顺序滚动
// 改密码时必然走到这里, 主库改完之后要对从库再跑一次本 act, 那一趟探测才会通过.
func (job *RedisConfRefresh) followMasterAuth(cli *myredis.RedisClient, port int, newPassword string) (bool, error) {
	if !job.masterAuthFollow[port] {
		return false, nil
	}
	addr := cli.Addr
	got, err := cli.ConfigGet("masterauth")
	if err != nil {
		return false, fmt.Errorf("redis(%s) config get masterauth failed,err:%v", addr, err)
	}
	current, _ := confRuntimeLookup(got, "masterauth")
	if unquoteConfValue(current) == newPassword {
		return false, nil
	}
	if _, err = cli.ConfigSet("masterauth", newPassword); err != nil {
		return false, fmt.Errorf("redis(%s) config set masterauth failed,err:%v", addr, err)
	}
	job.runtime.Logger.Info("redis(%s) masterauth follows the new password", addr)
	return true, nil
}

// masterAcceptsPassword 主库是否已经在用这个密码. 拨一个连接就知道 —— NewRedisClient 建连时
// 会 AUTH 再 PING.
//
// 目标密码为空串(改成无密码)时不发 AUTH: 主库若还带着密码, PING 会拿到 NOAUTH, 同样是"还没改".
// 认证类报错说明连得上但密码不对, 返回 false; 其余(连不上、超时)返回 error 交由调用方保守处理.
func masterAcceptsPassword(addr, password string) (bool, error) {
	cli, err := myredis.NewRedisClient(addr, password, 0, consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		if isRedisAuthError(err) {
			return false, nil
		}
		return false, err
	}
	cli.Close()
	return true, nil
}

// isRedisAuthError 区分"密码不对"与"连不上". 覆盖三种现场: 密码错、该带密码却没带、
// 带了密码但对端没设密码(改成无密码的单据里, 主库先改完就是这一种).
func isRedisAuthError(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToUpper(err.Error())
	for _, s := range []string{"WRONGPASS", "NOAUTH", "INVALID PASSWORD", "NO PASSWORD IS SET"} {
		if strings.Contains(msg, s) {
			return true
		}
	}
	return false
}

type restartAction int

const (
	restartSkip   restartAction = iota // 文件和运行态都已到位, 只再钉一次复制
	restartStart                       // 进程没在跑, 按需写文件后拉起
	restartBounce                      // 进程在跑但还没到位, 按需写文件后停再拉
)

func decideRestartAction(running, confEqual, runtimeMatch bool) restartAction {
	if !running {
		return restartStart
	}
	if confEqual && runtimeMatch {
		return restartSkip
	}
	return restartBounce
}

func (job *RedisConfRefresh) applyRestart(plans map[int]*regenConfPlan) error {
	for _, port := range job.params.Ports {
		if err := job.applyRestartPort(port, plans[port]); err != nil {
			return err
		}
	}
	return nil
}

func (job *RedisConfRefresh) applyRestartPort(port int, plan *regenConfPlan) error {
	addr := job.addrOf(port)
	cli := job.addrMapCli[addr]
	running := cli != nil
	confEqual := confDirectivesEqual(plan.oldConfData, plan.confData)
	runtimeMatch := false
	if running {
		var matchErr error
		runtimeMatch, matchErr = runtimeMatchesPlan(cli, plan.confData)
		if matchErr != nil {
			job.runtime.Logger.Warn("port(%d) runtime match check failed,will restart,err:%v", port, matchErr)
			runtimeMatch = false
		}
	}
	action := decideRestartAction(running, confEqual, runtimeMatch)
	job.runtime.Logger.Info("port(%d) restart decision:running=%v confEqual=%v runtimeMatch=%v action=%d",
		port, running, confEqual, runtimeMatch, action)

	switch action {
	case restartSkip:
		return settleReplication(cli, job.replSnapshots[port], job.params.Role,
			syncWaitTimeoutOrDefault(job.params.SyncWaitTimeoutSeconds), job.runtime.Logger)
	case restartStart:
		if err := job.writePlanIfChanged(port, plan); err != nil {
			return err
		}
		return job.startAndSettle(port)
	case restartBounce:
		if err := job.writePlanIfChanged(port, plan); err != nil {
			return err
		}
		if err := backupCacheMasterBeforeStop(job.params.Role, addr, cli, job.runtime.Logger); err != nil {
			return err
		}
		if err := job.stopRedisForRestart(port, plan); err != nil {
			return err
		}
		return job.startAndSettle(port)
	default:
		return fmt.Errorf("port(%d) unknown restart action", port)
	}
}

// stopRedisForRestart 停实例. 配置文件此时已经是渲染结果, 改密码时里面是新密码, 而进程还
// 只认旧密码, 所以用改写前配置里的那个 —— connectInstances 已经用它连上过.
//
// 旧配置没声明 requirepass 时退回按文件读取的老路径: 密码可能在 instance.conf 里,
// 那种现场只有 GetRedisPasswdFromConfFile 找得到.
func (job *RedisConfRefresh) stopRedisForRestart(port int, plan *regenConfPlan) error {
	oldDirectives := parseRedisConfDirectives(plan.oldConfData)
	if !oldDirectives.has("requirepass") {
		return stopRedisViaScript(job.params.IP, port, job.runtime.Logger)
	}
	return stopRedisViaScriptWithPassword(job.params.IP, port,
		unquoteConfValue(oldDirectives.lastValue("requirepass")), job.runtime.Logger)
}

func (job *RedisConfRefresh) startAndSettle(port int) error {
	cli, err := startRedisAndWaitRepl(job.params.IP, port, job.replSnapshots[port],
		job.params.Role, syncWaitTimeoutOrDefault(job.params.SyncWaitTimeoutSeconds), job.runtime.Logger)
	if cli != nil {
		job.addrMapCli[job.addrOf(port)] = cli
	}
	if err != nil {
		// 新配置起不来就失败, 把新文件留在原地给 DBA. 跑旧配置不是这次刷新想要的状态.
		job.runtime.Logger.Error(
			"port(%d) failed to start with refreshed conf,left new conf in place for DBA,err:%v", port, err)
		return err
	}
	return nil
}

// Retry times
func (job *RedisConfRefresh) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisConfRefresh) Rollback() error {
	return nil
}
