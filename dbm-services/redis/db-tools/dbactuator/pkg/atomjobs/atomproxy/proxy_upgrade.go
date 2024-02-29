package atomproxy

import (
	"encoding/json"
	"fmt"
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
	err = myredis.LocalRedisConnectTest(job.params.IP, []int{job.params.Port}, job.params.Password)
	if err != nil {
		return err
	}
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
	cli, err := myredis.NewRedisClientWithTimeout(addr, job.params.Password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	defer cli.Close()
	job.runtime.Logger.Info("start proxy (%s:%d) success", job.params.IP, port)
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
