package redisconf

import (
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// invariant 写盘前必须成立的一条约束. 任一条不成立就不写配置文件.
//
// 调用方会在停实例之前先跑一遍完整的 Plan, 所以正常情况下报错时实例还都在跑.
type invariant struct {
	name  string
	check func(req Request, confData string, oldDirs, newDirs Directives) error
}

// invariants 按顺序全部跑完, 一次报出所有不成立的项, 现场不用改一项重跑一次
var invariants = []invariant{
	{"no-placeholder", checkNoPlaceholder},
	{"no-include", checkNoInclude},
	{"complete-conf", checkCompleteConf},
	{"requirepass", Request.checkRequirepass},
	{"masterauth", Request.checkMasterAuth},
	{"replica-has-masterauth", Request.checkReplicaHasMasterAuth},
	{"dir", Request.checkDir},
	{"bind", Request.checkBind},
	{"replication", Request.checkReplication},
	{"databases", Request.checkDatabases},
	{"modules", Request.checkModules},
}

// Validate 写入前的兜底校验, 返回全部不成立的项
func (req Request) Validate(confData string) error {
	oldDirs := ParseDirectives(req.OldConfData)
	newDirs := ParseDirectives(confData)
	var errs []error
	for _, inv := range invariants {
		if err := inv.check(req, confData, oldDirs, newDirs); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}

func checkNoPlaceholder(req Request, confData string, _, _ Directives) error {
	if err := CheckUnresolvedPlaceholder(confData); err != nil {
		return fmt.Errorf("port(%d) conf(%s) %v", req.Port, req.ConfFile, err)
	}
	return nil
}

// checkNoInclude 重建结果必须自成一体: 带着 include 写下去, 被引用文件里的旧指令会重新混进来
func checkNoInclude(req Request, _ string, _, newDirs Directives) error {
	if newDirs.Has("include") {
		return fmt.Errorf("port(%d) regenerated conf must not contain include,got %v",
			req.Port, newDirs["include"])
	}
	return nil
}

// checkCompleteConf 缺 port/dir 说明下发的不是完整一份配置(同版本升级、版本降级场景
// dbm 侧只继承 maxmemory 这类少量配置项), 拿它重建只会写出一份空壳配置
func checkCompleteConf(req Request, _ string, _, newDirs Directives) error {
	for _, name := range []string{"port", "dir"} {
		if !newDirs.Has(name) {
			return fmt.Errorf(
				"port(%d) regenerated conf missing directive %q,delivered conf is not a complete redis.conf",
				req.Port, name)
		}
	}
	if newDirs.LastValue("port") != strconv.Itoa(req.Port) {
		return fmt.Errorf("port(%d) regenerated conf port=%q mismatch", req.Port, newDirs.LastValue("port"))
	}
	return nil
}

// checkRequirepass 密码默认不允许变化(空密码实例也算): 变了就连不上, 主从也会认证失败.
//
// 按"指令缺失等同于空密码"对称比较, 不能只在旧文件有 requirepass 时才比:
// 旧文件没有而目标版本配置引入一个, 同样会让 proxy / dbmon / dbha 连不上,
// 而重启后的实例自己用新配置里的密码, 表面上一切正常.
//
// 上游显式下发目标密码时改为另一套口径: 渲染结果必须正好带着那个密码,
// 与磁盘不同是本次的意图. 仍然要比 —— 拦的是"下发了改密码, 却没渲染进去".
func (req Request) checkRequirepass(_ string, oldDirs, newDirs Directives) error {
	oldPass := Unquote(oldDirs.LastValue("requirepass"))
	newPass := Unquote(newDirs.LastValue("requirepass"))
	if req.TargetPassword != nil {
		if newPass != *req.TargetPassword {
			return fmt.Errorf(
				"port(%d) regenerated conf requirepass does not match the delivered target password", req.Port)
		}
		if newPass != oldPass {
			req.Logger.Info("port(%d) regenerated conf changes requirepass to the delivered target", req.Port)
		}
		return nil
	}
	switch {
	case oldPass != "" && !newDirs.Has("requirepass"):
		return fmt.Errorf("port(%d) regenerated conf lost requirepass", req.Port)
	case oldPass != newPass:
		return fmt.Errorf("port(%d) regenerated conf would change requirepass", req.Port)
	}
	return nil
}

// checkMasterAuth masterauth 变了主从同步会认证失败.
func (req Request) checkMasterAuth(_ string, oldDirs, newDirs Directives) error {
	port := req.Port
	newPass := Unquote(newDirs.LastValue("requirepass"))
	oldMasterAuth := Unquote(oldDirs.LastValue("masterauth"))
	newMasterAuth := Unquote(newDirs.LastValue("masterauth"))
	// StepMasterAuthForReplica 兜底写入的取值就是 requirepass. 与"目标版本配置自己
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
	case req.passwordChanging(oldDirs) && oldMasterAuth != "" && newMasterAuth != oldMasterAuth:
		return fmt.Errorf("port(%d) regenerated conf moved masterauth while the master is not on the"+
			" new password yet", port)
	case req.passwordChanging(oldDirs) && oldMasterAuth != "":
		req.Logger.Info("port(%d) regenerated conf keeps masterauth on the old password,"+
			" the master has not been changed yet", port)
	case oldMasterAuth != "" && oldMasterAuth != newMasterAuth:
		if !authFromRequirepass || !req.Expect.Wanted {
			return fmt.Errorf("port(%d) regenerated conf would change masterauth", port)
		}
		// 旧文件留下的是一条指向旧密码的陈旧凭据, 而这个实例马上要作为从库跟随新主
		req.Logger.Info("port(%d) regenerated conf replaces a stale masterauth with requirepass", port)
	case oldMasterAuth == "" && newMasterAuth != "" && !authFromRequirepass:
		req.Logger.Warn("port(%d) regenerated conf introduces masterauth which old conf(%s) had none",
			port, req.ConfFile)
	}
	return nil
}

// checkReplicaHasMasterAuth 声明了从库身份就必须带着能用的凭据: 缺了主从同步会卡在 AUTH 上,
// 而进程是好的, 只能等同步超时才暴露. cluster 的凭据不在配置文件里, 不参与.
func (req Request) checkReplicaHasMasterAuth(confData string, _, newDirs Directives) error {
	if consts.IsClusterDbType(req.ClusterType) {
		return nil
	}
	newPass := Unquote(newDirs.LastValue("requirepass"))
	if newPass == "" || Unquote(newDirs.LastValue("masterauth")) != "" {
		return nil
	}
	if _, replTarget := EffectiveReplicationOf(confData); replTarget != "" {
		return fmt.Errorf("port(%d) regenerated conf declares replication of %q but has no masterauth",
			req.Port, replTarget)
	}
	return nil
}

// checkDir 数据目录不允许被改写; /data1 -> /data 这类软链下的两种写法算同一目录
func (req Request) checkDir(_ string, oldDirs, newDirs Directives) error {
	oldDir, newDir := oldDirs.LastValue("dir"), newDirs.LastValue("dir")
	if !SamePathValue(oldDir, newDir) {
		return fmt.Errorf("port(%d) regenerated conf would move dir from %q to %q", req.Port, oldDir, newDir)
	}
	return nil
}

// bindAddrSet 解析 bind 取值里的地址集合.
//
// 顺序与引号都不算差异. redis 的 "bind -::1" 里前缀 '-' 只表示该地址绑不上也不算启动失败,
// 说的还是同一个地址, 所以按地址本身归一.
func bindAddrSet(value string) map[string]bool {
	addrs := make(map[string]bool)
	for _, token := range strings.Fields(Unquote(strings.TrimSpace(value))) {
		addr := strings.TrimPrefix(Unquote(token), "-")
		if addr == "" {
			continue
		}
		addrs[addr] = true
	}
	return addrs
}

// checkBind 校验重建结果没有丢掉 bind 里原有的地址.
//
// bind 的取值来自 payload 的 IP, 不从磁盘抄, 所以下发一个陈旧 IP、或模板里写死
// 0.0.0.0, 都会静默改掉实例绑的地址: 前者让实例绑不上本机地址直接起不来,
// 后者把实例对外全开.
//
// 只查"有没有丢", 不要求集合相等: 早期实例磁盘上可能只有 bind <ip>, 而目标模板是
// <ip> 127.0.0.1, 按相等来比会让这些主机的升级凭空失败.
func (req Request) checkBind(_ string, oldDirs, newDirs Directives) error {
	if !oldDirs.Has("bind") {
		req.Logger.Warn("port(%d) old conf(%s) has no bind directive,skip bind check", req.Port, req.ConfFile)
		return nil
	}
	oldBind, newBind := oldDirs.LastValue("bind"), newDirs.LastValue("bind")
	if !newDirs.Has("bind") {
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

// checkReplication 校验重建结果里的主从关系.
//
// 两道闸:
//  1. 与期望一致 —— 这是最紧的一道, 校验的是即将写下去的内容. 期望默认是停机前的运行态,
//     能拦住"文件里的 replicaof 指向另一台还活着的同密码主"这类新旧文件比对看不出的错误;
//     上游指定了新主库时, 期望换成新拓扑, 校验的是我们自己刚渲染进去的那条 replicaof
//  2. 两者都没有时退化为新旧文件比对, 至少保证主从关系没被目标版本配置弄丢
func (req Request) checkReplication(confData string, _, _ Directives) error {
	newName, newValue := EffectiveReplicationOf(confData)
	if req.Expect.Captured() {
		if err := req.Expect.CheckConfMatchesExpectation(confData, req.ClusterType); err != nil {
			return fmt.Errorf("port(%d) regenerated conf %v", req.Port, err)
		}
		return nil
	}
	if oldName, oldValue := EffectiveReplicationOf(req.OldConfData); oldValue != "" && newValue != oldValue {
		return fmt.Errorf("port(%d) regenerated conf lost replication: old %s %q, new %s %q",
			req.Port, oldName, oldValue, newName, newValue)
	}
	return nil
}

// checkDatabases 新值不得小于旧值. parse 失败则跳过, 不误杀.
func (req Request) checkDatabases(_ string, oldDirs, newDirs Directives) error {
	oldVal, oldErr := strconv.Atoi(Unquote(oldDirs.LastValue("databases")))
	newVal, newErr := strconv.Atoi(Unquote(newDirs.LastValue("databases")))
	if oldErr != nil || newErr != nil || oldVal <= 0 || newVal <= 0 {
		return nil
	}
	if newVal < oldVal {
		return fmt.Errorf("port(%d) regenerated conf would shrink databases from %d to %d",
			req.Port, oldVal, newVal)
	}
	return nil
}

// checkModules module 不允许丢失, 且 so 文件必须存在
func (req Request) checkModules(_ string, oldDirs, newDirs Directives) error {
	if len(oldDirs["loadmodule"]) > 0 && len(newDirs["loadmodule"]) == 0 {
		return fmt.Errorf("port(%d) regenerated conf lost all %d loadmodule(s)",
			req.Port, len(oldDirs["loadmodule"]))
	}
	for _, soPath := range newDirs["loadmodule"] {
		if !util.FileExists(soPath) {
			return fmt.Errorf("port(%d) regenerated conf loadmodule(%s) not exists", req.Port, soPath)
		}
	}
	return nil
}
