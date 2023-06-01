package atommongodb

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

/*

1.预检查
检查输入的参数   检查端口是否合规  检查安装包 检查端口是否被使用（如果使用，则检查是否是mongodb服务）

2.解压安装包 判断是否已经解压过，版本是否正确
解压文件 做软链接 修改文件属主

3.安装 判断目录是否已被创建
创建相关各级目录-判断目录是否已经创建过 修改目录属主  创建配置文件(noauth, auth) 创建dbtype文件 复制集创建key文件

4.启动服务
以noauth启动服务

*/

// MongoDBPortMin MongoDB最小端口
const MongoDBPortMin = 27000

// MongoDBPortMax MongoDB最大端口
const MongoDBPortMax = 27230

// DefaultPerm 创建目录、文件的默认权限
const DefaultPerm = 0755

// MongoDBConfParams 配置文件参数
type MongoDBConfParams struct {
	common.MediaPkg `json:"mediapkg"`
	IP              string `json:"ip" validate:"required"`
	Port            int    `json:"port" validate:"required"`
	DbVersion       string `json:"dbVersion" validate:"required"`
	InstanceType    string `json:"instanceType" validate:"required"` // mongos mongod
	App             string `json:"app" validate:"required"`
	AreaId          string `json:"areaId" validate:"required"`
	SetId           string `json:"setId" validate:"required"`
	Auth            bool   `json:"auth"`        // true：以验证方式启动mongod false：以非验证方式启动mongod
	ClusterRole     string `json:"clusterRole"` // 部署cluster时填写，shardsvr  configsvr；部署复制集时为空
	DbConfig        struct {
		SlowOpThresholdMs int    `json:"slowOpThresholdMs"`
		CacheSizeGB       int    `json:"cacheSizeGB"`
		OplogSizeMB       int    `json:"oplogSizeMB" validate:"required"`
		Destination       string `json:"destination"`
	} `json:"dbConfig" validate:"required"`
}

// MongoDBInstall MongoDB安装
type MongoDBInstall struct {
	runtime               *jobruntime.JobGenericRuntime
	BinDir                string
	BackupDir             string
	DataDir               string
	OsUser                string // MongoDB安装在哪个用户下
	OsGroup               string
	ConfParams            *MongoDBConfParams
	DbpathDir             string
	BackupPath            string
	AuthConfFilePath      string
	AuthConfFileContent   []byte
	NoAuthConfFilePath    string
	NoAuthConfFileContent []byte
	DbTypeFilePath        string
	LogPath               string
	PidFilePath           string
	KeyFilePath           string
	InstallPackagePath    string
	LockFilePath          string // 锁文件路径
}

// NewMongoDBInstall 实例化结构体
func NewMongoDBInstall() jobruntime.JobRunner {
	return &MongoDBInstall{}
}

// Name 获取原子任务的名字
func (m *MongoDBInstall) Name() string {
	return "mongod_install"
}

// Run 运行原子任务
func (m *MongoDBInstall) Run() error {
	// 进行校验
	status, err := m.checkParams()
	if err != nil {
		return err
	}
	if status {
		return nil
	}

	// 解压安装包并修改属主
	if err = m.unTarAndCreateSoftLink(); err != nil {
		return err
	}

	// 创建目录并修改属主
	if err = m.mkdir(); err != nil {
		return err
	}

	// 创建配置文件，key文件并修改属主
	if err = m.createConfFileAndKeyFileAndDbTypeFile(); err != nil {
		return err
	}

	// 启动服务
	if err = m.startup(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (m *MongoDBInstall) Retry() uint {
	return 2
}

// Rollback 回滚
func (m *MongoDBInstall) Rollback() error {
	return nil
}

// Init 初始化
func (m *MongoDBInstall) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	m.runtime = runtime
	m.runtime.Logger.Info("start to init")
	m.BinDir = consts.UsrLocal
	m.BackupDir = consts.GetMongoBackupDir()
	m.DataDir = consts.GetMongoDataDir()
	m.OsUser = consts.GetProcessUser()
	m.OsGroup = consts.GetProcessUserGroup()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(m.runtime.PayloadDecoded), &m.ConfParams); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of mongodb config file fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of mongodb config file fail by json.Unmarshal, error:%s", err)
	}

	// 获取信息
	m.InstallPackagePath = m.ConfParams.MediaPkg.GetAbsolutePath()

	// 设置各种路径
	strPort := strconv.Itoa(m.ConfParams.Port)
	m.DbpathDir = filepath.Join(m.DataDir, "mongodata", strPort, "db")
	m.BackupPath = filepath.Join(m.BackupDir, "dbbak")
	m.AuthConfFilePath = filepath.Join(m.DataDir, "mongodata", strPort, "mongo.conf")
	m.NoAuthConfFilePath = filepath.Join(m.DataDir, "mongodata", strPort, "noauth.conf")
	m.LogPath = filepath.Join(m.BackupDir, "mongolog", strPort, "mongo.log")
	PidFileName := fmt.Sprintf("pid.%s", strPort)
	m.PidFilePath = filepath.Join(m.DataDir, "mongodata", strPort, PidFileName)
	m.KeyFilePath = filepath.Join(m.DataDir, "mongodata", strPort, "key_of_mongo")
	m.DbTypeFilePath = filepath.Join(m.DataDir, "mongodata", strPort, "dbtype")
	m.LockFilePath = filepath.Join(m.DataDir, "mongoinstall.lock")

	m.runtime.Logger.Info("init successfully")

	// 生成配置文件内容
	if err := m.makeConfContent(); err != nil {
		return err
	}

	return nil
}

// makeConfContent 生成配置文件内容
func (m *MongoDBInstall) makeConfContent() error {
	mainVersion, err := strconv.Atoi(strings.Split(m.ConfParams.DbVersion, ".")[0])
	if err != nil {
		return err
	}

	// mongodb 3.0及以上得到配置文件内容
	if mainVersion >= 3 {
		m.runtime.Logger.Info("start to make mongodb config file content")
		conf := common.NewYamlMongoDBConf()
		conf.Storage.DbPath = m.DbpathDir
		conf.Storage.Engine = "wiredTiger"
		conf.Storage.WiredTiger.EngineConfig.CacheSizeGB = m.ConfParams.DbConfig.CacheSizeGB
		conf.Replication.OplogSizeMB = m.ConfParams.DbConfig.OplogSizeMB
		conf.Replication.ReplSetName = strings.Join([]string{m.ConfParams.App, m.ConfParams.AreaId, m.ConfParams.SetId},
			"-")
		conf.SystemLog.LogAppend = true
		conf.SystemLog.Path = m.LogPath
		conf.SystemLog.Destination = m.ConfParams.DbConfig.Destination
		conf.ProcessManagement.Fork = true
		conf.ProcessManagement.PidFilePath = m.PidFilePath
		conf.Net.Port = m.ConfParams.Port
		conf.Net.BindIp = strings.Join([]string{"127.0.0.1", m.ConfParams.IP}, ",")
		conf.Net.WireObjectCheck = false
		conf.OperationProfiling.SlowOpThresholdMs = m.ConfParams.DbConfig.SlowOpThresholdMs
		conf.Sharding.ClusterRole = m.ConfParams.ClusterRole
		// 获取非验证配置文件内容
		m.NoAuthConfFileContent, err = conf.GetConfContent()
		if err != nil {
			m.runtime.Logger.Error(fmt.Sprintf(
				"version:%s make mongodb no auth config file content fail, error:%s", m.ConfParams.DbVersion, err))
			return fmt.Errorf("version:%s make mongodb no auth config file content fail, error:%s",
				m.ConfParams.DbVersion, err)
		}
		conf.Security.KeyFile = m.KeyFilePath
		// 获取验证配置文件内容
		m.AuthConfFileContent, err = conf.GetConfContent()
		if err != nil {
			m.runtime.Logger.Error(fmt.Sprintf(
				"version:%s make mongodb auth config file content fail, error:%s",
				m.ConfParams.DbVersion, err))
			return fmt.Errorf("version:%s make mongodb auth config file content fail, error:%s",
				m.ConfParams.DbVersion, err)
		}
		m.runtime.Logger.Info("make mongodb config file content successfully")
		return nil
	}

	// mongodb 3.0以下获取配置文件内容
	// 获取非验证配置文件内容
	m.runtime.Logger.Info("start to make mongodb config file content")
	NoAuthConf := common.IniNoAuthMongoDBConf
	AuthConf := common.IniAuthMongoDBConf
	replSet := strings.Join([]string{m.ConfParams.App, m.ConfParams.AreaId, m.ConfParams.SetId},
		"-")
	NoAuthConf = strings.Replace(NoAuthConf, "{{replSet}}", replSet, -1)
	AuthConf = strings.Replace(AuthConf, "{{replSet}}", replSet, -1)
	NoAuthConf = strings.Replace(NoAuthConf, "{{dbpath}}", m.DbpathDir, -1)
	AuthConf = strings.Replace(AuthConf, "{{dbpath}}", m.DbpathDir, -1)
	NoAuthConf = strings.Replace(NoAuthConf, "{{logpath}}", m.LogPath, -1)
	AuthConf = strings.Replace(AuthConf, "{{logpath}}", m.LogPath, -1)
	NoAuthConf = strings.Replace(NoAuthConf, "{{pidfilepath}}", m.PidFilePath, -1)
	AuthConf = strings.Replace(AuthConf, "{{pidfilepath}}", m.PidFilePath, -1)
	strPort := strconv.Itoa(m.ConfParams.Port)
	NoAuthConf = strings.Replace(NoAuthConf, "{{port}}", strPort, -1)
	AuthConf = strings.Replace(AuthConf, "{{port}}", strPort, -1)
	bindIP := strings.Join([]string{"127.0.0.1", m.ConfParams.IP}, ",")
	NoAuthConf = strings.Replace(NoAuthConf, "{{bind_ip}}", bindIP, -1)
	AuthConf = strings.Replace(AuthConf, "{{bind_ip}}", bindIP, -1)
	strOplogSize := strconv.Itoa(m.ConfParams.DbConfig.OplogSizeMB)
	NoAuthConf = strings.Replace(NoAuthConf, "{{oplogSize}}", strOplogSize, -1)
	AuthConf = strings.Replace(AuthConf, "{{oplogSize}}", strOplogSize, -1)
	NoAuthConf = strings.Replace(NoAuthConf, "{{instanceRole}}", m.ConfParams.ClusterRole, -1)
	AuthConf = strings.Replace(AuthConf, "{{instanceRole}}", m.ConfParams.ClusterRole, -1)
	AuthConf = strings.Replace(AuthConf, "{{keyFile}}", m.KeyFilePath, -1)
	m.NoAuthConfFileContent = []byte(NoAuthConf)
	m.AuthConfFileContent = []byte(AuthConf)
	m.runtime.Logger.Info("make mongodb config file content successfully")

	return nil
}

// checkParams 校验参数 检查输入的参数   检查端口是否合规  检查安装包 检查端口是否被使用（如果使用，则检查是否是mongodb服务）
func (m *MongoDBInstall) checkParams() (bool, error) {
	// 校验MongoDB配置文件
	m.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	m.runtime.Logger.Info("start to validate parameters of mongodb config file")
	if err := validate.Struct(m.ConfParams); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("validate parameters of mongodb config file fail, error:%s", err))
		return false, fmt.Errorf("validate parameters of mongodb config file fail, error:%s", err)
	}
	// 校验port是否合规
	m.runtime.Logger.Info("start to validate port if it is correct")
	if m.ConfParams.Port < MongoDBPortMin || m.ConfParams.Port > MongoDBPortMax {
		m.runtime.Logger.Error(fmt.Sprintf(
			"validate port if it is correct, port is not within defalut range [%d,%d]",
			MongoDBPortMin, MongoDBPortMax))
		return false, fmt.Errorf("validate port if it is correct, port is not within defalut range [%d,%d]",
			MongoDBPortMin, MongoDBPortMax)
	}

	// 校验安装包是否存在，md5值是否一致
	m.runtime.Logger.Info("start to validate install package")
	if flag := util.FileExists(m.InstallPackagePath); !flag {
		m.runtime.Logger.Error(fmt.Sprintf("validate install package, %s is not existed",
			m.InstallPackagePath))
		return false, fmt.Errorf("validate install file, %s is not existed",
			m.InstallPackagePath)
	}
	md5, _ := util.GetFileMd5(m.InstallPackagePath)
	if m.ConfParams.MediaPkg.PkgMd5 != md5 {
		m.runtime.Logger.Error(fmt.Sprintf("validate install package md5 fail, md5 is incorrect"))
		return false, fmt.Errorf("validate install package md5 fail, md5 is incorrect")
	}

	// 校验端口是否使用
	m.runtime.Logger.Info("start to validate port if it has been used")
	flag, _ := util.CheckPortIsInUse(m.ConfParams.IP, strconv.Itoa(m.ConfParams.Port))
	if flag {
		// 校验端口是否是mongod进程
		cmd := fmt.Sprintf("netstat -ntpl |grep %d | awk '{print $7}' |head -1", m.ConfParams.Port)
		result, _ := util.RunBashCmd(cmd, "", nil, 10*time.Second)
		if strings.Contains(result, "mongod") {
			// 检查配置文件是否一致，读取已有配置文件与新生成的配置文件内容对比
			content, _ := ioutil.ReadFile(m.AuthConfFilePath)
			if strings.Compare(string(content), string(m.AuthConfFileContent)) == 0 {
				// 检查mongod版本
				version, err := common.CheckMongoVersion(m.BinDir, "mongod")
				if err != nil {
					m.runtime.Logger.Error(
						fmt.Sprintf("mongod has been installed, port:%d, check mongod version fail. error:%s",
							m.ConfParams.Port, version))
					return false, fmt.Errorf("mongod has been installed, port:%d, check mongod version fail. error:%s",
						m.ConfParams.Port, version)
				}
				if version == m.ConfParams.DbVersion {
					m.runtime.Logger.Info(fmt.Sprintf("mongod has been installed, port:%d, version:%s",
						m.ConfParams.Port, version))
					return true, nil
				}
				m.runtime.Logger.Error(fmt.Sprintf("other mongod has been installed, port:%d, version:%s",
					m.ConfParams.Port, version))
				return false, fmt.Errorf("other mongod has been installed, port:%d, version:%s",
					m.ConfParams.Port, version)
			}

		}
		m.runtime.Logger.Error(
			fmt.Sprintf("validate port if it has been used, port:%d is used by other process",
				m.ConfParams.Port))
		return false, fmt.Errorf("validate port if it has been used, port:%d is used by other process",
			m.ConfParams.Port)
	}
	m.runtime.Logger.Info("validate parameters successfully")
	return false, nil
}

// unTarAndCreateSoftLink 解压安装包，创建软链接并给目录授权
func (m *MongoDBInstall) unTarAndCreateSoftLink() error {
	// 解压目录
	unTarPath := filepath.Join(m.BinDir, m.ConfParams.MediaPkg.GePkgBaseName())

	// soft link目录
	installPath := filepath.Join(m.BinDir, "mongodb")

	// 解压安装包并授权
	// 安装多实例并发执行添加文件锁
	m.runtime.Logger.Info("start to get install file lock")
	fileLock := common.NewFileLock(m.LockFilePath)
	// 获取锁
	err := fileLock.Lock()
	if err != nil {
		for {
			err = fileLock.Lock()
			if err != nil {
				time.Sleep(1 * time.Second)
				continue
			}
			m.runtime.Logger.Info("get install file lock successfully")
			break
		}
	} else {
		m.runtime.Logger.Info("get install file lock successfully")
	}

	if err = common.UnTarAndCreateSoftLinkAndChown(m.runtime, m.BinDir,
		m.InstallPackagePath, unTarPath, installPath, m.OsUser, m.OsGroup); err != nil {
		return err
	}
	// 释放锁
	_ = fileLock.UnLock()
	m.runtime.Logger.Info("release install file lock successfully")

	// 检查mongod版本
	m.runtime.Logger.Info("start to check mongod version")
	version, err := common.CheckMongoVersion(m.BinDir, "mongod")
	if err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("%s has been existed, check mongodb version, error:%s",
			installPath, err))
		return fmt.Errorf("%s has been existed, check mongodb version, error:%s",
			installPath, err)
	}
	if version != m.ConfParams.DbVersion {
		m.runtime.Logger.Error(
			fmt.Sprintf("%s has been existed, check mongodb version, version:%s is incorrect",
				installPath, version))
		return fmt.Errorf("%s has been existed, check mongodb version, version:%s is incorrect",
			installPath, version)
	}
	m.runtime.Logger.Info("check mongod version successfully")
	return nil
}

// mkdir 创建相关目录并给目录授权
func (m *MongoDBInstall) mkdir() error {
	// 创建日志文件目录
	logPathDir, _ := filepath.Split(m.LogPath)
	m.runtime.Logger.Info("start to create log directory")
	if err := util.MkDirsIfNotExistsWithPerm([]string{logPathDir}, DefaultPerm); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("create log directory fail, error:%s", err))
		return fmt.Errorf("create log directory fail, error:%s", err)
	}
	m.runtime.Logger.Info("create log directory successfully")

	// 创建数据文件目录
	m.runtime.Logger.Info("start to create data directory")
	if err := util.MkDirsIfNotExistsWithPerm([]string{m.DbpathDir}, DefaultPerm); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("create data directory fail, error:%s", err))
		return fmt.Errorf("create data directory fail, error:%s", err)
	}
	m.runtime.Logger.Info("create data directory successfully")

	// 创建备份文件目录
	m.runtime.Logger.Info("start to create backup directory")
	if err := util.MkDirsIfNotExistsWithPerm([]string{m.BackupDir}, DefaultPerm); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("create backup directory fail, error:%s", err))
		return fmt.Errorf("create backup directory fail, error:%s", err)
	}
	m.runtime.Logger.Info("create backup directory successfully")

	// 修改目录属主
	m.runtime.Logger.Info("start to execute chown command for dbPath, logPath and backupPath")
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", m.OsUser, m.OsGroup, filepath.Join(logPathDir, "../")),
		"", nil,
		10*time.Second); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("chown log directory fail, error:%s", err))
		return fmt.Errorf("chown log directory fail, error:%s", err)
	}
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", m.OsUser, m.OsGroup, filepath.Join(m.DbpathDir, "../../")),
		"", nil,
		10*time.Second); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("chown data directory fail, error:%s", err))
		return fmt.Errorf("chown data directory fail, error:%s", err)
	}
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", m.OsUser, m.OsGroup, m.BackupDir),
		"", nil,
		10*time.Second); err != nil {
		m.runtime.Logger.Error(fmt.Sprintf("chown backup directory fail, error:%s", err))
		return fmt.Errorf("chown backup directory fail, error:%s", err)
	}
	m.runtime.Logger.Info("execute chown command for dbPath, logPath and backupPath successfully")
	return nil
}

// createConfFileAndKeyFileAndDbTypeFile 创建配置文件以及key文件
func (m *MongoDBInstall) createConfFileAndKeyFileAndDbTypeFile() error {
	if err := common.CreateConfFileAndKeyFileAndDbTypeFileAndChown(
		m.runtime, m.AuthConfFilePath, m.AuthConfFileContent, m.OsUser, m.OsGroup, m.NoAuthConfFilePath,
		m.NoAuthConfFileContent, m.KeyFilePath, m.ConfParams.App, m.ConfParams.AreaId, m.DbTypeFilePath,
		m.ConfParams.InstanceType, DefaultPerm); err != nil {
		return err
	}
	return nil
}

// startup 启动服务
func (m *MongoDBInstall) startup() error {
	// 声明mongod可执行文件路径，把路径写入/etc/profile
	if err := common.AddPathToProfile(m.runtime, m.BinDir); err != nil {
		return err
	}

	// 启动服务
	m.runtime.Logger.Info("start to startup mongod")
	if err := common.StartMongoProcess(m.BinDir, m.ConfParams.Port,
		m.OsUser, m.ConfParams.Auth); err != nil {
		m.runtime.Logger.Error("startup mongod fail, error:%s", err)
		return fmt.Errorf("startup mongod fail, error:%s", err)
	}
	flag, service, err := common.CheckMongoService(m.ConfParams.Port)
	if err != nil {
		m.runtime.Logger.Error("check %s fail, error:%s", service, err)
		return fmt.Errorf("check %s fail, error:%s", service, err)
	}
	if flag == false {
		m.runtime.Logger.Error("startup %s fail", service)
		return fmt.Errorf("startup %s fail", service)
	}
	m.runtime.Logger.Info("startup %s successfully", service)

	return nil
}
