package atomproxy

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
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

// ProxyVersionUpgradeParams 代理版本升级参数
type ProxyVersionUpgradeParams struct {
	common.MediaPkg
	IP          string `json:"ip" validate:"required"`
	Port        int    `json:"port" validate:"required"` //  只支持1个端口
	Password    string `json:"password" validate:"required"`
	ClusterType string `json:"cluster_type" validate:"required"`
}

// ProxyVersionUpgrade 代理版本升级
type ProxyVersionUpgrade struct {
	runtime          *jobruntime.JobGenericRuntime
	params           ProxyVersionUpgradeParams
	localPkgBaseName string
	role             string // predixy or twemproxy
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ProxyVersionUpgrade)(nil)

// NewProxyVersionUpgrade new
func NewProxyVersionUpgrade() jobruntime.JobRunner {
	return &ProxyVersionUpgrade{}
}

// Init prepare run env
func (job *ProxyVersionUpgrade) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("ProxyVersionUpgrade Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ProxyVersionUpgrade Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if job.params.Port == 0 {
		err = fmt.Errorf("ProxyVersionUpgrade Init port:%d==0", job.params.Port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// Name 原子任务名
func (job *ProxyVersionUpgrade) Name() string {
	return "redis_proxy_version_upgrade"
}

// Run Command Run
func (job *ProxyVersionUpgrade) Run() (err error) {
	addr := fmt.Sprintf("%s:%d", job.params.IP, job.params.Port)
	cli, err := myredis.NewRedisClient(addr, job.params.Password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return err
	}
	cli.Close()
	err = job.getRole()
	if err != nil {
		return
	}
	err = job.getLocalProxyPkgBaseName()
	if err != nil {
		return err
	}
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	err = job.checkProxyLocalPkgAndTargetPkgSameType()
	if err != nil {
		return err
	}
	// 如果当前proxy运行版本已经ok
	isVersionOK, runTimeVer, err := job.isProxyRuntimeVersionOK()
	if err != nil {
		return err
	}
	if isVersionOK {
		job.runtime.Logger.Info("%s %s:%d runTimeVersion:%s already target version,check proxy memory-vs-conf before skip upgrade",
			job.role, job.params.IP, job.params.Port, runTimeVer)
		err = job.checkAndSyncBackendsBeforeRestart()
		if err != nil {
			return err
		}
		job.runtime.Logger.Info(fmt.Sprintf("%s %s:%d runTimeVersion:%s,skip upgrade...",
			job.role, job.params.IP, job.params.Port, runTimeVer))
		return
	}
	// 关闭 dbmon,最后再拉起
	err = util.StopBkDbmon()
	if err != nil {
		return err
	}
	defer util.StartBkDbmon()
	// 当前/usr/local/twemproxy or /usr/local/predixy 指向版本不是 目标版本
	err = job.untarMedia()
	if err != nil {
		return err
	}
	// 重启前校验 proxy 内存路由与磁盘配置一致性:
	// 后端切换 (switch/failover) 后, proxy 内存中的 backend 指向已更新, 但 config rewrite 可能失败
	// 或低版本 predixy 不支持, 导致磁盘配置仍为陈旧值. 若直接重启, 新进程会读到陈旧配置, 连不上真实后端.
	// 这里在 stop 之前用内存中的真实 backends 回写磁盘配置并复核, 回写失败才中断升级.
	err = job.checkAndSyncBackendsBeforeRestart()
	if err != nil {
		return err
	}
	// 先 stop proxy
	err = job.stopProxy()
	if err != nil {
		return err
	}
	// 更新 /usr/local/twemproxy or /usr/local/predixy 软链接
	err = job.updateFileLink()
	if err != nil {
		return err
	}
	// 再 start proxy
	err = job.startProxy()
	if err != nil {
		return err
	}
	// 如果当前proxy运行版本依然不ok,报错
	isVersionOK, runTimeVer, err = job.isProxyRuntimeVersionOK()
	if err != nil {
		return err
	}
	if !isVersionOK {
		err = fmt.Errorf("after upgrade,%s %s:%d runTimeVersion:%s not %s",
			job.role, job.params.IP, job.params.Port, runTimeVer, job.params.Pkg)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.runtime.Logger.Info(fmt.Sprintf("after upgrade,%s %s:%d runTimeVersion:%s == %s",
		job.role, job.params.IP, job.params.Port, runTimeVer, job.params.Pkg))

	return nil
}

func (job *ProxyVersionUpgrade) getRole() (err error) {
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		job.role = "predixy"
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		job.role = "twemproxy"
	} else {
		err = fmt.Errorf("unknown ClusterType:%s", job.params.ClusterType)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

func (job *ProxyVersionUpgrade) getLocalProxyPkgBaseName() (err error) {
	proxySoftLink := ""
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		proxySoftLink = filepath.Join(consts.UsrLocal, "predixy")
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		proxySoftLink = filepath.Join(consts.UsrLocal, "twemproxy")
	}
	_, err = os.Stat(proxySoftLink)
	if err != nil && os.IsNotExist(err) {
		err = fmt.Errorf("%s soft link(%s) not exist", job.role, proxySoftLink)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	realLink, err := os.Readlink(proxySoftLink)
	if err != nil {
		err = fmt.Errorf("readlink %s soft link(%s) failed,err:%+v", job.role, proxySoftLink, err)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.localPkgBaseName = filepath.Base(realLink)
	job.runtime.Logger.Info("before update,%s->%s", proxySoftLink, realLink)
	return nil
}

// checkProxyLocalPkgAndTargetPkgSameType 检查proxy本地包与目标包是同一类型,避免 twemproxy 传的是 predixy 的包
func (job *ProxyVersionUpgrade) checkProxyLocalPkgAndTargetPkgSameType() (err error) {
	targetPkgName := job.params.GePkgBaseName()
	if !strings.Contains(targetPkgName, job.role) {
		err = fmt.Errorf("/usr/local/%s->%s cannot update to %s",
			job.role, job.localPkgBaseName, targetPkgName)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

func (job *ProxyVersionUpgrade) isProxyRuntimeVersionOK() (ok bool, runTimeVer string, err error) {
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		runTimeVer, err = myredis.GetPredixyRunTimeVersion(job.params.IP, job.params.Port,
			job.params.Password)
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		runTimeVer, err = myredis.GetTwemproxyRunTimeVersion(job.params.IP, job.params.Port)
		runTimeVer = strings.Replace(runTimeVer, "rc-v0.", "", -1)
	}
	if err != nil {
		return false, runTimeVer, err
	}
	runtimeBaseVer, runtimeSubVer, err := util.VersionParse(runTimeVer)
	if err != nil {
		return false, runTimeVer, err
	}
	pkgBaseVer, pkgSubVer, err := util.VersionParse(job.params.GePkgBaseName())
	if err != nil {
		return false, runTimeVer, err
	}
	if runtimeBaseVer != pkgBaseVer || runtimeSubVer != pkgSubVer {
		return false, runTimeVer, nil
	}
	return true, runTimeVer, nil
}

// untarMedia 解压介质
func (job *ProxyVersionUpgrade) untarMedia() (err error) {
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	pkgAbsPath := job.params.GetAbsolutePath()
	untarCmd := fmt.Sprintf("tar -zxf %s -C %s", pkgAbsPath, consts.UsrLocal)
	job.runtime.Logger.Info(untarCmd)
	_, err = util.RunBashCmd(untarCmd, "", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("untar %s success", pkgAbsPath)
	return nil
}

// updateFileLink 更新 /usr/local/twemproxy or /usr/local/predixy 软链接
func (job *ProxyVersionUpgrade) updateFileLink() (err error) {
	pkgBaseName := job.params.GePkgBaseName()
	proxySoftLink := ""
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		proxySoftLink = filepath.Join(consts.UsrLocal, "predixy")
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		proxySoftLink = filepath.Join(consts.UsrLocal, "twemproxy")
	}
	_, err = os.Stat(proxySoftLink)
	if err == nil {
		// 删除 /usr/local/twemproxy or /usr/local/predixy 软链接
		err = os.Remove(proxySoftLink)
		if err != nil {
			err = fmt.Errorf("remove %s soft link(%s) failed,err:%+v", job.role, proxySoftLink, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	// 创建 /usr/local/{proxy} -> /usr/local/$pkgBaseName 软链接
	err = os.Symlink(filepath.Join(consts.UsrLocal, pkgBaseName), proxySoftLink)
	if err != nil {
		err = fmt.Errorf("os.Symlink %s -> %s fail,err:%s", proxySoftLink, filepath.Join(consts.UsrLocal, pkgBaseName), err)
		job.runtime.Logger.Error(err.Error())
		return
	}
	util.LocalDirChownMysql(proxySoftLink)
	util.LocalDirChownMysql(proxySoftLink + "/")
	job.runtime.Logger.Info("create softLink success,%s -> %s", proxySoftLink, filepath.Join(consts.UsrLocal, pkgBaseName))
	return nil
}

// stopProxy 关闭 proxy
func (job *ProxyVersionUpgrade) stopProxy() (err error) {
	stopScript := ""
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		stopScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "stop_predixy.sh")
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		stopScript = filepath.Join(consts.UsrLocal, "twemproxy", "bin", "stop_nutcracker.sh")
	}
	_, err = os.Stat(stopScript)
	if err != nil && os.IsNotExist(err) {
		job.runtime.Logger.Info("%s not exist", stopScript)
		return nil
	}
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s %d\"",
		consts.MysqlAaccount, stopScript, job.params.Port))

	maxRetryTimes := 5
	inUse := false
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		util.RunLocalCmd("su",
			[]string{consts.MysqlAaccount, "-c", stopScript + " " + strconv.Itoa(job.params.Port)},
			"", nil, 10*time.Minute)
		inUse, err = util.CheckPortIsInUse(job.params.IP, strconv.Itoa(job.params.Port))
		if err != nil {
			job.runtime.Logger.Error(fmt.Sprintf("check %s:%d inUse failed,err:%v", job.params.IP, job.params.Port, err))
			return err
		}
		if !inUse {
			break
		}
		time.Sleep(2 * time.Second)
	}
	if inUse {
		err = fmt.Errorf("stop %s (%s:%d) failed,port:%d still using",
			job.role, job.params.IP, job.params.Port, job.params.Port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("stop %s (%s:%d) success",
		job.role, job.params.IP, job.params.Port)
	return nil
}

// startProxy 拉起 proxy
func (job *ProxyVersionUpgrade) startProxy() (err error) {
	startScript := ""
	port := job.params.Port
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		startScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "start_predixy.sh")
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		startScript = filepath.Join(consts.UsrLocal, "twemproxy", "bin", "start_nutcracker.sh")
	}
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\" 2>/dev/null",
		consts.MysqlAaccount, startScript+" "+strconv.Itoa(port)))
	_, err = util.RunLocalCmd("su",
		[]string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(port) + " 2>/dev/null"},
		"", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli, err := myredis.NewRedisClientWithRetry(addr, job.params.Password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	defer cli.Close()
	job.runtime.Logger.Info("start proxy (%s:%d) success", job.params.IP, port)
	return nil
}

// checkAndSyncBackendsBeforeRestart 重启前校验 proxy 内存路由与磁盘配置是否一致,
// 不一致(磁盘缺失内存中存活的 backend)时, 用内存回写磁盘配置并复核;
// 回写或复核失败则返回 error, 阻止后续 stop/start, 避免重启后读到陈旧配置连不上后端.
func (job *ProxyVersionUpgrade) checkAndSyncBackendsBeforeRestart() (err error) {
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		return job.checkAndSyncPredixyConf()
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		return job.checkAndSyncTwemproxyConf()
	}
	job.runtime.Logger.Info("cluster_type:%s not predixy/twemproxy,skip mem-vs-conf check", job.params.ClusterType)
	return nil
}

// checkAndSyncPredixyConf 校验并(必要时)回写 predixy 配置文件
func (job *ProxyVersionUpgrade) checkAndSyncPredixyConf() (err error) {
	confFile, err := myredis.GetPredixyLocalConfFile(job.params.Port)
	if err != nil {
		return err
	}
	if confFile == "" {
		err = fmt.Errorf("predixy(%s:%d) local conf file not found", job.params.IP, job.params.Port)
		job.runtime.Logger.Error("%s", err)
		return err
	}
	// 内存中的 backends (info servers)
	infoServers, err := myredis.GetPredixyInfoServersDecoded(job.params.IP, job.params.Port, job.params.Password)
	if err != nil {
		return err
	}
	missing, failedPresent, err := predixyConfServerDiff(confFile, infoServers)
	if err != nil {
		return err
	}
	if len(missing) == 0 && len(failedPresent) == 0 {
		job.runtime.Logger.Info("predixy(%s:%d) conf Servers block consistent with memory,missing=0,skip sync",
			job.params.IP, job.params.Port)
		return nil
	}
	job.runtime.Logger.Warn(
		"predixy(%s:%d) conf(%s) stale,missing backends:%v,failed backends still present:%v,will sync from memory",
		job.params.IP, job.params.Port, confFile, missing, failedPresent)
	job.runtime.Logger.Info("predixy(%s:%d) regenerate conf Servers block from memory via regex replace",
		job.params.IP, job.params.Port)
	err = regeneratePredixyConfServers(confFile, infoServers)
	if err != nil {
		return fmt.Errorf("sync predixy(%s:%d) conf from memory failed,err:%v", job.params.IP, job.params.Port, err)
	}
	// 回写后复核 (再次读取磁盘配置)
	missing, failedPresent, err = predixyConfServerDiff(confFile, infoServers)
	if err != nil {
		return err
	}
	if len(missing) != 0 || len(failedPresent) != 0 {
		return fmt.Errorf("after sync,predixy(%s:%d) conf Servers block still inconsistent,missing:%v failed_present:%v",
			job.params.IP, job.params.Port, missing, failedPresent)
	}
	job.runtime.Logger.Info("predixy(%s:%d) conf synced from memory and verified ok", job.params.IP, job.params.Port)
	return nil
}

// predixyServersBlockRe 匹配 predixy 配置中的 Servers {} 块.
// 该块内仅有 "+ addr" 行, 无嵌套花括号, 故用 [^}]* 非贪婪匹配整块即可.
var predixyServersBlockRe = regexp.MustCompile(`(?s)Servers\s*\{[^}]*\}`)

// extractPredixyServersBlock 提取 predixy 配置中唯一的 Servers {} 块文本
func extractPredixyServersBlock(confData string) (string, error) {
	blocks := predixyServersBlockRe.FindAllString(confData, -1)
	if len(blocks) != 1 {
		return "", fmt.Errorf("expect exactly 1 'Servers {}' block,got %d", len(blocks))
	}
	return blocks[0], nil
}

// predixyConfServerDiff 返回 predixy 内存(info servers)与磁盘配置 Servers {} 块的差异:
//   - missing: CurrentIsFail != 1 的 server 在配置块中缺失
//   - failedPresent: CurrentIsFail == 1 的 server 仍存在于配置块中
//
// 比对范围限定在 Servers {} 块内, 避免与文件其它位置(如注释)误匹配.
func predixyConfServerDiff(confFile string, infoServers []*myredis.PredixyInfoServer) (
	missing []string,
	failedPresent []string,
	err error,
) {
	confBytes, err := os.ReadFile(confFile)
	if err != nil {
		return nil, nil, fmt.Errorf("read predixy conf(%s) failed,err:%v", confFile, err)
	}
	serversBlock, err := extractPredixyServersBlock(string(confBytes))
	if err != nil {
		return nil, nil, fmt.Errorf("predixy conf(%s) %v", confFile, err)
	}
	for _, svr := range infoServers {
		existsInConf := strings.Contains(serversBlock, svr.Server)
		if svr.CurrentIsFail == 1 {
			if existsInConf {
				failedPresent = append(failedPresent, svr.Server)
			}
			continue
		}
		if !existsInConf {
			missing = append(missing, svr.Server)
		}
	}
	return missing, failedPresent, nil
}

// regeneratePredixyConfServers 不支持 config rewrite 时, 依据内存(info servers)中的 backends
// 整体重建 predixy 配置文件中的 Servers {} 块(其余配置原样保留).
// CurrentIsFail == 1 的 server 不写入配置文件, 避免重启后继续读取失败 backend.
func regeneratePredixyConfServers(confFile string, infoServers []*myredis.PredixyInfoServer) error {
	confBytes, err := os.ReadFile(confFile)
	if err != nil {
		return fmt.Errorf("read predixy conf(%s) failed,err:%v", confFile, err)
	}
	confData := string(confBytes)

	servers := make([]string, 0, len(infoServers))
	for _, svr := range infoServers {
		if svr.CurrentIsFail != 1 {
			servers = append(servers, svr.Server)
		}
	}
	if len(servers) == 0 {
		return fmt.Errorf("no server in memory,refuse to rewrite predixy conf(%s) Servers block", confFile)
	}
	if _, err = extractPredixyServersBlock(confData); err != nil {
		return fmt.Errorf("predixy conf(%s) %v", confFile, err)
	}

	var blk strings.Builder
	blk.WriteString("Servers {\n")
	for _, svr := range servers {
		blk.WriteString(fmt.Sprintf("        + %s\n", svr))
	}
	blk.WriteString("    }")

	newConf := predixyServersBlockRe.ReplaceAllLiteralString(confData, blk.String())
	if err = backupConfFile(confFile, confBytes); err != nil {
		return err
	}
	if err = os.WriteFile(confFile, []byte(newConf), 0644); err != nil {
		return fmt.Errorf("write predixy conf(%s) failed,err:%v", confFile, err)
	}
	util.LocalDirChownMysql(confFile)
	return nil
}

func backupConfFile(confFile string, confBytes []byte) error {
	fileInfo, err := os.Stat(confFile)
	if err != nil {
		return fmt.Errorf("stat conf(%s) failed,err:%v", confFile, err)
	}
	backupFile := confFile + "." + time.Now().Format(consts.FilenameTimeLayout) + ".bak"
	if err = os.WriteFile(backupFile, confBytes, fileInfo.Mode().Perm()); err != nil {
		return fmt.Errorf("backup conf(%s) to %s failed,err:%v", confFile, backupFile, err)
	}
	util.LocalDirChownMysql(backupFile)
	return nil
}

// checkAndSyncTwemproxyConf 校验并(必要时)回写 twemproxy 配置文件
func (job *ProxyVersionUpgrade) checkAndSyncTwemproxyConf() (err error) {
	confFile, err := myredis.GetTwemproxyLocalConfFile(job.params.Port)
	if err != nil {
		return err
	}
	if confFile == "" {
		err = fmt.Errorf("twemproxy(%s:%d) local conf file not found", job.params.IP, job.params.Port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	// 内存中的 backends (get nosqlproxy servers)
	backendList, _, err := myredis.GetTwemproxyBackendsDecoded(job.params.IP, job.params.Port)
	if err != nil {
		return err
	}
	missing, err := twemproxyConfMissingBackends(confFile, backendList)
	if err != nil {
		return err
	}
	if len(missing) == 0 {
		job.runtime.Logger.Info("twemproxy(%s:%d) conf consistent with memory,missing=0,skip sync",
			job.params.IP, job.params.Port)
		return nil
	}
	job.runtime.Logger.Warn(
		"twemproxy(%s:%d) conf(%s) stale,backends missing in conf:%v,will sync from memory",
		job.params.IP, job.params.Port, confFile, missing)
	// 先尝试 config rewrite: 若该 twemproxy 版本支持, 直接让其把内存路由落盘.
	// 不支持/失败, 或落盘后磁盘仍与内存不一致, 则回退到依据内存重建配置文件 servers 段.
	rwErr := job.twemproxyConfigRewrite()
	if rwErr == nil {
		missing, err = twemproxyConfMissingBackends(confFile, backendList)
		if err != nil {
			return err
		}
	}
	if rwErr != nil || len(missing) != 0 {
		if rwErr != nil {
			job.runtime.Logger.Warn("twemproxy(%s:%d) config rewrite not applicable(%v),regenerate conf servers from memory",
				job.params.IP, job.params.Port, rwErr)
		} else {
			job.runtime.Logger.Warn("twemproxy(%s:%d) config rewrite did not persist backends,regenerate conf servers from memory",
				job.params.IP, job.params.Port)
		}
		if err = syncTwemproxyConfFromMemory(confFile, backendList); err != nil {
			return fmt.Errorf("sync twemproxy(%s:%d) conf from memory failed,err:%v", job.params.IP, job.params.Port, err)
		}
	} else {
		job.runtime.Logger.Info("twemproxy(%s:%d) conf synced via 'config rewrite'", job.params.IP, job.params.Port)
	}
	// 回写后复核
	missing, err = twemproxyConfMissingBackends(confFile, backendList)
	if err != nil {
		return err
	}
	if len(missing) != 0 {
		return fmt.Errorf("after sync,twemproxy(%s:%d) conf still missing backends:%v",
			job.params.IP, job.params.Port, missing)
	}
	job.runtime.Logger.Info("twemproxy(%s:%d) conf synced from memory and verified ok", job.params.IP, job.params.Port)
	return nil
}

// twemproxyConfigRewrite 尝试在 twemproxy 服务端口上执行 config rewrite.
func (job *ProxyVersionUpgrade) twemproxyConfigRewrite() (err error) {
	addr := fmt.Sprintf("%s:%d", job.params.IP, job.params.Port)
	cli, err := myredis.NewRedisClient(addr, job.params.Password, 0, consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return err
	}
	defer cli.Close()
	_, err = cli.ConfigRewrite()
	return err
}

// twemproxyConfMissingBackends 返回内存(get nosqlproxy servers)中出现、但磁盘配置 servers 段中缺失的 backend addr 列表.
// 比对范围限定在 servers 列表内, 避免与文件其它位置(如 listen) 误匹配.
func twemproxyConfMissingBackends(confFile string, backendList []myredis.TwemproxyBackendItem) ([]string, error) {
	tConf := common.NewTwemproxyConf()
	if err := tConf.Load(confFile); err != nil {
		return nil, fmt.Errorf("load twemproxy conf(%s) failed,err:%v", confFile, err)
	}
	serversBlock := strings.Join(tConf.NosqlProxy.Servers, "\n")
	var missing []string
	for _, backend := range backendList {
		if !strings.Contains(serversBlock, backend.Addr) {
			missing = append(missing, backend.Addr)
		}
	}
	return missing, nil
}

// twemproxyServersBlockRe 匹配 twemproxy 配置中的 servers 列表块.
// twemproxy 对 servers 列表缩进较敏感, 写回时固定使用:
//
//	servers:
//	 - addr:port:1 app start-end 1
var twemproxyServersBlockRe = regexp.MustCompile(`(?m)^\s*servers:\s*\n(?:\s*-\s.*(?:\n|$))*`)

// syncTwemproxyConfFromMemory 依据内存 backends 重建 twemproxy 配置中的 servers 列表.
// 内存 (get nosqlproxy servers) 为路由真值, 重建后经 CheckServersValid (含 bucket 总和校验) 通过才落盘.
func syncTwemproxyConfFromMemory(confFile string, backendList []myredis.TwemproxyBackendItem) error {
	tConf := common.NewTwemproxyConf()
	if err := tConf.Load(confFile); err != nil {
		return fmt.Errorf("load twemproxy conf(%s) failed,err:%v", confFile, err)
	}
	newServers := make([]string, 0, len(backendList))
	for _, backend := range backendList {
		// 配置行格式: addr:weight app start-end status, 权重与状态固定为 1 (与配置生成保持一致)
		newServers = append(newServers, fmt.Sprintf("%s:1 %s %d-%d 1",
			backend.Addr, backend.App, backend.SegStart, backend.SegEnd))
	}
	if err := tConf.CheckServersValid(newServers); err != nil {
		return fmt.Errorf("rebuilt twemproxy servers invalid,err:%v,servers:%v", err, newServers)
	}
	if err := replaceTwemproxyServersBlock(confFile, newServers); err != nil {
		return err
	}
	util.LocalDirChownMysql(confFile)
	return nil
}

// replaceTwemproxyServersBlock 仅替换原配置文件中的 servers 列表块, 其它配置原样保留.
// 不使用 yaml.Marshal, 避免生成 twemproxy 无法接受的列表缩进.
func replaceTwemproxyServersBlock(confFile string, servers []string) error {
	confBytes, err := os.ReadFile(confFile)
	if err != nil {
		return fmt.Errorf("read twemproxy conf(%s) failed,err:%v", confFile, err)
	}
	confData := string(confBytes)
	locs := twemproxyServersBlockRe.FindAllStringIndex(confData, -1)
	if len(locs) != 1 {
		return fmt.Errorf("expect exactly 1 'servers:' block in twemproxy conf(%s),got %d", confFile, len(locs))
	}

	var blk strings.Builder
	blk.WriteString("  servers:\n")
	for _, svr := range servers {
		blk.WriteString(fmt.Sprintf("   - %s\n", svr))
	}
	newConf := confData[:locs[0][0]] + blk.String() + confData[locs[0][1]:]
	if err = os.WriteFile(confFile, []byte(newConf), 0644); err != nil {
		return fmt.Errorf("write twemproxy conf(%s) failed,err:%v", confFile, err)
	}
	return nil
}

// Retry times
func (job *ProxyVersionUpgrade) Retry() uint {
	return 2
}

// Rollback rollback
func (job *ProxyVersionUpgrade) Rollback() error {
	return nil
}
