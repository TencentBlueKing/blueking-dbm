package atomredis

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/flosch/pongo2/v6"
	"github.com/go-playground/validator/v10"
)

// RedisAddDtsServerParams 新增dts_server参数
type RedisAddDtsServerParams struct {
	common.MediaPkg
	BkDbmNginxURL       string `json:"bk_dbm_nginx_url" validate:"required"`
	BkDbmCloudID        int64  `json:"bk_dbm_cloud_id"`
	BkDbmCloudToken     string `json:"bk_dbm_cloud_token" validate:"required"`
	SystemUser          string `json:"system_user" validate:"required"`
	SystemPassword      string `json:"system_password" validate:"required"`
	CityName            string `json:"city_name" validate:"required"`
	WarningMsgNotifiers string `json:"warning_msg_notifiers"`
}

// RedisAddDtsServer  redis add dts_server
type RedisAddDtsServer struct {
	runtime            *jobruntime.JobGenericRuntime
	params             RedisAddDtsServerParams
	DataDir            string `json:"data_dir"`
	RedisDtsDir        string `json:"redis_dts_dir"`
	shouldUpdateMedia  bool
	shouldUpdateConfig bool
	tmpConfFile        string
	currentConfFile    string
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisAddDtsServer)(nil)

// NewRedisAddDtsServer new
func NewRedisAddDtsServer() jobruntime.JobRunner {
	return &RedisAddDtsServer{}
}

// Init 初始化
func (job *RedisAddDtsServer) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisInstall Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisInstall Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisAddDtsServer) Name() string {
	return "redis_add_dts_server"
}

// Run 执行
func (job *RedisAddDtsServer) Run() (err error) {
	var ok bool
	err = job.getDataDir()
	if err != nil {
		return err
	}
	if job.isDtsDirExists() && job.isPackageMd5Equal() {
		err = job.GenerateTmpConfigFile()
		if err != nil {
			return err
		}
		job.shouldUpdateConfig, err = job.isConfigFileUpdated()
		if err != nil {
			return err
		}
		if !job.shouldUpdateConfig {
			// media md5 not changed and config file not changed
			job.runtime.Logger.Info("redis_dts_server package md5 not changed,not need to update")
			return nil
		}
	}
	if !job.isDtsDirExists() {
		// dts dir not exists
		err = job.UntarMedia()
		if err != nil {
			return err
		}
	}
	err = job.GenerateTmpConfigFile()
	if err != nil {
		return err
	}
	job.shouldUpdateConfig, err = job.isConfigFileUpdated()
	if err != nil {
		return err
	}
	ok, err = job.ableToStopDtsServer()
	if err != nil {
		return err
	}
	if !ok {
		err = fmt.Errorf("redis_dts_server other tasks are running,can not stop")
		return
	}
	err = job.stopDtsServer()
	if err != nil {
		return err
	}
	if !job.isPackageMd5Equal() {
		// dts dir exists but media md5 not equal
		err = job.UntarMedia()
		if err != nil {
			return err
		}
	}
	if job.shouldUpdateConfig {
		// update config file
		err = job.updateLocalConfigFile()
		if err != nil {
			return err
		}
	}
	err = job.startDtsServer()
	if err != nil {
		return err
	}

	return nil
}

func (job *RedisAddDtsServer) getDataDir() (err error) {
	job.DataDir = filepath.Join(consts.GetRedisDataDir(), "dbbak")
	util.MkDirsIfNotExists([]string{job.DataDir})
	util.LocalDirChownMysql(job.DataDir)
	return nil
}

func (job *RedisAddDtsServer) isDtsDirExists() bool {
	pkgBaseName := job.params.GePkgBaseName()
	job.RedisDtsDir = filepath.Join(job.DataDir, pkgBaseName)
	return util.FileExists(job.RedisDtsDir)
}

// isPackageMd5Equal 检查当前包的md5是否和上次一致
func (job *RedisAddDtsServer) isPackageMd5Equal() bool {
	baseName := filepath.Join(job.DataDir, job.params.GePkgBaseName())
	// /data/dbbak/redis_dts.tar.gz
	currentPackageFile := filepath.Join(job.DataDir, baseName+"tar.gz")
	// /data/install/redis_dts.tar.gz
	lastPackageFile := job.params.GetAbsolutePath()
	if !util.FileExists(currentPackageFile) {
		return false
	}
	currentPackageMd5, err := util.GetFileMd5(currentPackageFile)
	if err != nil {
		job.runtime.Logger.Error("get current package md5 failed,err:%v,packageFile:%s", err, currentPackageFile)
		return false
	}
	lastPackageMd5, err := util.GetFileMd5(lastPackageFile)
	if err != nil {
		job.runtime.Logger.Error("get last package md5 failed,err:%v,packageFile:%s", err, lastPackageFile)
		return false
	}
	if currentPackageMd5 != lastPackageMd5 {
		job.runtime.Logger.Error("current package file:%s,md5:%s not equal last package file:%s,md5:%s",
			currentPackageFile, currentPackageMd5, lastPackageFile, lastPackageMd5)
		return false
	}
	job.runtime.Logger.Error("current package file:%s,md5:%s equal last package file:%s,md5:%s",
		currentPackageFile, currentPackageMd5, lastPackageFile, lastPackageMd5)
	return false
}

// GenerateTmpConfigFile 生成临时配置文件
func (job *RedisAddDtsServer) GenerateTmpConfigFile() (err error) {
	job.runtime.Logger.Info("begin to generate redis dts config file")
	templateFile := filepath.Join(job.RedisDtsDir, "config-template.yaml")
	if !util.FileExists(templateFile) {
		err = fmt.Errorf("redis_dts_server config template file:%s not exists", templateFile)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	templdateData, err := ioutil.ReadFile(templateFile)
	if err != nil {
		err = fmt.Errorf("read redis_dts_server config template file:%s failed,err:%v", templateFile, err)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	tpl, err := pongo2.FromBytes(templdateData)
	if err != nil {
		err = fmt.Errorf("pongo2.FromString fail,err:%v,dts_server config template file:%s", err, templateFile)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	pctx01 := pongo2.Context{
		"bk_dbm_nginx_url":      job.params.BkDbmNginxURL,
		"bk_dbm_cloud_id":       strconv.FormatInt(job.params.BkDbmCloudID, 10),
		"bk_dbm_cloud_token":    job.params.BkDbmCloudToken,
		"system_user":           job.params.SystemUser,
		"system_password":       job.params.SystemPassword,
		"city_name":             job.params.CityName,
		"warning_msg_notifiers": job.params.WarningMsgNotifiers,
	}
	confData, err := tpl.Execute(pctx01)
	if err != nil {
		err = fmt.Errorf("tpl.Execute fail,err:%v,dts_server config template file:%s", err, templateFile)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.currentConfFile = filepath.Join(job.RedisDtsDir, "config.yaml")
	job.tmpConfFile = filepath.Join(job.RedisDtsDir, "tmp_config.yaml")
	err = ioutil.WriteFile(job.tmpConfFile, []byte(confData), 0644)
	if err != nil {
		err = fmt.Errorf("write redis_dts_server config file:%s failed,err:%v", job.tmpConfFile, err)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	util.LocalDirChownMysql(job.RedisDtsDir)
	job.runtime.Logger.Info("generate redis dts config file success")
	return nil
}

// isConfigFileUpdated 判断配置文件是否更新
func (job *RedisAddDtsServer) isConfigFileUpdated() (updated bool, err error) {
	if !util.FileExists(job.tmpConfFile) {
		return false, nil
	}
	if !util.FileExists(job.currentConfFile) {
		return true, nil
	}
	tmpFileMD5, err := util.GetFileMd5(job.tmpConfFile)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return false, err
	}

	confFileMD5, err := util.GetFileMd5(job.currentConfFile)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return false, err
	}
	if tmpFileMD5 != confFileMD5 {
		job.runtime.Logger.Info("tmp config file:%s md5:%s not equal current config file:%s md5:%s",
			job.tmpConfFile, tmpFileMD5, job.currentConfFile, confFileMD5)
		return true, nil
	}
	return false, nil
}

func (job *RedisAddDtsServer) updateLocalConfigFile() (err error) {
	if !util.FileExists(job.tmpConfFile) {
		err = fmt.Errorf("tmp config file:%s not exists", job.tmpConfFile)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	cpCmd := fmt.Sprintf("cp -f %s %s", job.tmpConfFile, job.currentConfFile)
	_, err = util.RunBashCmd(cpCmd, "", nil, 10*time.Minute)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// UntarMedia 解压介质,更新介质文件
func (job *RedisAddDtsServer) UntarMedia() (err error) {
	job.runtime.Logger.Info("begin to untar redis media")
	defer func() {
		if err != nil {
			job.runtime.Logger.Error("untar redis_dts_server media fail")
		} else {
			job.runtime.Logger.Info("untar redis_dts_server media success")
		}
	}()
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error("UntarMedia failed,err:%v", err)
		return
	}
	lastPkgAbsPath := job.params.GetAbsolutePath()
	tarCmd := fmt.Sprintf("tar -zxf %s -C %s", lastPkgAbsPath, job.DataDir)
	job.runtime.Logger.Info(tarCmd)
	_, err = util.RunBashCmd(tarCmd, "", nil, 10*time.Minute)
	if err != nil {
		return
	}
	util.LocalDirChownMysql(job.RedisDtsDir)

	// copy redis_dts.tar.gz to /data/dbbak/
	cpCmd := fmt.Sprintf("cp -f %s %s", lastPkgAbsPath, job.DataDir)
	job.runtime.Logger.Info(cpCmd)
	_, err = util.RunBashCmd(cpCmd, "", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	return nil
}

// ableToStopDtsServer 是否可以停止dts_server
func (job *RedisAddDtsServer) ableToStopDtsServer() (ok bool, err error) {
	psCmd :=
		"ps aux|grep 'redis_dts'|grep -vE 'dbactuator|grep|./redis_dts_server|redis-sync|redis-shake' || { true; }"
	job.runtime.Logger.Info(psCmd)
	output, err := util.RunBashCmd(psCmd, "", nil, 10*time.Second)
	if err != nil {
		job.runtime.Logger.Error("check redis_dts_server process failed,err:%v", err)
		return false, err
	}
	if output != "" {
		job.runtime.Logger.Error("redis_dts other tasks are running,can not stop.details:\n%s\n", output)
		return false, nil
	}
	return true, nil
}

func (job *RedisAddDtsServer) stopDtsServer() (err error) {
	job.runtime.Logger.Info("begin to stop redis_dts_server")
	defer func() {
		if err != nil {
			job.runtime.Logger.Error("stop redis_dts_server fail")
		} else {
			job.runtime.Logger.Info("stop redis_dts_server success")
		}
	}()
	stopCmd := fmt.Sprintf("cd %s && sh stop.sh", job.RedisDtsDir)
	job.runtime.Logger.Info(stopCmd)
	_, err = util.RunBashCmd(stopCmd, "", nil, 10*time.Second)
	if err != nil {
		return err
	}
	return nil
}

func (job *RedisAddDtsServer) startDtsServer() (err error) {
	job.runtime.Logger.Info("begin to start redis_dts_server")
	defer func() {
		if err != nil {
			job.runtime.Logger.Error("start redis_dts_server fail")
		} else {
			job.runtime.Logger.Info("start redis_dts_server success")
		}
	}()
	util.LocalDirChownMysql(job.RedisDtsDir)
	startCmd := fmt.Sprintf("su %s -c \"nohup cd %s && sh start.sh &\"", consts.MysqlAaccount, job.RedisDtsDir)
	job.runtime.Logger.Info(startCmd)
	_, err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", "cd " + job.RedisDtsDir +
		" && nohup sh start.sh  >/dev/null 2>&1 &"}, "", nil, 10*time.Second)
	if err != nil {
		return err
	}
	time.Sleep(2 * time.Second)
	alive, err := job.isDtsServerAlive()
	if err != nil {
		return err
	}
	if !alive {
		err = errors.New("redis_dts_server start failed")
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("redis_dts_server start success")
	return nil
}

func (job *RedisAddDtsServer) isDtsServerAlive() (alive bool, err error) {
	psCmd := "ps -ef|grep redis_dts_server|grep -ivE 'grep|redis-sync|redis-shake|dbactuator'"
	job.runtime.Logger.Info(psCmd)
	output, err := util.RunBashCmd(psCmd, "", nil, 10*time.Second)
	if err != nil {
		return false, err
	}
	if output == "" {
		return false, nil
	}
	return true, nil
}

// Retry times
func (job *RedisAddDtsServer) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisAddDtsServer) Rollback() error {
	return nil
}
