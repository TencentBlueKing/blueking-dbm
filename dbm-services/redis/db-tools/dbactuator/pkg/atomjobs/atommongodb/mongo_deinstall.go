package atommongodb

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// DeInstallConfParams 参数
type DeInstallConfParams struct {
	IP           string   `json:"ip" validate:"required"`
	Port         int      `json:"port" validate:"required"`
	App          string   `json:"app" validate:"required"`
	AreaId       string   `json:"areaId" validate:"required"`
	NodeInfo     []string `json:"nodeInfo" validate:"required"`     // []string ip,ip  如果为复制集节点，则为复制集所有节点的ip；如果为mongos，则为mongos的ip
	InstanceType string   `json:"instanceType" validate:"required"` // mongod mongos
}

// DeInstall 添加分片到集群
type DeInstall struct {
	runtime          *jobruntime.JobGenericRuntime
	BinDir           string
	DataDir          string
	BackupDir        string
	DbpathDir        string
	InstallPath      string
	PortDir          string
	LogPortDir       string
	DbPathRenameDir  string
	LogPathRenameDir string
	Mongo            string
	OsUser           string
	ServiceStatus    bool
	IPInfo           string
	ConfParams       *DeInstallConfParams
}

// NewDeInstall 实例化结构体
func NewDeInstall() jobruntime.JobRunner {
	return &DeInstall{}
}

// Name 获取原子任务的名字
func (d *DeInstall) Name() string {
	return "mongo_deinstall"
}

// Run 运行原子任务
func (d *DeInstall) Run() error {
	// 检查实例状态
	if err := d.checkMongoService(); err != nil {
		return err
	}

	// 关闭进程
	if err := d.shutdownProcess(); err != nil {
		return err
	}

	// rename目录
	if err := d.DirRename(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (d *DeInstall) Retry() uint {
	return 2
}

// Rollback 回滚
func (d *DeInstall) Rollback() error {
	return nil
}

// Init 初始化
func (d *DeInstall) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	d.runtime = runtime
	d.runtime.Logger.Info("start to init")
	d.BinDir = consts.UsrLocal
	d.DataDir = consts.GetMongoDataDir()
	d.BackupDir = consts.GetMongoBackupDir()

	d.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(d.runtime.PayloadDecoded), &d.ConfParams); err != nil {
		d.runtime.Logger.Error(
			"get parameters of deInstall fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of deInstall fail by json.Unmarshal, error:%s", err)
	}

	// 获取各种目录
	d.InstallPath = filepath.Join(d.BinDir, "mongodb")
	d.Mongo = filepath.Join(d.BinDir, "mongodb", "bin", "mongo")
	strPort := strconv.Itoa(d.ConfParams.Port)
	d.PortDir = filepath.Join(d.DataDir, "mongodata", strPort)
	d.DbpathDir = filepath.Join(d.DataDir, "mongodata", strPort, "db")
	d.DbPathRenameDir = filepath.Join(d.DataDir, "mongodata", fmt.Sprintf("%s_%s_%s_%d",
		d.ConfParams.InstanceType, d.ConfParams.App, d.ConfParams.AreaId, d.ConfParams.Port))
	d.IPInfo = strings.Join(d.ConfParams.NodeInfo, "|")
	d.LogPortDir = filepath.Join(d.BackupDir, "mongolog", strPort)
	d.LogPathRenameDir = filepath.Join(d.BackupDir, "mongolog", fmt.Sprintf("%s_%s_%s_%d",
		d.ConfParams.InstanceType, d.ConfParams.App, d.ConfParams.AreaId, d.ConfParams.Port))

	// 进行校验
	if err := d.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (d *DeInstall) checkParams() error {
	// 校验配置参数
	d.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	d.runtime.Logger.Info("start to validate parameters of deInstall")
	if err := validate.Struct(d.ConfParams); err != nil {
		d.runtime.Logger.Error("validate parameters of deInstall fail, error:%s", err)
		return fmt.Errorf("validate parameters of deInstall fail, error:%s", err)
	}
	return nil
}

// checkMongoService 检查mongo服务
func (d *DeInstall) checkMongoService() error {
	d.runtime.Logger.Info("start to check process status")
	flag, _, err := common.CheckMongoService(d.ConfParams.Port)
	if err != nil {
		d.runtime.Logger.Error("get mongo service status fail, error:%s", err)
		return fmt.Errorf("get mongo service status fail, error:%s", err)
	}
	d.ServiceStatus = flag
	return nil
}

// checkConnection 检查连接
func (d *DeInstall) checkConnection() error {
	d.runtime.Logger.Info("start to check connection")
	cmd := fmt.Sprintf(
		"source /etc/profile;netstat -nat | grep %d |awk '{print $5}'|awk -F: '{print $1}'|sort|uniq -c|sort -nr |grep  -Ewv  '0.0.0.0|127.0.0.1|%s' || true",
		d.ConfParams.Port, d.IPInfo)

	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
	if err != nil {
		d.runtime.Logger.Error("check connection fail, error:%s", err)
		return fmt.Errorf("check connection fail, error:%s", err)
	}
	result = strings.Replace(result, "\n", "", -1)
	if result != "" {
		d.runtime.Logger.Error("check connection fail, there are some connections")
		return fmt.Errorf("check connection fail, there are some connections")
	}
	return nil
}

// shutdownProcess 关闭进程
func (d *DeInstall) shutdownProcess() error {
	if d.ServiceStatus == true {
		d.runtime.Logger.Info("start to shutdown service")
		// 检查连接
		if err := d.checkConnection(); err != nil {
			return err
		}

		// 关闭进程
		if err := common.ShutdownMongoProcess(d.OsUser, d.ConfParams.InstanceType, d.BinDir, d.DbpathDir,
			d.ConfParams.Port); err != nil {
			d.runtime.Logger.Error("shutdown mongo service fail, error:%s", err)
			return fmt.Errorf("shutdown mongo service fail, error:%s", err)
		}
	}

	return nil
}

// DirRename 打包数据目录
func (d *DeInstall) DirRename() error {
	// renameDb数据目录
	flag := util.FileExists(d.PortDir)
	if flag == true {
		d.runtime.Logger.Info("start to rename db directory")
		cmd := fmt.Sprintf(
			"mv %s %s",
			d.PortDir, d.DbPathRenameDir)
		if _, err := util.RunBashCmd(
			cmd,
			"", nil,
			10*time.Second); err != nil {
			d.runtime.Logger.Error("rename db directory fail, error:%s", err)
			return fmt.Errorf("rename db directory fail, error:%s", err)
		}
	}

	// renameDb日志目录
	flag = util.FileExists(d.LogPortDir)
	if flag == true {
		d.runtime.Logger.Info("start to rename log directory")
		cmd := fmt.Sprintf(
			"mv %s %s",
			d.LogPortDir, d.LogPathRenameDir)
		if _, err := util.RunBashCmd(
			cmd,
			"", nil,
			10*time.Second); err != nil {
			d.runtime.Logger.Error("rename log directory fail, error:%s", err)
			return fmt.Errorf("rename log directory fail, error:%s", err)
		}
	}

	return nil
}
