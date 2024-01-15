package atommongodb

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mongo/db-tools/dbactuator/pkg/common"
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// MongoSConfParams 配置文件参数
type MongoSConfParams struct {
	common.MediaPkg `json:"mediapkg"`
	IP              string   `json:"ip" validate:"required"`
	Port            int      `json:"port" validate:"required"`
	InstanceType    string   `json:"instanceType" validate:"required"` // mongos mongod
	App             string   `json:"app" validate:"required"`
	SetId           string   `json:"setId" validate:"required"`
	KeyFile         string   `json:"keyFile" validate:"required"`  // keyFile的内容 app-setId
	Auth            bool     `json:"auth"`                         // true：以验证方式启动mongos false：以非验证方式启动mongos
	ConfigDB        []string `json:"configDB" validate:"required"` // ip:port
	DbConfig        struct {
		SlowOpThresholdMs int    `json:"slowOpThresholdMs"`
		Destination       string `json:"destination"`
	} `json:"dbConfig" validate:"required"`
}

// MongoSInstall MongoS安装
type MongoSInstall struct {
	runtime               *jobruntime.JobGenericRuntime
	BinDir                string
	DataDir               string
	OsUser                string // MongoDB安装在哪个用户下
	OsGroup               string
	ConfParams            *MongoSConfParams
	DbVersion             string
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

// NewMongoSInstall 实例化结构体
func NewMongoSInstall() jobruntime.JobRunner {
	return &MongoSInstall{}
}

// Name 获取原子任务的名字
func (s *MongoSInstall) Name() string {
	return "mongos_install"
}

// Run 运行原子任务
func (s *MongoSInstall) Run() error {
	// 进行校验
	status, err := s.checkParams()
	if err != nil {
		return err
	}
	if status {
		return nil
	}

	// 解压安装包并修改属主
	if err = s.unTarAndCreateSoftLink(); err != nil {
		return err
	}

	// 创建目录并修改属主
	if err = s.mkdir(); err != nil {
		return err
	}

	// 创建配置文件，key文件并修改属主
	if err = s.creatFile(); err != nil {
		return err
	}

	// 启动服务
	if err = s.startup(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (s *MongoSInstall) Retry() uint {
	return 2
}

// Rollback 回滚
func (s *MongoSInstall) Rollback() error {
	return nil
}

// Init 初始化
func (s *MongoSInstall) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	s.runtime = runtime
	s.runtime.Logger.Info("start to init")
	s.BinDir = consts.UsrLocal
	s.DataDir = consts.GetMongoDataDir()
	s.OsUser = consts.GetProcessUser()
	s.OsGroup = consts.GetProcessUserGroup()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(s.runtime.PayloadDecoded), &s.ConfParams); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of mongodb config file fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of mongodb config file fail by json.Unmarshal, error:%s", err)
	}

	// 获取信息
	s.InstallPackagePath = s.ConfParams.MediaPkg.GetAbsolutePath()
	s.DbVersion = strings.Split(s.ConfParams.MediaPkg.GePkgBaseName(), "-")[3]

	// 设置各种路径
	strPort := strconv.Itoa(s.ConfParams.Port)
	s.AuthConfFilePath = filepath.Join(s.DataDir, "mongodata", strPort, "mongo.conf")
	s.NoAuthConfFilePath = filepath.Join(s.DataDir, "mongodata", strPort, "noauth.conf")
	s.LogPath = filepath.Join(s.DataDir, "mongolog", strPort, "mongo.log")
	PidFileName := fmt.Sprintf("pid.%s", strPort)
	s.PidFilePath = filepath.Join(s.DataDir, "mongodata", strPort, PidFileName)
	s.KeyFilePath = filepath.Join(s.DataDir, "mongodata", strPort, "key_of_mongo")
	s.DbTypeFilePath = filepath.Join(s.DataDir, "mongodata", strPort, "dbtype")
	s.LockFilePath = filepath.Join(s.DataDir, "mongoinstall.lock")

	// 生成配置文件内容
	s.runtime.Logger.Info("make mongos config file content")
	if err := s.makeConfContent(); err != nil {
		return err
	}

	return nil
}

// makeConfContent 生成配置文件内容
func (s *MongoSInstall) makeConfContent() error {
	// 只支持mongos 3.0及以上得到配置文件内容
	// 判断mongos版本
	s.runtime.Logger.Info("start to make config file content")
	mainVersion, err := strconv.Atoi(strings.Split(s.DbVersion, ".")[0])
	if err != nil {
		s.runtime.Logger.Error(
			"get %s version fail, error:%s", s.ConfParams.InstanceType, err)
		return fmt.Errorf("get %s version fail, error:%s", s.ConfParams.InstanceType, err)
	}
	clusterId := strings.Join([]string{s.ConfParams.App, s.ConfParams.SetId, "conf"}, "-")
	IpConfigDB := strings.Join(s.ConfParams.ConfigDB, ",")
	configDB := strings.Join([]string{clusterId, IpConfigDB}, "/")

	// 生成mongos配置文件
	conf := common.NewYamlMongoSConf()
	conf.Sharding.ConfigDB = configDB
	conf.SystemLog.LogAppend = true
	conf.SystemLog.Path = s.LogPath
	conf.SystemLog.Destination = s.ConfParams.DbConfig.Destination
	conf.ProcessManagement.Fork = true
	conf.ProcessManagement.PidFilePath = s.PidFilePath
	conf.Net.Port = s.ConfParams.Port
	conf.Net.BindIp = strings.Join([]string{"127.0.0.1", s.ConfParams.IP}, ",")
	conf.Net.WireObjectCheck = false
	// mongos版本小于4获取配置文件内容
	if mainVersion < 4 {
		s.NoAuthConfFileContent, err = conf.GetConfContent()
		if err != nil {
			s.runtime.Logger.Error(
				"version:%s make mongos no auth config file content fail, error:%s", s.DbVersion, err)
			return fmt.Errorf("version:%s make mongos no auth config file content fail, error:%s",
				s.DbVersion, err)
		}
		conf.Security.KeyFile = s.KeyFilePath
		// 获取验证配置文件内容
		s.AuthConfFileContent, err = conf.GetConfContent()
		if err != nil {
			s.runtime.Logger.Error(fmt.Sprintf(
				"version:%s make mongos auth config file content fail, error:%s",
				s.DbVersion, err))
			return fmt.Errorf("version:%s make mongos auth config file content fail, error:%s",
				s.DbVersion, err)
		}
		s.runtime.Logger.Info("make config file content successfully")
		return nil
	}

	// mongos版本4及以上获取配置文件内容
	conf.OperationProfiling.SlowOpThresholdMs = s.ConfParams.DbConfig.SlowOpThresholdMs
	conf.OperationProfiling.SlowOpThresholdMs = s.ConfParams.DbConfig.SlowOpThresholdMs
	// 获取非验证配置文件内容
	s.NoAuthConfFileContent, err = conf.GetConfContent()
	if err != nil {
		s.runtime.Logger.Error(
			"version:%s make mongos no auth config file content fail, error:%s", s.DbVersion, err)
		return fmt.Errorf("version:%s make mongos no auth config file content fail, error:%s",
			s.DbVersion, err)
	}
	conf.Security.KeyFile = s.KeyFilePath
	// 获取验证配置文件内容
	s.AuthConfFileContent, err = conf.GetConfContent()
	if err != nil {
		s.runtime.Logger.Error(fmt.Sprintf(
			"version:%s make mongos auth config file content fail, error:%s",
			s.DbVersion, err))
		return fmt.Errorf("version:%s make mongos auth config file content fail, error:%s",
			s.DbVersion, err)
	}
	s.runtime.Logger.Info("make config file content successfully")
	return nil
}

// checkParams 校验参数 检查输入的参数   检查端口是否合规  检查安装包 检查端口是否被使用（如果使用，则检查是否是mongodb服务）
func (s *MongoSInstall) checkParams() (bool, error) {
	// 校验Mongo配置文件
	s.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	s.runtime.Logger.Info("start to validate parameters of mongos config file")
	if err := validate.Struct(s.ConfParams); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("validate parameters of mongos config file fail, error:%s", err))
		return false, fmt.Errorf("validate parameters of mongos config file fail, error:%s", err)
	}
	s.runtime.Logger.Info("= validate parameters of mongos config file successfully")

	// 校验port是否合规
	s.runtime.Logger.Info("start to validate port if it is correct")
	if s.ConfParams.Port < MongoDBPortMin || s.ConfParams.Port > MongoDBPortMax {
		s.runtime.Logger.Error(fmt.Sprintf(
			"validate port if it is correct, port is not within defalut range [%d,%d]",
			MongoDBPortMin, MongoDBPortMax))
		return false, fmt.Errorf("validate port if it is correct, port is not within defalut range [%d,%d]",
			MongoDBPortMin, MongoDBPortMax)
	}
	s.runtime.Logger.Info("validate port if it is correct successfully")

	// 校验安装包是否存在，md5值是否一致
	s.runtime.Logger.Info("start to validate install package")
	if flag := util.FileExists(s.InstallPackagePath); !flag {
		s.runtime.Logger.Error(fmt.Sprintf("validate install package, %s is not existed",
			s.InstallPackagePath))
		return false, fmt.Errorf("validate install file, %s is not existed",
			s.InstallPackagePath)
	}
	md5, _ := util.GetFileMd5(s.InstallPackagePath)
	if s.ConfParams.MediaPkg.PkgMd5 != md5 {
		s.runtime.Logger.Error(fmt.Sprintf("validate install package md5 fail, md5 is incorrect"))
		return false, fmt.Errorf("validate install package md5 fail, md5 is incorrect")
	}
	s.runtime.Logger.Info("validate install package md5 successfully")

	// 校验端口是否使用
	s.runtime.Logger.Info("start to validate port if it has been used")
	flag, _ := util.CheckPortIsInUse(s.ConfParams.IP, strconv.Itoa(s.ConfParams.Port))
	if flag {
		// 校验端口是否是mongod进程
		cmd := fmt.Sprintf("netstat -ntpl |grep %d | awk '{print $7}' |head -1", s.ConfParams.Port)
		result, _ := util.RunBashCmd(cmd, "", nil, 10*time.Second)
		if strings.Contains(result, "mongos") {
			// 检查配置文件是否一致，读取已有配置文件与新生成的配置文件内容对比
			content, _ := ioutil.ReadFile(s.AuthConfFilePath)
			if strings.Compare(string(content), string(s.AuthConfFileContent)) == 0 {
				// 检查mongodb版本
				version, err := common.CheckMongoVersion(s.BinDir, "mongos")
				if err != nil {
					s.runtime.Logger.Error(
						fmt.Sprintf("mongos has been installed, port:%d, check mongos version fail. error:%s",
							s.ConfParams.Port, version))
					return false, fmt.Errorf("mongos has been installed, port:%d, check mongos version fail. error:%s",
						s.ConfParams.Port, version)
				}
				if version == s.DbVersion {
					s.runtime.Logger.Info(fmt.Sprintf("mongos has been installed, port:%d, version:%s",
						s.ConfParams.Port, version))
					return true, nil
				}
				s.runtime.Logger.Error(fmt.Sprintf("other mongos has been installed, port:%d, version:%s",
					s.ConfParams.Port, version))
				return false, fmt.Errorf("other mongos has been installed, port:%d, version:%s",
					s.ConfParams.Port, version)
			}

		}
		s.runtime.Logger.Error(
			fmt.Sprintf("validate port if it has been used, port:%d is used by other process",
				s.ConfParams.Port))
		return false, fmt.Errorf("validate port if it has been used, port:%d is used by other process",
			s.ConfParams.Port)
	}
	s.runtime.Logger.Info("validate port if it has been used successfully")
	s.runtime.Logger.Info("validate parameters successfully")
	return false, nil
}

// unTarAndCreateSoftLink 解压安装包，创建软链接并给目录授权
func (s *MongoSInstall) unTarAndCreateSoftLink() error {
	// 判断解压目录是否存在
	unTarPath := filepath.Join(s.BinDir, s.ConfParams.MediaPkg.GePkgBaseName())

	// soft link目录
	installPath := filepath.Join(s.BinDir, "mongodb")

	// 解压安装包并授权
	// 安装多实例并发执行添加文件锁
	s.runtime.Logger.Info("start to get install file lock")
	fileLock := common.NewFileLock(s.LockFilePath)
	// 获取锁
	err := fileLock.Lock()
	if err != nil {
		for {
			err = fileLock.Lock()
			if err != nil {
				time.Sleep(1 * time.Second)
				continue
			}
			s.runtime.Logger.Info("get install file lock successfully")
			break
		}
	} else {
		s.runtime.Logger.Info("get install file lock successfully")
	}
	if err = common.UnTarAndCreateSoftLinkAndChown(s.runtime, s.BinDir,
		s.InstallPackagePath, unTarPath, installPath, s.OsUser, s.OsGroup); err != nil {
		return err
	}
	// 释放锁
	s.runtime.Logger.Info("release install file lock successfully")
	_ = fileLock.UnLock()

	// 检查mongos版本
	s.runtime.Logger.Info("start to check mongos version")
	version, err := common.CheckMongoVersion(s.BinDir, "mongos")
	if err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("%s has been existed, check mongodb version, error:%s",
			installPath, err))
		return fmt.Errorf("%s has been existed, check mongodb version, error:%s",
			installPath, err)
	}
	if version != s.DbVersion {
		s.runtime.Logger.Error(
			fmt.Sprintf("%s has been existed, check mongodb version, version:%s is incorrect",
				installPath, version))
		return fmt.Errorf("%s has been existed, check mongodb version, version:%s is incorrect",
			installPath, version)
	}
	s.runtime.Logger.Info("check mongos version successfully")
	return nil
}

// mkdir 创建相关目录并给目录授权
func (s *MongoSInstall) mkdir() error {
	// 创建日志文件目录
	logPathDir, _ := filepath.Split(s.LogPath)
	s.runtime.Logger.Info("start to create log directory")
	if err := util.MkDirsIfNotExistsWithPerm([]string{logPathDir}, DefaultPerm); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("create log directory fail, error:%s", err))
		return fmt.Errorf("create log directory fail, error:%s", err)
	}
	s.runtime.Logger.Info("create log directory successfully")

	// 创建配置文件目录
	confFilePathDir, _ := filepath.Split(s.AuthConfFilePath)
	s.runtime.Logger.Info("start to create data directory")
	if err := util.MkDirsIfNotExistsWithPerm([]string{confFilePathDir}, DefaultPerm); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("create data directory fail, error:%s", err))
		return fmt.Errorf("create data directory fail, error:%s", err)
	}
	s.runtime.Logger.Info("create data directory successfully")

	// 修改目录属主
	s.runtime.Logger.Info("start to execute chown command for dbPath, logPath and backupPath")
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", s.OsUser, s.OsGroup, filepath.Join(logPathDir, "../")),
		"", nil,
		10*time.Second); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("chown log directory fail, error:%s", err))
		return fmt.Errorf("chown log directory fail, error:%s", err)
	}
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", s.OsUser, s.OsGroup, filepath.Join(confFilePathDir, "../")),
		"", nil,
		10*time.Second); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("chown data directory fail, error:%s", err))
		return fmt.Errorf("chown data directory fail, error:%s", err)
	}
	s.runtime.Logger.Info("execute chown command for dbPath, logPath and backupPath successfully")
	return nil
}

// createFile 创建配置文件以及key文件
func (s *MongoSInstall) creatFile() error {
	// 创建配置文件，key文件，dbType文件并授权
	if err := common.CreateConfFileAndKeyFileAndDbTypeFileAndChown(
		s.runtime, s.AuthConfFilePath, s.AuthConfFileContent, s.OsUser, s.OsGroup, s.NoAuthConfFilePath,
		s.NoAuthConfFileContent, s.KeyFilePath, s.ConfParams.KeyFile, s.DbTypeFilePath,
		s.ConfParams.InstanceType, DefaultPerm); err != nil {
		return err
	}
	return nil
}

// startup 启动服务
func (s *MongoSInstall) startup() error {
	// 申明mongos可执行文件路径，把路径写入/etc/profile
	if err := common.AddPathToProfile(s.runtime, s.BinDir); err != nil {
		return err
	}

	// 启动服务
	s.runtime.Logger.Info("start to startup mongos")
	if err := common.StartMongoProcess(s.BinDir, s.ConfParams.Port,
		s.OsUser, s.ConfParams.Auth); err != nil {
		s.runtime.Logger.Error(fmt.Sprintf("startup mongos fail, error:%s", err))
		return fmt.Errorf("shutdown mongos fail, error:%s", err)
	}
	flag, service, err := common.CheckMongoService(s.ConfParams.Port)
	if err != nil {
		s.runtime.Logger.Error("check %s fail, error:%s", service, err)
		return fmt.Errorf("check %s fail, error:%s", service, err)
	}
	if flag == false {
		s.runtime.Logger.Error("startup %s fail", service)
		return fmt.Errorf("startup %s fail", service)
	}
	s.runtime.Logger.Info("startup %s successfully", service)

	return nil
}
