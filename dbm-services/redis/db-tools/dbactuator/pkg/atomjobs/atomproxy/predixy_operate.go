package atomproxy

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"time"

	"github.com/go-playground/validator/v10"
)

// PredixyDir preidxy dir
const PredixyDir = "predixy"

// PredixyOperateParams 启停参数
type PredixyOperateParams struct {
	// common.MediaPkg
	// 	DataDirs      []string          `json:"data_dirs"` //  /data /data1
	IP      string `json:"ip" validate:"required"`
	Port    int    `json:"port" validate:"required"` //  只支持1个端口
	Operate string `json:"operate" validate:"required"`
	Debug   bool   `json:"debug"`
}

// PredixyOperate install Predixy 原子任务
type PredixyOperate struct {
	runtime *jobruntime.JobGenericRuntime
	params  *PredixyOperateParams
}

// NewPredixyOperate new
func NewPredixyOperate() jobruntime.JobRunner {
	return &PredixyOperate{}
}

// Init 初始化
func (job *PredixyOperate) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("PredixyOperate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("PredixyOperate Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if job.params.Port < PredixyPortMin || job.params.Port > PredixyPortMax {
		err = fmt.Errorf("checkParams. Port(%d) must in range [%d,%d]", job.params.Port, PredixyPortMin, PredixyPortMax)
		job.runtime.Logger.Error(err.Error())
		return err
	}

	return nil
}

// Name 原子任务名
func (job *PredixyOperate) Name() string {
	return "predixy_operate"
}

// Run 执行
func (job *PredixyOperate) Run() (err error) {
	port := job.params.Port
	op := job.params.Operate
	execUser := consts.MysqlAaccount
	binPath := getPathWitChRoot("", consts.UsrLocal, PredixyDir, "bin")
	stopScript := filepath.Join(binPath, "stop_predixy.sh")
	startScript := filepath.Join(binPath, "start_predixy.sh")
	cmd := []string{}

	running, err := job.IsPredixyRunning(port)
	if err != nil {
		return nil
	}
	job.runtime.Logger.Info("check predixy %d before exec cmd. status is %s", port, running)
	if op == consts.ProxyStart {
		if running {
			return nil
		}
		cmd = []string{"su", execUser, "-c", fmt.Sprintf("%s %s", startScript, strconv.Itoa(port))}
	} else {
		// stop or shutdown
		if !running {
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

	running, err = job.IsPredixyRunning(port)
	job.runtime.Logger.Info("check predixy %d after exec cmd. status is %s", port, running)
	if running && op == consts.ProxyStart {
		return nil
	} else if !running && op == consts.ProxyStop {
		return nil
	} else if !running && op == consts.ProxyShutdown {
		// 删除Exporter配置文件，删除失败有Warn，但不会停止
		if err := common.DeleteExporterConfigFile(port); err != nil {
			job.runtime.Logger.Warn("predixy %d DeleteExporterConfigFile return err:%v", port, err)
		} else {
			job.runtime.Logger.Info("predixy %d DeleteExporterConfigFile success", port)
		}
		return job.DirBackup(execUser, port)
	} else {
		return err
	}
}

// Retry times
func (job *PredixyOperate) Retry() uint {
	return 2
}

// Rollback rollback
func (job *PredixyOperate) Rollback() error {
	return nil
}

// IsPredixyRunning 检查进程
func (job *PredixyOperate) IsPredixyRunning(port int) (installed bool, err error) {
	portIsUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	return portIsUse, err
}

// DirBackup 备份目录
func (job *PredixyOperate) DirBackup(execUser string, port int) error {
	job.runtime.Logger.Info("mv %d dir begin.", port)
	if job.params.Debug {
		return nil
	}
	dataDir := getPathWitChRoot("", consts.DataPath, PredixyDir)
	insDir := fmt.Sprintf("%s/%d", dataDir, port)
	// 判断目录是否存在
	job.runtime.Logger.Info("check predixy ins dir[%s] exists.", insDir)
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
		job.runtime.Logger.Info("mv Predixy port[%d] dir succ....", port)
		return nil
	}
	job.runtime.Logger.Info("mv Predixy port[%d] dir faild....", port)
	return fmt.Errorf("Predixy port[%d] dir [%s] exists too..pleace check", port, insDir)
}
