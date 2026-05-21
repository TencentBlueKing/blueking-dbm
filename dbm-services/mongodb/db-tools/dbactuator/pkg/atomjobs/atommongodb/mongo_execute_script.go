package atommongodb

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// ExecScriptConfParams 参数
type ExecScriptConfParams struct {
	IP             string   `json:"ip" validate:"required"`
	Port           int      `json:"port" validate:"required"`
	Type           string   `json:"type" validate:"required"` // cluster：执行脚本为传入的mongos replicaset：执行脚本为指定节点
	Secondary      bool     `json:"secondary"`                // 复制集是否在secondary节点执行script
	TaskId         string   `json:"taskid" validate:"required"`
	ScriptFile     bool     `json:"scriptFile"`     // 判断是否为通过脚本文件走制品库
	Script         string   `json:"script"`         // 集群初始化在primary执行的脚本内容
	ScriptName     string   `json:"scriptName"`     // 脚本名称
	ScriptNameList []string `json:"scriptNameList"` // 脚本名称列表
	AdminUsername  string   `json:"adminUsername" validate:"required"`
	AdminPassword  string   `json:"adminPassword" validate:"required"`
	RepoUrl        string   `json:"repoUrl"`      // 制品库url
	RepoUsername   string   `json:"repoUsername"` // 制品库用户名
	RepoToken      string   `json:"repoToken"`    // 制品库token
	RepoProject    string   `json:"repoProject"`  // 制品库project
	RepoRepo       string   `json:"repoRepo"`     // 制品库repo
	RepoPath       string   `json:"repoPath"`     // 制品库路径
}

// ExecScript 添加分片到集群
type ExecScript struct {
	BaseJob
	runtime            *jobruntime.JobGenericRuntime
	BinDir             string
	Mongo              string
	OsUser             string
	OsGroup            string
	execIP             string
	execPort           int
	ExecuteDir         string
	ScriptFilePathList []string
	ResultFilePathList []string
	ScriptFilePath     string
	ResultFilePath     string
	ConfParams         *ExecScriptConfParams
	MainVersion        float64
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
	// 获取主版本 设置客户端
	if err := e.getMainVersion(); err != nil {
		return err
	}

	// 脚本内容创建脚本文件 不走制品库
	if err := e.createScriptFile(); err != nil {
		return err
	}

	// 判断是否在secondary节点执行script
	if err := e.secondaryExecuteScriptChange(); err != nil {
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
	e.BinDir = consts.GetMongoBinDir()
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

	e.ExecuteDir = filepath.Join(consts.PackageSavePath, "dbactuator-"+e.ConfParams.TaskId)
	// 端口
	strPort := strconv.Itoa(e.ConfParams.Port)
	if e.ConfParams.ScriptFile == true {
		// 通过脚本文件走制品库
		for _, file := range e.ConfParams.ScriptNameList {
			e.ScriptFilePathList = append(e.ScriptFilePathList, filepath.Join(e.ExecuteDir, file))
			e.ResultFilePathList = append(e.ResultFilePathList, filepath.Join(e.ExecuteDir, strings.TrimSuffix(file, filepath.Ext(file))+"_"+strPort+"_result.txt"))
		}
	} else {
		// 不通过脚本文件走制品库
		e.ScriptFilePath = filepath.Join(e.ExecuteDir, strings.Join([]string{
			e.ConfParams.ScriptName + "_" + strPort + "_" + "script", "js"}, "."))
		e.ResultFilePath = filepath.Join(e.ExecuteDir, strings.Join([]string{
			e.ConfParams.ScriptName, strPort, strings.Join([]string{"result", "txt"}, ".")}, "_"))
		e.ScriptFilePathList = append(e.ScriptFilePathList, e.ScriptFilePath)
		e.ResultFilePathList = append(e.ResultFilePathList, e.ResultFilePath)
	}
	// 修改执行目录属组
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s:%s %s", e.OsUser, e.OsGroup, e.ExecuteDir),
		"", nil,
		60*time.Second); err != nil {
		e.runtime.Logger.Error("chown execute dir fail, error:%s", err)
		return fmt.Errorf("chown execute dir fail, error:%s", err)
	}

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

	e.runtime.Logger.Info("init successfully")

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
	if e.ConfParams.ScriptFile == false {
		if e.ConfParams.Script == "" {
			e.runtime.Logger.Error("ScriptFile parameters is false, validate parameters of Script fail, error: Script is empty")
			return fmt.Errorf("ScriptFile parameters is false, validate parameters of Script fail, error: Script is empty")
		}
	} else {
		if len(e.ConfParams.ScriptNameList) == 0 {
			e.runtime.Logger.Error("ScriptFile parameters is true, validate parameters of ScriptNameList fail, error: ScriptNameList is empty")
			return fmt.Errorf("ScriptFile parameters is true, validate parameters of ScriptNameList fail, error: ScriptNameList is empty")
		}
	}
	e.runtime.Logger.Info("validate parameters successfully")
	return nil
}

// createScriptFile 创建script文件
func (e *ExecScript) createScriptFile() error {
	if e.ConfParams.ScriptFile == true {
		return nil
	}
	// 创建文件
	e.runtime.Logger.Info("start to create script file")
	script, err := os.OpenFile(e.ScriptFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	if err != nil {
		e.runtime.Logger.Error("create script file fail, error:%s", err)
		return fmt.Errorf("create script file fail, error:%s", err)
	}
	defer script.Close()
	if _, err = script.WriteString(e.ConfParams.Script); err != nil {
		e.runtime.Logger.Error("script file write content fail, error:%s", err)
		return fmt.Errorf("script file write content fail, error:%s",
			err)
	}
	e.runtime.Logger.Info("create script file successfully")
	// 修改配置文件属主
	e.runtime.Logger.Info("start to execute chown command for script file")
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s:%s %s", e.OsUser, e.OsGroup, e.ExecuteDir),
		"", nil,
		60*time.Second); err != nil {
		e.runtime.Logger.Error("chown script file fail, error:%s", err)
		return fmt.Errorf("chown script file fail, error:%s", err)
	}
	e.runtime.Logger.Info("execute chown command for script file successfully")
	return nil
}

// getMainVersion 获取主版本
func (e *ExecScript) getMainVersion() error {
	// 获取mongo版本呢
	mongoName := "mongod"
	version, err := common.CheckMongoVersion(e.BinDir, mongoName)
	if err != nil {
		e.runtime.Logger.Error("get mongo service main version fail, error:%s", err)
		return fmt.Errorf("get mongo service main version fail, error:%s", err)
	}
	splitVersion := strings.Split(version, ".")
	mainVersion, _ := strconv.ParseFloat(strings.Join([]string{splitVersion[0], splitVersion[1]}, "."), 32)
	e.MainVersion = mainVersion
	if e.MainVersion >= 5.0 {
		e.Mongo = filepath.Join(e.BinDir, "mongodb", "bin", "mongosh")
	}
	e.runtime.Logger.Info("get mongo service main version:%f successfully", mainVersion)
	return nil
}

// secondaryExecuteScriptChange secondary执行script需要添加rs.slaveOk或者rs.secondaryOk
func (e *ExecScript) secondaryExecuteScriptChange() error {
	// 复制集，判断在primary节点还是在secondary节点执行脚本
	if e.ConfParams.Type == "replicaset" && e.ConfParams.Secondary == true {
		e.runtime.Logger.Info("secondary execute script start to add rs content")
		// secondary执行script
		secondaryOk := "rs.slaveOk()\n"
		if e.MainVersion >= 3.6 {
			secondaryOk = "rs.secondaryOk()\n"
		}
		for _, script := range e.ScriptFilePathList {
			if _, err := util.RunBashCmd(
				fmt.Sprintf("sed -i '1i\\%s' %s", secondaryOk, script),
				"", nil,
				60*time.Second); err != nil {
				e.runtime.Logger.Error("%s add %s content fail, error:%s", script, secondaryOk, err)
				return fmt.Errorf("%s add %s content fail, error:%s", script, secondaryOk, err)
			}
			e.runtime.Logger.Info("%s add %s content successfully", script, secondaryOk)
		}
		e.runtime.Logger.Info("secondary execute script add rs content successfully")
	}
	return nil
}

// execScript 执行脚本（使用 mycmd 调用 mongo，避免 RunBashCmd 记录明文密码）
func (e *ExecScript) execScript() error {
	e.runtime.Logger.Info("start to execute script")
	timeout := 86400 * 3 * time.Second // 3天
	for index, script := range e.ScriptFilePathList {
		e.runtime.Logger.Info("start to execute %s", script)
		resultFile := e.ResultFilePathList[index]
		resultF, err := os.OpenFile(resultFile, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
		if err != nil {
			e.runtime.Logger.Error("open result file fail:%s", err)
			return fmt.Errorf("open result file %s: %w", resultFile, err)
		}

		var stderrBuf bytes.Buffer
		cmdBuilder := mycmd.New(
			e.Mongo,
			"-u", e.ConfParams.AdminUsername,
			"-p", mycmd.Password(e.ConfParams.AdminPassword),
			"--host", e.execIP,
			"--port", strconv.Itoa(e.execPort),
			"--authenticationDatabase=admin",
			"--quiet",
			script,
		)
		maskedCmdline := cmdBuilder.GetCmdLine("", true)
		ret, err := cmdBuilder.Run3(timeout, resultF, &stderrBuf)
		if err != nil {
			stderr := strings.TrimSpace(stderrBuf.String())
			e.runtime.Logger.Error(
				"execute mongo script fail, cmd:%q, exitCode:%d, stdout:%q, stderr:%q, err:%v",
				maskedCmdline, ret.ExitCode, ret.GetStdout(), stderr, err,
			)
			if stderr != "" {
				return fmt.Errorf("execute mongo script fail: %w (stderr: %s)", err, stderr)
			}
			return fmt.Errorf("execute mongo script fail: %w", err)
		}
		resultF.Close()
		e.runtime.Logger.Info("execute cmd:%s successfully", maskedCmdline)
	}

	e.runtime.Logger.Info("execute mongo script successfully")
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
	for _, resultFile := range e.ResultFilePathList {
		// url
		url := strings.Join([]string{e.ConfParams.RepoUrl, "generic", e.ConfParams.RepoProject, e.ConfParams.RepoRepo,
			e.ConfParams.RepoPath, filepath.Base(resultFile)}, "/")
		e.runtime.Logger.Info("upload file url: %s", url)

		// 生成请求body内容
		file, err := os.ReadFile(resultFile)
		if err != nil {
			e.runtime.Logger.Error("get result file:%s content fail, error:%s", resultFile, err)
			return fmt.Errorf("get result file:%s content fail, error:%s", resultFile, err)
		}

		// 生成请求
		request, err := http.NewRequest("PUT", url, strings.NewReader(string(file)))
		if err != nil {
			e.runtime.Logger.Error("create request for uploading result file:%s fail, error:%s", resultFile, err)
			return fmt.Errorf("create request for uploading result file:%s fail, error:%s", resultFile, err)
		}

		// 设置请求头
		auth := base64.StdEncoding.EncodeToString([]byte(strings.Join([]string{e.ConfParams.RepoUsername,
			e.ConfParams.RepoToken}, ":")))
		request.Header.Set("Authorization", "Basic "+auth)
		request.Header.Set("X-BKREPO-EXPIRES", "30")
		request.Header.Set("X-BKREPO-OVERWRITE", "true")
		request.Header.Set("Content-Type", "multipart/form-data")

		// 执行请求
		response, err := http.DefaultClient.Do(request)
		if err != nil {
			e.runtime.Logger.Error("request server for uploading result file fail, error:%s", err)
			return fmt.Errorf("request server for uploading result file fail, error:%s", err)
		}

		// 解析响应
		resp, err := io.ReadAll(response.Body)
		if err != nil {
			e.runtime.Logger.Error("read data from response fail, error:%s", err)
			return fmt.Errorf("read data from response fail, error:%s", err)
		}
		output := Output{}
		_ = json.Unmarshal(resp, &output)
		if output.Code != 0 && output.Message == "" {
			e.runtime.Logger.Error("upload file:%s fail, error:%s", resultFile, output.Message)
			return fmt.Errorf("upload file:%s fail, error:%s", resultFile, output.Message)
		}
		response.Body.Close()
		e.runtime.Logger.Info("upload result file:%s successfully", resultFile)
	}

	e.runtime.Logger.Info("upload result file successfully")
	return nil
}
