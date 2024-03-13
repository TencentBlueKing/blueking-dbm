package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// MongoDChangeOplogSizeConfParams 参数  // 修改oplog大小
type MongoDChangeOplogSizeConfParams struct {
	IP            string `json:"ip" validate:"required"` // 执行节点
	Port          int    `json:"port" validate:"required"`
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
	NewOplogSize  int    `json:"newOplogSize"` // 单位：GB
}

// MongoDChangeOplogSize 修改oplog大小
type MongoDChangeOplogSize struct {
	BaseJob
	runtime            *jobruntime.JobGenericRuntime
	BinDir             string
	Mongo              string
	MongoD             string
	OsUser             string
	OsGroup            string
	DataDir            string
	DbpathDir          string
	ConfParams         *MongoDChangeOplogSizeConfParams
	PrimaryIP          string
	PrimaryPort        int
	MainVersion        int
	Version            float64
	AuthConfFilePath   string
	NoAuthConfFilePath string
	OplogSizeMB        int
	NewOplogSizeMB     int
	ScriptDir          string
	ScriptFilePath     string
	NewPort            int
}

// NewMongoDChangeOplogSize 实例化结构体
func NewMongoDChangeOplogSize() jobruntime.JobRunner {
	return &MongoDChangeOplogSize{}
}

// Name 获取原子任务的名字
func (c *MongoDChangeOplogSize) Name() string {
	return "mongod_change_oplogsize"
}

// Run 运行原子任务
func (c *MongoDChangeOplogSize) Run() error {
	// 检查现有oplog大小
	if err := c.checkOplogSizeAndFreeSpace(); err != nil {
		return err
	}

	// 修改配置文件
	if err := c.changeConfigFile(); err != nil {
		return err
	}

	// 修改oplog大小
	if err := c.changeOplogSize(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (c *MongoDChangeOplogSize) Retry() uint {
	return 2
}

// Rollback 回滚
func (c *MongoDChangeOplogSize) Rollback() error {
	return nil
}

// Init 初始化
func (c *MongoDChangeOplogSize) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	c.runtime = runtime
	c.runtime.Logger.Info("start to init")
	c.BinDir = consts.UsrLocal
	c.Mongo = filepath.Join(c.BinDir, "mongodb", "bin", "mongo")
	c.MongoD = filepath.Join(c.BinDir, "mongodb", "bin", "mongod")
	c.OsUser = consts.GetProcessUser()
	c.OsGroup = consts.GetProcessUserGroup()
	c.DataDir = consts.GetMongoDataDir()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(c.runtime.PayloadDecoded), &c.ConfParams); err != nil {
		c.runtime.Logger.Error(fmt.Sprintf(
			"get parameters of mongoDChangeOplogSize fail by json.Unmarshal, error:%s", err))
		return fmt.Errorf("get parameters of mongoDChangeOplogSize fail by json.Unmarshal, error:%s", err)
	}
	// 获取路径
	strPort := strconv.Itoa(c.ConfParams.Port)
	c.AuthConfFilePath = filepath.Join(c.DataDir, "mongodata", strPort, "mongo.conf")
	c.NoAuthConfFilePath = filepath.Join(c.DataDir, "mongodata", strPort, "noauth.conf")
	c.DbpathDir = filepath.Join(c.DataDir, "mongodata", strPort, "db")
	c.ScriptDir = filepath.Join("/", "home", c.OsUser, c.runtime.UID)
	c.ScriptFilePath = filepath.Join(c.ScriptDir, strings.Join([]string{"script", "js"}, "."))
	c.NewOplogSizeMB = c.ConfParams.NewOplogSize * 1024
	c.NewPort = c.ConfParams.Port + 1000

	// 获取primary信息
	info, err := common.AuthGetPrimaryInfo(c.Mongo, c.ConfParams.AdminUsername, c.ConfParams.AdminPassword,
		c.ConfParams.IP, c.ConfParams.Port)
	if err != nil {
		c.runtime.Logger.Error(fmt.Sprintf(
			"get primary db info of mongoDChangeOplogSize fail, error:%s", err))
		return fmt.Errorf("get primary db info of mongoDChangeOplogSize fail, error:%s", err)
	}
	// 判断info是否为null
	if info == "" {
		c.runtime.Logger.Error(fmt.Sprintf(
			"get primary db info of mongoDChangeOplogSize fail, error:%s", err))
		return fmt.Errorf("get primary db info of mongoDChangeOplogSize fail, error:%s", err)
	}
	getInfo := strings.Split(info, ":")
	c.PrimaryIP = getInfo[0]
	c.PrimaryPort, _ = strconv.Atoi(getInfo[1])

	// 获取mongo版本
	version, err := common.CheckMongoVersion(c.BinDir, "mongod")
	if err != nil {
		c.runtime.Logger.Error(fmt.Sprintf("check mongo version fail, error:%s", err))
		return fmt.Errorf("check mongo version fail, error:%s", err)
	}
	c.MainVersion, _ = strconv.Atoi(strings.Split(version, ".")[0])
	c.Version, _ = strconv.ParseFloat(version[0:3], 64)

	c.runtime.Logger.Info("init successfully")

	// 进行校验
	if err = c.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (c *MongoDChangeOplogSize) checkParams() error {
	// 校验重启配置参数
	validate := validator.New()
	c.runtime.Logger.Info("start to validate parameters of mongoDChangeOplogSize")
	if err := validate.Struct(c.ConfParams); err != nil {
		c.runtime.Logger.Error("validate parameters of mongoDChangeOplogSize fail, error:%s", err)
		return fmt.Errorf("validate parameters of mongoDChangeOplogSize fail, error:%s", err)
	}
	c.runtime.Logger.Info("validate parameters of mongoDChangeOplogSize successfully")
	return nil
}

// checkOplogSizeAndFreeSpace  检查现有oplog大小及挂载点的剩余空间
func (c *MongoDChangeOplogSize) checkOplogSizeAndFreeSpace() error {
	// 检查现有oplog大小
	c.runtime.Logger.Info("start to check current oplogSize")
	cmd := fmt.Sprintf(
		"%s  --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\" %s",
		c.Mongo, c.ConfParams.IP, c.ConfParams.Port,
		"db.getSiblingDB('local').oplog.rs.stats(1024*1024*1024).maxSize", "admin")
	oplogSize, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
	if err != nil {
		c.runtime.Logger.Error("get current oplogSize fail, error:%s", err)
		return fmt.Errorf("get current oplogSize fail, error:%s", err)
	}
	oplogSizeInt, _ := strconv.Atoi(strings.Replace(oplogSize, "\n", "", -1))
	c.OplogSizeMB = oplogSizeInt * 1024
	if oplogSizeInt == c.ConfParams.NewOplogSize {
		c.runtime.Logger.Error("newOplogSize:%dGB is same as current oplogSize:%dGB", c.ConfParams.NewOplogSize, oplogSizeInt)
		return fmt.Errorf("newOplogSize:%dGB is same as current oplogSize:%dGB", c.ConfParams.NewOplogSize, oplogSizeInt)
	} else if oplogSizeInt > c.ConfParams.NewOplogSize {
		c.runtime.Logger.Error("newOplogSize:%dGB is less than current oplogSize:%dGB", c.ConfParams.NewOplogSize,
			oplogSizeInt)
		return fmt.Errorf("newOplogSize:%dGB is less than current oplogSize:%dGB", c.ConfParams.NewOplogSize, oplogSizeInt)
	}
	c.runtime.Logger.Info("check current oplogSize successfully")

	//
	c.runtime.Logger.Info("start to check free space about mountPoint")
	cmd = fmt.Sprintf("df -m |grep %s | awk '{print $4}'", c.OsUser)
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
	if err != nil {
		c.runtime.Logger.Error("check free space about mountPoint, error:%s", err)
		return fmt.Errorf("check free space about mountPoint, error:%s", err)
	}
	result = strings.Replace(result, "\n", "", -1)
	resultInt, _ := strconv.Atoi(result)
	if resultInt < c.NewOplogSizeMB-c.OplogSizeMB+5120 {
		c.runtime.Logger.Error("free space is not enough about mountPoint")
		return fmt.Errorf("free space is not enough about mountPoint")
	}
	c.runtime.Logger.Info("check free space about mountPoint successfully")
	return nil
}

// changeConfigFile 修改配置文件
func (c *MongoDChangeOplogSize) changeConfigFile() error {
	c.runtime.Logger.Info("start to change config file content")
	var authCmd string
	var noAuthCmd string
	var checkAuthCmd string
	var checkNoAuthcmd string
	// 修改oplog大小参数及
	if c.MainVersion >= 3 {
		authCmd = fmt.Sprintf("sed -i \"s/oplogSizeMB: %d/oplogSizeMB: %d/g\" %s", c.OplogSizeMB, c.NewOplogSizeMB,
			c.AuthConfFilePath)
		noAuthCmd = fmt.Sprintf("sed -i \"s/oplogSizeMB: %d/oplogSizeMB: %d/g\" %s", c.OplogSizeMB, c.NewOplogSizeMB,
			c.NoAuthConfFilePath)
	} else {
		authCmd = fmt.Sprintf("sed -i \"soplogSize=%d/oplogSize=%d/g\" %s", c.OplogSizeMB, c.NewOplogSizeMB,
			c.AuthConfFilePath)
		noAuthCmd = fmt.Sprintf("sed -i \"s/oplogSize=%d/oplogSize=%d/g\" %s", c.OplogSizeMB, c.NewOplogSizeMB,
			c.NoAuthConfFilePath)
	}
	if _, err := util.RunBashCmd(
		authCmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("change auth config file fail, error:%s", err)
		return fmt.Errorf("change auth config file fail, error:%s", err)
	}
	if _, err := util.RunBashCmd(
		noAuthCmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("change noAuth config file fail, error:%s", err)
		return fmt.Errorf("change noAuth config file fail, error:%s", err)
	}
	// 检查oplog大小参数
	if c.MainVersion >= 3 {
		checkAuthCmd = fmt.Sprintf("cat %s |grep oplogSizeMB", c.AuthConfFilePath)
		checkNoAuthcmd = fmt.Sprintf("cat %s |grep oplogSizeMB", c.NoAuthConfFilePath)
	} else {
		checkAuthCmd = fmt.Sprintf("cat %s |grep oplogSize", c.AuthConfFilePath)
		checkNoAuthcmd = fmt.Sprintf("cat %s |grep oplogSize", c.NoAuthConfFilePath)
	}
	result, err := util.RunBashCmd(
		checkAuthCmd,
		"", nil,
		10*time.Second)
	if err != nil {
		c.runtime.Logger.Error("check oplogSize parameter of auth config file fail, error:%s", err)
		return fmt.Errorf("check oplogSize parameter of auth config file fail, error:%s", err)
	}
	if strings.Contains(result, strconv.Itoa(c.NewOplogSizeMB)) {
		c.runtime.Logger.Info("change oplogSize parameter of auth config file successfully")
	}
	result1, err := util.RunBashCmd(
		checkNoAuthcmd,
		"", nil,
		10*time.Second)
	if err != nil {
		c.runtime.Logger.Error("check oplogSize parameter of noAuth config file fail, error:%s", err)
		return fmt.Errorf("check oplogSize parameter of noAuth config file fail, error:%s", err)
	}
	if strings.Contains(result1, strconv.Itoa(c.NewOplogSizeMB)) {
		c.runtime.Logger.Info("change oplogSize parameter of noAuth config file successfully")
	}
	c.runtime.Logger.Info("change config file content successfully")
	return nil
}

// createScript db版本小于3.6 创建修改脚本
func (c *MongoDChangeOplogSize) createScript() error {
	c.runtime.Logger.Info("create change oplogSize script")
	scriptContent := `db = db.getSiblingDB('local');
db.temp.drop();
db.temp.save( db.oplog.rs.find( { }, { ts: 1, h: 1 } ).sort( {$natural : -1} ).limit(1).next() );
db.oplog.rs.drop();
db.runCommand( { create: "oplog.rs", capped: true, size: ({{oplogSizeGB}} * 1024 * 1024 * 1024) } );
db.oplog.rs.save( db.temp.findOne() );
db.temp.drop();`
	scriptContent = strings.Replace(scriptContent, "{{oplogSizeGB}}", strconv.Itoa(c.ConfParams.NewOplogSize), -1)
	// 创建目录
	if err := util.MkDirsIfNotExists([]string{c.ScriptDir}); err != nil {
		c.runtime.Logger.Error("create script directory:%s fail, error:%s", c.ScriptDir, err)
		return fmt.Errorf("create script directory:%s fail, error:%s", c.ScriptDir, err)
	}
	// 创建文件
	c.runtime.Logger.Info("start to create script file")
	script, err := os.OpenFile(c.ScriptFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer script.Close()
	if err != nil {
		c.runtime.Logger.Error(
			fmt.Sprintf("create script file fail, error:%s", err))
		return fmt.Errorf("create script file fail, error:%s", err)
	}
	if _, err = script.WriteString(scriptContent); err != nil {
		c.runtime.Logger.Error(
			fmt.Sprintf("script file write content fail, error:%s",
				err))
		return fmt.Errorf("script file write content fail, error:%s",
			err)
	}
	// 修改配置文件属主
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", c.OsUser, c.OsGroup, c.ScriptDir),
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("chown script file fail, error:%s", err)
		return fmt.Errorf("chown script file fail, error:%s", err)
	}
	return nil
}

// standaloneStart 单机形式启动
func (c *MongoDChangeOplogSize) standaloneStart() error {
	if err := common.ShutdownMongoProcess(c.OsUser, "mongod", c.BinDir, c.DbpathDir,
		c.ConfParams.Port); err != nil {
		c.runtime.Logger.Error("shutdown mongod fail, error:%s", err)
		return fmt.Errorf("shutdown mongod fail, error:%s", err)
	}
	// 检查NewPort是否使用
	for {
		flag, _ := util.CheckPortIsInUse(c.ConfParams.IP, strconv.Itoa(c.NewPort))
		if flag {
			c.NewPort += 1
		}
		if !flag {
			break
		}
	}
	// 以单机形式启动
	cmd := fmt.Sprintf("%s --port %d --dbpath %s --fork", c.MongoD, c.NewPort, c.DbpathDir)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("startup mongod by port:%d fail, error:%s", c.NewPort, err)
		return fmt.Errorf("startup mongod by port:%d fail, error:%s", c.NewPort, err)
	}
	// 检查是否启动成功
	flag, _, err := common.CheckMongoService(c.NewPort)
	if err != nil || flag == false {
		c.runtime.Logger.Error("check mongod fail by port:%d fail, error:%s", c.NewPort, err)
		return fmt.Errorf("check mongod fail by port:%d fail, error:%s", c.NewPort, err)
	}
	return nil
}

// normalStart 正常启动
func (c *MongoDChangeOplogSize) normalStart() error {
	if err := common.ShutdownMongoProcess(c.OsUser, "mongod", c.BinDir, c.DbpathDir,
		c.NewPort); err != nil {
		c.runtime.Logger.Error("shutdown mongod about port:%d fail, error:%s", c.NewPort, err)
		return fmt.Errorf("shutdown mongod about port:%d fail, error:%s", c.NewPort, err)
	}
	if err := common.StartMongoProcess(c.BinDir, c.ConfParams.Port, c.OsUser, true); err != nil {
		c.runtime.Logger.Error("startup mongod about port:%d fail, error:%s", c.ConfParams.Port, err)
		return fmt.Errorf("startup mongod about port:%d fail, error:%s", c.ConfParams.Port, err)
	}
	// 检查是否启动成功
	flag, _, err := common.CheckMongoService(c.NewPort)
	if err != nil || flag == false {
		c.runtime.Logger.Error("check mongod fail about port:%d fail, error:%s", c.ConfParams.Port, err)
		return fmt.Errorf("check mongod fail about port:%d fail, error:%s", c.ConfParams.Port, err)
	}
	return nil
}

// setOplog db版本小于3.6修改oplog
func (c *MongoDChangeOplogSize) setOplog() error {
	// 关闭dbmon
	c.runtime.Logger.Info("stop dbmon")
	cmd := fmt.Sprintf("/home/%s/dbmon/stop.sh", c.OsUser)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("stop dbmon fail, error:%s", err)
		return fmt.Errorf("stop dbmon fail, error:%s", err)
	}

	// 如果是主库进行主备切换
	if c.ConfParams.IP == c.PrimaryIP && c.ConfParams.Port == c.PrimaryPort {
		c.runtime.Logger.Info("change primary to secondary")
		flag, err := common.AuthRsStepDown(c.Mongo, c.ConfParams.IP, c.ConfParams.Port, c.ConfParams.AdminUsername,
			c.ConfParams.AdminPassword)
		if err != nil {
			c.runtime.Logger.Error("change primary to secondary fail, error:%s", err)
			return fmt.Errorf("change primary to secondary fail, error:%s", err)
		}
		if !flag {
			c.runtime.Logger.Error("change primary to secondary fail")
			return fmt.Errorf("change primary to secondary fail")
		}
	}

	// 创建修改oplog脚本
	if err := c.createScript(); err != nil {
		return err
	}

	// 关闭进程以单机形式启动
	if err := c.standaloneStart(); err != nil {
		return err
	}

	// 执行修改oplog脚本脚本
	cmd = fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet %s",
		c.Mongo, c.ConfParams.AdminUsername, c.ConfParams.AdminPassword, c.ConfParams.IP, c.ConfParams.Port,
		c.ScriptFilePath)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("execute script fail, error:%s", err)
		return fmt.Errorf("execute script fail, error:%s", err)
	}
	// 检查新建oplog文档数量，需要等于1
	cmd = fmt.Sprintf(
		"%s  --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\" %s",
		c.Mongo, c.ConfParams.IP, c.ConfParams.Port, "db.getSiblingDB('local').oplog.rs.count()", "admin")
	result, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second)
	if err != nil {
		c.runtime.Logger.Error("check the number of new oplog document fail, error:%s", err)
		return fmt.Errorf("check the number of new oplog document fail, error:%s", err)
	}
	result = strings.Replace(result, "\n", "", -1)
	resultInt, _ := strconv.Atoi(result)
	if resultInt != 1 {
		c.runtime.Logger.Error("number of new oplog document is not equal 1, please check")
		return fmt.Errorf("number of new oplog document is not equal 1, please check")
	}

	// 关闭进程正常重启进程
	if err = c.normalStart(); err != nil {
		return err
	}

	// 开启dbmon
	c.runtime.Logger.Info("start dbmon")
	cmd = fmt.Sprintf("/home/%s/dbmon/start.sh", c.OsUser)
	if _, err = util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("start dbmon fail, error:%s", err)
		return fmt.Errorf("start dbmon fail, error:%s", err)
	}
	return nil
}

// setOplog3 db版本大于等于3.6修改oplog
func (c *MongoDChangeOplogSize) setOplog3() error {
	script := fmt.Sprintf("db.adminCommand({replSetResizeOplog: 1, size: %d})", c.NewOplogSizeMB)
	cmd := fmt.Sprintf(
		"%s  --host %s --port %d --authenticationDatabase=admin --quiet --eval \"%s\" %s",
		c.Mongo, c.ConfParams.IP, c.ConfParams.Port, script, "admin")
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		c.runtime.Logger.Error("change oplogSize fail, error:%s", err)
		return fmt.Errorf("change oplogSize fail, error:%s", err)
	}
	return nil
}

// changeOplogSize 修改oplog大小
func (c *MongoDChangeOplogSize) changeOplogSize() error {
	c.runtime.Logger.Info("start to change oplog size")
	if c.Version >= 3.6 {
		if err := c.setOplog3(); err != nil {
			return err
		}
	} else {
		if err := c.setOplog(); err != nil {
			return err
		}
	}
	c.runtime.Logger.Info("change oplog size successfully")
	return nil
}
