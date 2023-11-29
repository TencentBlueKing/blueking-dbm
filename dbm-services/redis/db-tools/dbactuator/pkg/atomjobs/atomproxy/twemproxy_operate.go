package atomproxy

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

/*
	TwemproxyInstall 原子任务
	twemproxy进程启停
*/

//

// TwemproxyOperateParams 启停参数
type TwemproxyOperateParams struct {
	// common.MediaPkg
	// 	DataDirs      []string          `json:"data_dirs"` //  /data /data1
	IP      string `json:"ip" validate:"required"`
	Port    int    `json:"port" validate:"required"` //  只支持1个端口
	Operate string `json:"operate" validate:"required"`
	Debug   bool   `json:"debug"`
}

// TwemproxyOperate install twemproxy 原子任务
type TwemproxyOperate struct {
	runtime *jobruntime.JobGenericRuntime
	params  *TwemproxyOperateParams
}

// NewTwemproxyOperate new
func NewTwemproxyOperate() jobruntime.JobRunner {
	return &TwemproxyOperate{}
}

// Init 初始化
func (job *TwemproxyOperate) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("TwemproxyOperate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("TwemproxyOperate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if job.params.Port < twemproxyPortMin || job.params.Port > twemproxyPortMax {
		err = fmt.Errorf("checkParams. Port(%d) must in range [%d,%d]", job.params.Port, twemproxyPortMin, twemproxyPortMax)
		job.runtime.Logger.Error(err.Error())
		return err
	}

	return nil
}

// Name 原子任务名
func (job *TwemproxyOperate) Name() string {
	return "twemproxy_operate"
}

// Run 执行
func (job *TwemproxyOperate) Run() (err error) {
	port := job.params.Port
	op := job.params.Operate
	execUser := consts.MysqlAaccount
	binPath := getPathWitChRoot("", consts.UsrLocal, "twemproxy", "bin")
	stopScript := filepath.Join(binPath, "stop_nutcracker.sh")
	startScript := filepath.Join(binPath, "start_nutcracker.sh")
	var cmd []string

	running, err := job.IsTwemproxyRunning(port)
	job.runtime.Logger.Info("check twemproxy %d before exec cmd. status is %s", port, running)
	if err != nil {
		return nil
	}
	if op == consts.ProxyStart {
		if running {
			return nil
		}
		cmd = []string{"su", execUser, "-c", fmt.Sprintf("%s %s", startScript, strconv.Itoa(port))}
	} else {
		// stop or shutdown
		if !running {
			// 如果是shutdown,此时需要清理相关目录
			if op == consts.ProxyShutdown {
				if err := common.DeleteExporterConfigFile(port); err != nil {
					job.runtime.Logger.Warn("twemproxy %d DeleteExporterConfigFile return err:%v", port, err)
				} else {
					job.runtime.Logger.Info("twemproxy %d DeleteExporterConfigFile success", port)
				}

				return job.DirBackup(execUser, port)
			}
			return nil
		}
		cmd = []string{"su", execUser, "-c", fmt.Sprintf("%s %s", stopScript, strconv.Itoa(port))}
	}
	_, err = util.RunLocalCmd(cmd[0], cmd[1:], "",
		nil, 10*time.Second)
	job.runtime.Logger.Info(fmt.Sprintf("%s Process %s", op, cmd))
	if err != nil {
		return err
	}
	time.Sleep(5 * time.Second)

	// 二次检查进程状态
	running, err = job.IsTwemproxyRunning(port)
	job.runtime.Logger.Info("check twemproxy %d after exec cmd. status is %s", port, running)
	if running && op == consts.ProxyStart {
		return nil
	} else if !running && op == consts.ProxyStop {
		return nil
	} else if !running && op == consts.ProxyShutdown {

		// 删除Exporter配置文件，删除失败有Warn，但不会停止
		if err := common.DeleteExporterConfigFile(port); err != nil {
			job.runtime.Logger.Warn("twemproxy %d DeleteExporterConfigFile return err:%v", port, err)
		} else {
			job.runtime.Logger.Info("twemproxy %d DeleteExporterConfigFile success", port)
		}

		return job.DirBackup(execUser, port)
	} else {
		return err
	}
}

// Retry times
func (job *TwemproxyOperate) Retry() uint {
	return 2
}

// Rollback rollback
func (job *TwemproxyOperate) Rollback() error {
	return nil
}

// IsTwemproxyRunning 检查进程
func (job *TwemproxyOperate) IsTwemproxyRunning(port int) (installed bool, err error) {
	portIsUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	return portIsUse, err
}

// DirBackup 备份目录
func (job *TwemproxyOperate) DirBackup(execUser string, port int) error {
	job.runtime.Logger.Info("mv %d dir begin.", port)
	if job.params.Debug {
		return nil
	}
	dataDir := getPathWitChRoot("", consts.DataPath, twemproxyDir)
	insDir := fmt.Sprintf("%s/%d", dataDir, port)
	// 判断目录是否存在
	job.runtime.Logger.Info("check twemproxy ins dir[%s] exists.", insDir)
	exist := util.FileExists(insDir)
	if !exist {
		job.runtime.Logger.Info("dir %s is not exists", insDir)
		return nil
	}
	mvCmd := fmt.Sprintf("mv %s/%d %s/bak_%d_%s", dataDir, port, dataDir, port, time.Now().Format("20060102150405"))
	job.runtime.Logger.Info(mvCmd)
	cmd := []string{"su", execUser, "-c", mvCmd}
	_, _ = util.RunLocalCmd(cmd[0], cmd[1:], "",
		nil, 10*time.Second)
	time.Sleep(10 * time.Second)
	exist = util.FileExists(insDir)
	if !exist {
		job.runtime.Logger.Info("mv twemproxy port[%d] dir succ....", port)
		return nil
	}
	job.runtime.Logger.Info("mv twemproxy port[%d] dir faild....", port)
	return fmt.Errorf("twemproxy port[%d] dir [%s] exists too..pleace check", port, insDir)
}
