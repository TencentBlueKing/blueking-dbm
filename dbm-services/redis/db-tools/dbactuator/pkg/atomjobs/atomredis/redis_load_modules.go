package atomredis

import (
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisLoadModulesParams load module的参数
type RedisLoadModulesParams struct {
	RedisModulesPkg   common.RedisModulesMediaPkg `json:"redis_modules_pkg"`
	IP                string                      `json:"ip" validate:"required"`
	Ports             []int                       `json:"ports" validate:"required"`
	LoadModulesDetail []LoadModuleItem            `json:"load_modules_detail" validate:"required"`
}

// RedisLoadModules TODO
type RedisLoadModules struct {
	runtime           *jobruntime.JobGenericRuntime
	params            RedisLoadModulesParams
	AddrMapCli        map[string]*myredis.RedisClient `json:"addr_map_cli"`
	AddrMapConfigFile map[string]string               `json:"addr_map_config_file"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisLoadModules)(nil)

// NewRedisLoadModules new
func NewRedisLoadModules() jobruntime.JobRunner {
	return &RedisLoadModules{}
}

// Init 初始化
func (job *RedisLoadModules) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisLoadModules Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisLoadModules Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisLoadModules) Name() string {
	return "redis_load_modules"
}

// Run 执行
func (job *RedisLoadModules) Run() (err error) {
	err = job.allInstsAbleToConnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()
	// 解压redis modules
	err = job.params.RedisModulesPkg.UnTar()
	if err != nil {
		return err
	}
	// 确保module so文件存在
	err = job.isModulesSoFileExists()
	if err != nil {
		return err
	}
	soFile := ""
	for _, cli := range job.AddrMapCli {
		for _, moduleItem := range job.params.LoadModulesDetail {
			soFile = filepath.Join(consts.RedisModulePath, moduleItem.SoFile)
			err = cli.ModuleLoad(soFile)
			if err != nil {
				job.runtime.Logger.Error(fmt.Sprintf("redis:%s load module(%s) fail,err:%v",
					cli.Addr, moduleItem.SoFile, err))
				return
			}
		}
	}
	for addr, cli := range job.AddrMapCli {
		// config rewrite
		_, err = cli.ConfigRewrite()
		if err != nil {
			return err
		}
		// 确保loadmodule $sofile 保存到配置文件中
		confFile, _ := job.AddrMapConfigFile[addr]
		for _, moduleItem := range job.params.LoadModulesDetail {
			soFile = filepath.Join(consts.RedisModulePath, moduleItem.SoFile)
			err = util.SaveKvToConfigFile(confFile, "loadmodule", soFile)
			if err != nil {
				job.runtime.Logger.Error(fmt.Sprintf("redis:%s load module(%s) fail,err:%v",
					cli.Addr, moduleItem.SoFile, err))
				return
			}
		}
	}
	return nil
}

// isModulesSoFileExists 判断module so文件是否存在
func (job *RedisLoadModules) isModulesSoFileExists() (err error) {
	if len(job.params.LoadModulesDetail) == 0 {
		err = fmt.Errorf("params load_modules_detail empty, %+v", job.params.LoadModulesDetail)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	// 确认module so文件存在
	soFile := ""
	for _, moduleItem := range job.params.LoadModulesDetail {
		soFile = filepath.Join(consts.RedisModulePath, moduleItem.SoFile)
		if !util.FileExists(soFile) {
			err = errors.New(fmt.Sprintf("module(%s) not exists", soFile))
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	return nil
}

// allInstsAbleToConnect 检查所有实例可连接
func (job *RedisLoadModules) allInstsAbleToConnect() (err error) {
	var addr, password, confFile string
	instsAddrs := make([]string, 0, len(job.params.Ports))
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	job.AddrMapConfigFile = make(map[string]string, len(job.params.Ports))
	for _, port := range job.params.Ports {
		// addr = fmt.Sprintf("%s:%d", job.params.IP, port)
		// 因为 Redis-7 以上版本, enable-module-command local,所以需要用 "127.0.0.1" 作为地址
		addr = fmt.Sprintf("%s:%d", "127.0.0.1", port)
		instsAddrs = append(instsAddrs, addr)
		// 获取配置文件
		confFile, err = myredis.GetRedisLoccalConfFile(port)
		if err != nil {
			return err
		}
		job.AddrMapConfigFile[addr] = confFile
		// 获取密码
		password, err = myredis.GetRedisPasswdFromConfFile(port)
		if err != nil {
			return err
		}
		cli, err := myredis.NewRedisClientWithTimeout(addr, password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if err != nil {
			return err
		}
		job.AddrMapCli[addr] = cli
	}
	job.runtime.Logger.Info("all redis instances able to connect,(%+v)", instsAddrs)
	return nil
}

// allInstDisconnect 所有实例断开连接
func (job *RedisLoadModules) allInstDisconnect() {
	for _, cli := range job.AddrMapCli {
		cli.Close()
	}
}

// Retry times
func (job *RedisLoadModules) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisLoadModules) Rollback() error {
	return nil
}
