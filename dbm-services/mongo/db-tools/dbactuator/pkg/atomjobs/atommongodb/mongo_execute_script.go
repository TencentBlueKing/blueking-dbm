package atommongodb

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
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

// ExecScriptConfParams 参数
type ExecScriptConfParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"`
	Script        string `json:"script" validate:"required"`
	Type          string `json:"type" validate:"required"` // cluster：执行脚本为传入的mongos replicaset：执行脚本为指定节点
	Secondary     bool   `json:"secondary"`                // 复制集是否在secondary节点执行script
	AdminUsername string `json:"adminUsername" validate:"required"`
	AdminPassword string `json:"adminPassword" validate:"required"`
	RepoUrl       string `json:"repoUrl"`      // 制品库url
	RepoUsername  string `json:"repoUsername"` // 制品库用户名
	RepoToken     string `json:"repoToken"`    // 制品库token
	RepoProject   string `json:"repoProject"`  // 制品库project
	RepoRepo      string `json:"repoRepo"`     // 制品库repo
	RepoPath      string `json:"repoPath"`     // 制品库路径
}

// ExecScript 添加分片到集群
type ExecScript struct {
	runtime        *jobruntime.JobGenericRuntime
	BinDir         string
	Mongo          string
	OsUser         string
	OsGroup        string
	execIP         string
	execPort       int
	ScriptDir      string
	ScriptContent  string
	ScriptFilePath string
	ResultFilePath string
	ConfParams     *ExecScriptConfParams
}

// NewExecScript 实例化结构体
func NewExecScript() jobruntime.JobRunner {
	return &ExecScript{}
}

// Name 获取原子任务的名字
func (e *ExecScript) Name() string {
	return "mongo_execute_script"
}

// Run 运行原子任务
func (e *ExecScript) Run() error {
	// 生成script内容
	if err := e.makeScriptContent(); err != nil {
		return err
	}

	// 创建script文件
	if err := e.creatScriptFile(); err != nil {
		return err
	}

	// 执行脚本生成结果文件
	if err := e.execScript(); err != nil {
		return err
	}

	// 上传结果文件到制品库
	if err := e.uploadFile(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (e *ExecScript) Retry() uint {
	return 2
}

// Rollback 回滚
func (e *ExecScript) Rollback() error {
	return nil
}

// Init 初始化
func (e *ExecScript) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	e.runtime = runtime
	e.runtime.Logger.Info("start to init")
	e.BinDir = consts.UsrLocal
	e.OsUser = consts.GetProcessUser()
	e.OsGroup = consts.GetProcessUserGroup()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(e.runtime.PayloadDecoded), &e.ConfParams); err != nil {
		e.runtime.Logger.Error(
			"get parameters of execScript fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of execScript fail by json.Unmarshal, error:%s", err)
	}

	// 获取各种目录
	e.Mongo = filepath.Join(e.BinDir, "mongodb", "bin", "mongo")
	e.ScriptDir = filepath.Join("/", "home", e.OsUser, e.runtime.UID)
	e.ScriptFilePath = filepath.Join(e.ScriptDir, strings.Join([]string{"script", "js"}, "."))
	e.ResultFilePath = filepath.Join(e.ScriptDir, strings.Join([]string{"result", "txt"}, "."))
	e.runtime.Logger.Info("init successfully")

	// 复制集获取执行脚本的IP端口 默认为primary节点 可以指定secondary节点
	if e.ConfParams.Type == "cluster" {
		e.execIP = e.ConfParams.IP
		e.execPort = e.ConfParams.Port
	}
	if e.ConfParams.Type == "replicaset" {
		primaryInfo, err := common.AuthGetPrimaryInfo(e.Mongo, e.ConfParams.AdminUsername,
			e.ConfParams.AdminPassword,
			e.ConfParams.IP, e.ConfParams.Port)
		if err != nil {
			e.runtime.Logger.Error("init get primary info fail, error:%s", err)
			return fmt.Errorf("init get primary info fail, error:%s", err)
		}
		e.execIP = strings.Split(primaryInfo, ":")[0]
		e.execPort, _ = strconv.Atoi(strings.Split(primaryInfo, ":")[1])
		if e.ConfParams.Secondary == true {
			_, _, _, _, _, memberInfo, err := common.GetNodeInfo(e.Mongo, e.ConfParams.IP, e.ConfParams.Port,
				e.ConfParams.AdminUsername, e.ConfParams.AdminPassword, e.ConfParams.IP, e.ConfParams.Port)
			if err != nil {
				e.runtime.Logger.Error("init get member info fail, error:%s", err)
				return fmt.Errorf("init get member info fail, error:%s", err)
			}
			for _, v := range memberInfo {
				if v["state"] == "2" && v["hidden"] == "false" {
					e.execIP = strings.Split(v["name"], ":")[0]
					e.execPort, _ = strconv.Atoi(strings.Split(v["name"], ":")[1])
				}
			}
		}
	}

	// 进行校验
	if err := e.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (e *ExecScript) checkParams() error {
	// 校验配置参数
	e.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.runtime.Logger.Info("start to validate parameters of deInstall")
	if err := validate.Struct(e.ConfParams); err != nil {
		e.runtime.Logger.Error("validate parameters of execScript fail, error:%s", err)
		return fmt.Errorf("validate parameters of execScript fail, error:%s", err)
	}
	e.runtime.Logger.Info("validate parameters successfully")
	return nil
}

// makeScriptContent 生成script内容
func (e *ExecScript) makeScriptContent() error {
	// 复制集，判断在primary节点还是在secondary节点执行脚本
	e.runtime.Logger.Info("start to make script content")
	if e.ConfParams.Type == "replicaset" && e.ConfParams.Secondary == true {
		// 获取mongo版本呢
		mongoName := "mongod"
		version, err := common.CheckMongoVersion(e.BinDir, mongoName)
		if err != nil {
			e.runtime.Logger.Error("get mongo service version fail, error:%s", err)
			return fmt.Errorf("get mongo service version fail, error:%s", err)
		}
		splitVersion := strings.Split(version, ".")
		mainVersion, _ := strconv.ParseFloat(strings.Join([]string{splitVersion[0], splitVersion[1]}, "."), 32)

		// secondary执行script
		secondaryOk := "rs.slaveOk()\n"
		if mainVersion >= 3.6 {
			secondaryOk = "rs.secondaryOk()\n"
		}
		e.ScriptContent = strings.Join([]string{secondaryOk, e.ConfParams.Script}, "")
		e.runtime.Logger.Info("make script content successfully")
		return nil
	}
	e.ScriptContent = e.ConfParams.Script
	e.runtime.Logger.Info("make script content successfully")
	return nil
}

// creatScriptFile 创建script文件
func (e *ExecScript) creatScriptFile() error {
	// 创建目录
	e.runtime.Logger.Info("start to make script directory")
	if err := util.MkDirsIfNotExists([]string{e.ScriptDir}); err != nil {
		e.runtime.Logger.Error("create script directory:%s fail, error:%s", e.ScriptDir, err)
		return fmt.Errorf("create script directory:%s fail, error:%s", e.ScriptDir, err)
	}

	// 创建文件
	e.runtime.Logger.Info("start to create script file")
	script, err := os.OpenFile(e.ScriptFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	defer script.Close()
	if err != nil {
		e.runtime.Logger.Error(
			fmt.Sprintf("create script file fail, error:%s", err))
		return fmt.Errorf("create script file fail, error:%s", err)
	}
	if _, err = script.WriteString(e.ScriptContent); err != nil {
		e.runtime.Logger.Error(
			fmt.Sprintf("script file write content fail, error:%s",
				err))
		return fmt.Errorf("script file write content fail, error:%s",
			err)
	}
	e.runtime.Logger.Info("create script file successfully")
	// 修改配置文件属主
	e.runtime.Logger.Info("start to execute chown command for script file")
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", e.OsUser, e.OsGroup, e.ScriptDir),
		"", nil,
		10*time.Second); err != nil {
		e.runtime.Logger.Error(fmt.Sprintf("chown script file fail, error:%s", err))
		return fmt.Errorf("chown script file fail, error:%s", err)
	}
	e.runtime.Logger.Info("execute chown command for script file successfully")
	return nil
}

// execScript 执行脚本
func (e *ExecScript) execScript() error {
	e.runtime.Logger.Info("start to execute script")
	cmd := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet  %s > %s",
		e.Mongo, e.ConfParams.AdminUsername, e.ConfParams.AdminPassword, e.execIP, e.execPort,
		e.ScriptFilePath, e.ResultFilePath)
	cmdX := fmt.Sprintf(
		"%s -u %s -p '%s' --host %s --port %d --authenticationDatabase=admin --quiet  %s > %s",
		e.Mongo, e.ConfParams.AdminUsername, "xxx", e.execIP, e.execPort,
		e.ScriptFilePath, e.ResultFilePath)
	if _, err := util.RunBashCmd(
		cmd,
		"", nil,
		10*time.Second); err != nil {
		e.runtime.Logger.Error("execute script:%s fail, error:%s", cmdX, err)
		return fmt.Errorf("execute script:%s fail, error:%s", cmdX, err)
	}
	e.runtime.Logger.Info("execute script:%s successfully", cmdX)
	return nil
}

// Output 请求响应结构体
type Output struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// uploadFile 上传结果文件
func (e *ExecScript) uploadFile() error {
	if e.ConfParams.RepoUrl == "" {
		return nil
	}
	e.runtime.Logger.Info("start to upload result file")
	// url
	url := strings.Join([]string{e.ConfParams.RepoUrl, e.ConfParams.RepoProject, e.ConfParams.RepoRepo,
		e.ConfParams.RepoPath, e.runtime.UID, "result.txt"}, "/")

	// 生成请求body内容
	file, err := ioutil.ReadFile(e.ResultFilePath)
	if err != nil {
		e.runtime.Logger.Error("get result file content fail, error:%s", err)
		return fmt.Errorf("get result file content fail, error:%s", err)
	}

	// 生成请求
	request, err := http.NewRequest("PUT", url, strings.NewReader(string(file)))
	if err != nil {
		e.runtime.Logger.Error("create request for uploading result file fail, error:%s", err)
		return fmt.Errorf("create request for uploading result file fail, error:%s", err)
	}

	// 设置请求头
	auth := base64.StdEncoding.EncodeToString([]byte(strings.Join([]string{e.ConfParams.RepoUsername,
		e.ConfParams.RepoToken}, ":")))
	request.Header.Set("Authorization", "Basic "+auth)
	request.Header.Set("X-BKREPO-EXPIRES", "30")
	request.Header.Set("X-BKREPO-OVERWRITE", "true")
	request.Header.Set("Content-Type", "multipart/form-data")
	if err != nil {
		e.runtime.Logger.Error("set request head for uploading result file fail, error:%s", err)
		return fmt.Errorf("set request head for uploading result file fail, error:%s", err)
	}

	// 执行请求
	response, err := http.DefaultClient.Do(request)
	defer response.Body.Close()
	if err != nil {
		e.runtime.Logger.Error("request server for uploading result file fail, error:%s", err)
		return fmt.Errorf("request server for uploading result file fail, error:%s", err)
	}

	// 解析响应
	resp, err := ioutil.ReadAll(response.Body)
	if err != nil {
		e.runtime.Logger.Error("read data from response fail, error:%s", err)
		return fmt.Errorf("read data from response fail, error:%s", err)
	}
	output := Output{}
	_ = json.Unmarshal(resp, &output)
	if output.Code != 0 && output.Message == "" {
		e.runtime.Logger.Error("upload file fail, error:%s", output.Message)
		return fmt.Errorf("upload file fail, error:%s", output.Message)
	}
	e.runtime.Logger.Info("upload result file successfully")
	return nil
}
