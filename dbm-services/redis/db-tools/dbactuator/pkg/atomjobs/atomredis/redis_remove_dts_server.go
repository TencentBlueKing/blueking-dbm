package atomredis

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RedisRemoveDtsServerParams 删除dts_server参数
type RedisRemoveDtsServerParams struct {
	common.MediaPkg
}

// RedisRemoveDtsServer 删除dts_server
type RedisRemoveDtsServer struct {
	runtime     *jobruntime.JobGenericRuntime
	params      *RedisRemoveDtsServerParams
	DataDir     string `json:"data_dir"`
	RedisDtsDir string `json:"redis_dts_dir"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisRemoveDtsServer)(nil)

// NewRedisRemoveDtsServer new
func NewRedisRemoveDtsServer() jobruntime.JobRunner {
	return &RedisRemoveDtsServer{}
}

// Init 初始化
func (job *RedisRemoveDtsServer) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisRemoveDtsServer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisRemoveDtsServer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisRemoveDtsServer) Name() string {
	return "redis_remove_dts_server"
}

// Run 执行
func (job *RedisRemoveDtsServer) Run() (err error) {
	err = job.getDataDir()
	if err != nil {
		return err
	}
	if !job.isDtsDirExists() {
		job.runtime.Logger.Warn("dts_server dir(%s) not exists,skip", job.RedisDtsDir)
		return nil
	}
	ok, err := job.ableToStopDtsServer()
	if err != nil {
		return err
	}
	if !ok {
		err = fmt.Errorf("redis_dts_server other tasks are running,can not stop")
		return
	}
	err = job.stopDtsServer()
	return err
}

func (job *RedisRemoveDtsServer) getDataDir() (err error) {
	job.DataDir = filepath.Join(consts.GetRedisDataDir(), "dbbak")
	util.MkDirsIfNotExists([]string{job.DataDir})
	util.LocalDirChownMysql(job.DataDir)
	return nil
}

func (job *RedisRemoveDtsServer) isDtsDirExists() bool {
	pkgBaseName := job.params.GePkgBaseName()
	job.RedisDtsDir = filepath.Join(job.DataDir, pkgBaseName)
	return util.FileExists(job.RedisDtsDir)
}

// ableToStopDtsServer 是否可以停止dts_server
func (job *RedisRemoveDtsServer) ableToStopDtsServer() (ok bool, err error) {
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

func (job *RedisRemoveDtsServer) stopDtsServer() (err error) {
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

// Retry times
func (job *RedisRemoveDtsServer) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisRemoveDtsServer) Rollback() error {
	return nil
}
