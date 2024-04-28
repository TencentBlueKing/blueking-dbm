package atomsys

import (
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/pkg/errors"

	"github.com/go-playground/validator/v10"
)

// ChangePwdParams 修改密码参数
// 传进来的实例。新老密码可能不一致，所以要求传一个数组进来
type ChangePwdParams struct {
	IP       string     `json:"ip" validate:"required"`
	Role     string     `json:"role" validate:"required"`
	InsParam []InsParam `json:"ins_param" validate:"required"`
}

// InsParam 实例相关参数
type InsParam struct {
	Port        int    `json:"port" validate:"required"`
	OldPassword string `json:"old_password" validate:"required"`
	NewPassword string `json:"new_password" validate:"required"`
}

// ChangePwd atomjob
type ChangePwd struct {
	runtime *jobruntime.JobGenericRuntime
	params  ChangePwdParams

	errChan chan error
}

// NewChangePassword new
func NewChangePassword() jobruntime.JobRunner {
	return &ChangePwd{}
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ChangePwd)(nil)

// Init 初始化
func (job *ChangePwd) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("ChangePwd Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ChangePwd Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *ChangePwd) Name() string {
	return "change_password"
}

// Run 执行
func (job *ChangePwd) Run() (err error) {
	params := job.params.InsParam
	for _, param := range params {
		if job.params.Role == consts.MetaRoleRedisMaster ||
			job.params.Role == consts.MetaRoleRedisSlave {
			err = job.changeRedisPwd(param.Port, param.OldPassword, param.NewPassword)
			if err != nil {
				return err
			}
		} else {
			err = job.changeProxyPwd(param.Port, param.OldPassword, param.NewPassword)
			if err != nil {
				return err
			}
		}
		// 检查新密码是否能够连接
		err = job.checkConn(param.Port, param.NewPassword)
		if err != nil {
			return err
		}
	}

	return nil
}

func (job *ChangePwd) changeProxyPwd(port int, oldPwd string, newPwd string) error {
	// 修改proxy配置文件
	// twemproxy 配置文件路径:/data/twemproxy-0.2.4/${port}/nutcracker.${port}.yml -> password: oldPwd
	// predixy 修改：/data/predixy/${port}/predixy.conf -> Auth
	var confFile, oldPwdReplaceStr, newPwdReplaceStr, sedCmd string
	var err error
	if job.params.Role == consts.MetaRoleTwemproxy {
		confFile, err = myredis.GetTwemproxyLocalConfFile(port)
		if err != nil {
			return err
		}
		oldPwdReplaceStr = fmt.Sprintf("password: %s", oldPwd)
		newPwdReplaceStr = fmt.Sprintf("password: %s", newPwd)

		sedCmd = fmt.Sprintf(`sed -i 's/%s/%s/' %s`, oldPwdReplaceStr, newPwdReplaceStr, confFile)
	} else if job.params.Role == consts.MetaRolePredixy {
		confFile, err = myredis.GetPredixyLocalConfFile(port)
		if err != nil {
			return err
		}
		oldPwdReplaceStr = fmt.Sprintf("Auth \"%s\"", oldPwd)
		newPwdReplaceStr = fmt.Sprintf("Auth \"%s\"", newPwd)

		// predixy admin密码可能和write密码一样，所以这个地方只改第一个
		//sed '/Mode write/{x;s/oldPwdReplaceStr/newPwdReplaceStr/;x};h'
		//sed -e ':a' -e 'N;$!ba' -e 's/\(%s\)\(.*Mode write\)/newPwdReplaceStr\2/'
		//上面这几种办法，在执行的时候都会遇到问题，所以这里先写死只匹配第7行
		sedCmd = fmt.Sprintf(`sed -i '7s/%s/%s/' %s`, oldPwdReplaceStr, newPwdReplaceStr, confFile)
	} else {
		return errors.Errorf("Unknown  proxy type[%+v]", job.params.Role)
	}
	job.runtime.Logger.Info("get proxy local config file (%s:%d) success", job.params.IP, port)
	job.runtime.Logger.Info("Run sedCmd:%s", sedCmd)
	_, err = util.RunBashCmd(sedCmd, "", nil, 10*time.Second)
	if err != nil {
		job.runtime.Logger.Warn("new password replace old password (%s:%d) Warning. old password maybe error",
			job.params.IP, port)
	} else {
		job.runtime.Logger.Info("new password replace old password (%s:%d) success", job.params.IP, port)
	}

	// 检查是否修改成功
	pwd, err := myredis.GetProxyPasswdFromConfFlie(port, job.params.Role)
	if err != nil {
		return nil
	}
	if pwd != newPwd {
		return errors.Errorf("change config file password failed. not restart")
	}
	job.runtime.Logger.Info("GetProxyPasswdFromConfFlie (%s:%d) success", job.params.IP, port)

	// 重启proxy实例
	err = job.stopProxy(port)
	if err != nil {
		return err
	}
	err = job.startProxy(port, newPwd)
	if err != nil {
		return err
	}

	return nil
}

// stopProxy 关闭 proxy
func (job *ChangePwd) stopProxy(port int) (err error) {
	stopScript := ""
	if job.params.Role == consts.MetaRolePredixy {
		stopScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "stop_predixy.sh")
	} else if job.params.Role == consts.MetaRoleTwemproxy {
		stopScript = filepath.Join(consts.UsrLocal, "twemproxy", "bin", "stop_nutcracker.sh")
	}
	_, err = os.Stat(stopScript)
	if err != nil && os.IsNotExist(err) {
		job.runtime.Logger.Info("%s not exist", stopScript)
		return nil
	}
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s %d\"",
		consts.MysqlAaccount, stopScript, port))

	maxRetryTimes := 5
	inUse := false
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		_, err = util.RunLocalCmd("su",
			[]string{consts.MysqlAaccount, "-c", stopScript + " " + strconv.Itoa(port)},
			"", nil, 10*time.Minute)
		if err != nil {
			return err
		}
		// 暂停3s,避免检查错误
		time.Sleep(3 * time.Second)
		inUse, err = util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
		if err != nil {
			job.runtime.Logger.Error(fmt.Sprintf("check %s:%d inUse failed,err:%v", job.params.IP, port, err))
			return err
		}
		if !inUse {
			break
		}
		job.runtime.Logger.Error(fmt.Sprintf("stop %s (%s:%d) failed,port:%d still using. will continue stop",
			job.params.Role, job.params.IP, port, port))
		time.Sleep(2 * time.Second)
	}
	if inUse {
		err = fmt.Errorf("stop %s (%s:%d) failed,port:%d still using",
			job.params.Role, job.params.IP, port, port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("stop %s (%s:%d) success",
		job.params.Role, job.params.IP, port)
	return nil
}

// startProxy 拉起 proxy
func (job *ChangePwd) startProxy(port int, pwd string) (err error) {
	startScript := ""
	if job.params.Role == consts.MetaRolePredixy {
		startScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "start_predixy.sh")
	} else if job.params.Role == consts.MetaRoleTwemproxy {
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
	job.runtime.Logger.Info("start proxy (%s:%d) success", job.params.IP, port)
	return nil
}

// changeRedisPwd 修改密码
func (job *ChangePwd) changeRedisPwd(port int, oldPwd string, newPwd string) error {
	// 连接redis执行config masterauth 和 requirepass
	insAddr := fmt.Sprintf("%s:%d", job.params.IP, port)
	redisClient, err := myredis.NewRedisClient(insAddr, oldPwd, 0, consts.TendisTypeRedisInstance)
	defer redisClient.Close()
	if err != nil {
		return err
	}

	if job.params.Role == consts.MetaRoleRedisSlave {
		_, err = redisClient.ConfigSet("masterauth", newPwd)
		if err != nil {
			return err
		}
		job.runtime.Logger.Info("config set masterauth (%s:%d) success", job.params.IP, port)
	}

	_, err = redisClient.ConfigSet("requirepass", newPwd)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("config set requirepass (%s:%d) success", job.params.IP, port)

	// 做一次config rewrite 重写redis配置文件
	_, err = redisClient.ConfigRewrite()
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("rewrite config (%s:%d) success", job.params.IP, port)

	cli, err := myredis.NewRedisClientWithTimeout(insAddr, newPwd, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	defer cli.Close()
	job.runtime.Logger.Info("use new password conn (%s:%d) success", job.params.IP, port)

	return nil
}

// checkConn 检查用新密码是否能正常连接
func (job *ChangePwd) checkConn(port int, pwd string) error {
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli, err := myredis.NewRedisClientWithTimeout(addr, pwd, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	defer cli.Close()

	return err
}

// Retry times
func (job *ChangePwd) Retry() uint {
	return 2
}

// Rollback rollback
func (job *ChangePwd) Rollback() error {
	return nil
}
