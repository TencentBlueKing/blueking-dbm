package atomredis

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisConfigSetParams 参数
type RedisConfigSetParams struct {
	IP               string            `json:"ip" validate:"required"`
	Ports            []int             `json:"ports" validate:"required"`
	ConfigSetMap     map[string]string `json:"config_set_map" validate:"required"`
	Role             string            `json:"role" validate:"required"`
	SyncToConfigFile bool              `json:"sync_to_config_file"`
}

// RedisConfigSet TODO
type RedisConfigSet struct {
	runtime           *jobruntime.JobGenericRuntime
	params            RedisConfigSetParams
	localPkgBaseName  string
	AddrMapCli        map[string]*myredis.RedisClient `json:"addr_map_cli"`
	AddrMapConfigFile map[string]string               `json:"addr_map_config_file"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisConfigSet)(nil)

// NewRedisConfigSet new
func NewRedisConfigSet() jobruntime.JobRunner {
	return &RedisConfigSet{}
}

// Init prepare run env
func (job *RedisConfigSet) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisConfigSet Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisConfigSet Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if len(job.params.Ports) == 0 {
		err = fmt.Errorf("RedisConfigSet Init ports(%+v) is empty", job.params.Ports)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// Name 原子任务名
func (job *RedisConfigSet) Name() string {
	return "redis_config_set"
}

// Run Command Run
func (job *RedisConfigSet) Run() (err error) {
	err = job.allInstsAbleToConnect()
	if err != nil {
		return err
	}
	defer job.allInstDisconnect()

	for _, cli := range job.AddrMapCli {
		for k, v := range job.params.ConfigSetMap {
			_, err = cli.ConfigSet(k, v)
			if err != nil {
				return err
			}
		}
	}
	if job.params.SyncToConfigFile {
		for addr, cli := range job.AddrMapCli {
			_, err = cli.ConfigRewrite()
			if err != nil {
				return err
			}
			confFile, _ := job.AddrMapConfigFile[addr]
			for k, v := range job.params.ConfigSetMap {
				err = job.syncToConfigFile(confFile, k, v)
				if err != nil {
					return err
				}
			}
		}
	}
	return nil
}

// syncToConfigFile 同步到本地配置文件
func (job *RedisConfigSet) syncToConfigFile(confFile, item, value string) (err error) {
	return util.SaveKvToConfigFile(confFile, item, value)
}

// allInstsAbleToConnect 检查所有实例可连接
func (job *RedisConfigSet) allInstsAbleToConnect() (err error) {
	var addr, password, confFile string
	instsAddrs := make([]string, 0, len(job.params.Ports))
	job.AddrMapCli = make(map[string]*myredis.RedisClient, len(job.params.Ports))
	job.AddrMapConfigFile = make(map[string]string, len(job.params.Ports))
	for _, port := range job.params.Ports {
		addr = fmt.Sprintf("%s:%d", job.params.IP, port)
		instsAddrs = append(instsAddrs, addr)
		// 获取配置文件
		if job.params.Role == consts.MetaRolePredixy {
			confFile, err = myredis.GetPredixyLocalConfFile(port)
		} else if job.params.Role == consts.MetaRoleTwemproxy {
			confFile, err = myredis.GetTwemproxyLocalConfFile(port)
		} else {
			confFile, err = myredis.GetRedisLoccalConfFile(port)
		}
		if err != nil {
			return err
		}
		job.AddrMapConfigFile[addr] = confFile
		// 获取密码
		if job.params.Role == consts.MetaRolePredixy {
			password, err = myredis.GetPredixyAdminPasswdFromConfFlie(port)
		} else if job.params.Role == consts.MetaRoleTwemproxy {
			password, err = myredis.GetProxyPasswdFromConfFlie(port, job.params.Role)
		} else {
			password, err = myredis.GetRedisPasswdFromConfFile(port)
		}
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
func (job *RedisConfigSet) allInstDisconnect() {
	for _, cli := range job.AddrMapCli {
		cli.Close()
	}
}

// Retry times
func (job *RedisConfigSet) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisConfigSet) Rollback() error {
	return nil
}
