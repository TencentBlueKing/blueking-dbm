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

const scriptExecDoneMarker = ".script_exec_done"

// ExecScriptConfParams 参数
type ExecScriptConfParams struct {
	IP             string   `json:"ip" validate:"required"`
	Port           int      `json:"port" validate:"required"`
	Type           string   `json:"type" validate:"required"` // cluster：mongos；replicaset：副本集
	TaskId         string   `json:"taskid" validate:"required"`
	ScriptFile     bool     `json:"scriptFile"`     // true：脚本文件已由制品库下发；false：使用 Script 内容现场写文件
	Script         string   `json:"script"`         // ScriptFile=false 时的脚本内容
	ScriptName     string   `json:"scriptName"`     // ScriptFile=false 时的脚本名
	ScriptNameList []string `json:"scriptNameList"` // ScriptFile=true 时的脚本名列表
	AdminUsername  string   `json:"adminUsername" validate:"required"`
	AdminPassword  string   `json:"adminPassword" validate:"required"`
	// ClusterName 集群名称，用于结果文件命名（与脚本编号一起区分多集群/多脚本结果）
	ClusterName string `json:"clusterName"`
	// DbVersion 实例主版本（如 mongodb-3.0.15 / 3.0.15）。多版本共享主机上
	// /usr/local/mongodb 可能指向其它版本，不能用来选 mongo/mongosh。
	DbVersion    string `json:"dbVersion"`
	RepoUrl      string `json:"repoUrl"`
	RepoUsername string `json:"repoUsername"`
	RepoToken    string `json:"repoToken"`
	RepoProject  string `json:"repoProject"`
	RepoRepo     string `json:"repoRepo"`
	RepoPath     string `json:"repoPath"`
}

// ExecScript MongoDB 脚本执行原子任务
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
	// 上传失败重试：若上次全部脚本已成功（每脚本完成标记 + 结果文件齐全），跳过再执行，只补上传
	if e.canSkipRunScripts() {
		e.runtime.Logger.Info(
			"skip runScripts: done markers and result files exist under %s, upload only",
			e.ExecuteDir)
	} else {
		if err := e.resolveMongoShellByVersion(); err != nil {
			return err
		}
		if err := e.createScriptFile(); err != nil {
			return err
		}
		// 兼容 mongosh: 老脚本里可能使用 mongo shell 的别名 getSisterDB
		if err := e.normalizeScriptCompatibility(); err != nil {
			return err
		}
		if err := e.runScripts(); err != nil {
			return err
		}
	}

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
	e.runtime = runtime
	e.runtime.Logger.Info("start to init")
	e.BinDir = consts.GetMongoBinDir()
	e.OsUser = consts.GetProcessUser()
	e.OsGroup = consts.GetProcessUserGroup()

	if err := json.Unmarshal([]byte(e.runtime.PayloadDecoded), &e.ConfParams); err != nil {
		e.runtime.Logger.Error("get parameters of execScript fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of execScript fail by json.Unmarshal, error:%s", err)
	}

	// Init 阶段统一用 mongo（环境保证 ≥5 也带 mongo）；Run 里再按版本切 mongosh
	e.Mongo = filepath.Join(e.BinDir, "mongodb", "bin", "mongo")
	e.ExecuteDir = filepath.Join(consts.PackageSavePath, "dbactuator-"+e.ConfParams.TaskId)

	strPort := strconv.Itoa(e.ConfParams.Port)
	if e.ConfParams.ScriptFile {
		for i, file := range e.ConfParams.ScriptNameList {
			e.ScriptFilePathList = append(e.ScriptFilePathList, filepath.Join(e.ExecuteDir, file))
			scriptBase := strings.TrimSuffix(file, filepath.Ext(file))
			resultName := buildScriptResultFileName(e.ConfParams.ClusterName, i+1, scriptBase)
			e.ResultFilePathList = append(e.ResultFilePathList, filepath.Join(e.ExecuteDir, resultName))
		}
	} else {
		scriptPath := filepath.Join(e.ExecuteDir, fmt.Sprintf("%s_%s_script.js", e.ConfParams.ScriptName, strPort))
		resultName := buildScriptResultFileName(e.ConfParams.ClusterName, 1, e.ConfParams.ScriptName)
		resultPath := filepath.Join(e.ExecuteDir, resultName)
		e.ScriptFilePathList = append(e.ScriptFilePathList, scriptPath)
		e.ResultFilePathList = append(e.ResultFilePathList, resultPath)
	}

	if err := e.chownExecuteDir(); err != nil {
		return err
	}

	// 复制集在 primary 上执行；分片集群使用传入的 mongos
	switch e.ConfParams.Type {
	case "cluster":
		e.execIP = e.ConfParams.IP
		e.execPort = e.ConfParams.Port
	case "replicaset":
		primaryInfo, err := common.GetPrimaryInfo(
			e.Mongo, e.ConfParams.AdminUsername, e.ConfParams.AdminPassword,
			e.ConfParams.IP, e.ConfParams.Port)
		if err != nil {
			e.runtime.Logger.Error("init get primary info fail, error:%s", err)
			return fmt.Errorf("init get primary info fail, error:%s", err)
		}
		parts := strings.Split(primaryInfo, ":")
		if len(parts) != 2 {
			return fmt.Errorf("invalid primary info: %s", primaryInfo)
		}
		e.execIP = parts[0]
		e.execPort, _ = strconv.Atoi(parts[1])
	}

	e.runtime.Logger.Info("init successfully")
	return e.checkParams()
}

// buildScriptResultFileName 结果文件名：{集群名称}_{脚本编号}_{脚本名}_result.txt
// scriptNo 从 1 起；clusterName 为空时用 cluster 占位，兼容旧 payload。
func buildScriptResultFileName(clusterName string, scriptNo int, scriptBase string) string {
	if clusterName == "" {
		clusterName = "cluster"
	}
	return fmt.Sprintf("%s_%d_%s_result.txt", clusterName, scriptNo, scriptBase)
}

func (e *ExecScript) chownExecuteDir() error {
	if _, err := mycmd.New("chown", "-R", e.OsUser+":"+e.OsGroup, e.ExecuteDir).Run(60 * time.Second); err != nil {
		e.runtime.Logger.Error("chown execute dir fail, error:%s", err)
		return fmt.Errorf("chown execute dir fail, error:%s", err)
	}
	return nil
}

// newMongoCmd 构造带认证的 mongo/mongosh 命令（不含脚本参数）
func (e *ExecScript) newMongoCmd(extra ...any) *mycmd.CmdBuilder {
	args := []any{
		e.Mongo,
		"-u", e.ConfParams.AdminUsername,
		"-p", mycmd.Password(e.ConfParams.AdminPassword),
		"--host", e.execIP,
		"--port", strconv.Itoa(e.execPort),
		"--authenticationDatabase=admin",
		"--quiet",
	}
	return mycmd.New(append(args, extra...)...)
}

// checkParams 校验参数
func (e *ExecScript) checkParams() error {
	e.runtime.Logger.Info("start to validate parameters")
	if err := validator.New().Struct(e.ConfParams); err != nil {
		e.runtime.Logger.Error("validate parameters of execScript fail, error:%s", err)
		return fmt.Errorf("validate parameters of execScript fail, error:%s", err)
	}
	if !e.ConfParams.ScriptFile {
		if e.ConfParams.Script == "" {
			return fmt.Errorf("ScriptFile is false but Script is empty")
		}
	} else if len(e.ConfParams.ScriptNameList) == 0 {
		return fmt.Errorf("ScriptFile is true but ScriptNameList is empty")
	}
	e.runtime.Logger.Info("validate parameters successfully")
	return nil
}

// createScriptFile 创建script文件（仅 ScriptFile=false）
func (e *ExecScript) createScriptFile() error {
	if e.ConfParams.ScriptFile {
		return nil
	}
	if len(e.ScriptFilePathList) == 0 {
		return fmt.Errorf("script file path list is empty")
	}
	scriptPath := e.ScriptFilePathList[0]
	e.runtime.Logger.Info("start to create script file: %s", scriptPath)
	if err := os.WriteFile(scriptPath, []byte(e.ConfParams.Script), DefaultPerm); err != nil {
		e.runtime.Logger.Error("create script file fail, error:%s", err)
		return fmt.Errorf("create script file fail, error:%s", err)
	}
	return e.chownExecuteDir()
}

// resolveMongoShellByVersion 获取主版本并选择 mongo shell 客户端。
// 优先使用 payload.dbVersion / 实例探测版本；不要用 BinDir 下 mongod -version。
func (e *ExecScript) resolveMongoShellByVersion() error {
	version := strings.TrimSpace(e.ConfParams.DbVersion)
	if version != "" {
		e.runtime.Logger.Info("resolveMongoShellByVersion use payload dbVersion:%s", version)
	} else {
		probed, err := e.probeInstanceVersion()
		if err != nil {
			e.runtime.Logger.Warn(
				"probe instance version fail (%v), fallback to binDir mongod -version", err)
			version, err = common.CheckMongoVersion(e.BinDir, "mongod")
			if err != nil {
				e.runtime.Logger.Error("get mongo service main version fail, error:%s", err)
				return fmt.Errorf("get mongo service main version fail, error:%s", err)
			}
		} else {
			version = probed
			e.runtime.Logger.Info("resolveMongoShellByVersion probed instance version:%s", version)
		}
	}
	mainVersion, err := strconv.ParseFloat(versionMajorMinor(version), 64)
	if err != nil {
		e.runtime.Logger.Error("parse mongo service major.minor version fail, version:%s, error:%s", version, err)
		return fmt.Errorf("parse mongo service major.minor version fail, version:%s, error:%s", version, err)
	}
	e.MainVersion = mainVersion
	mongoExeName := "mongo"
	if e.MainVersion >= 5.0 {
		mongoExeName = "mongosh"
	}
	e.Mongo = filepath.Join(e.BinDir, "mongodb", "bin", mongoExeName)
	e.runtime.Logger.Info(
		"resolveMongoShellByVersion successfully, mongoExeName:%s, mainVersion:%f", mongoExeName, mainVersion)
	return nil
}

// probeInstanceVersion 用 Init 阶段的 mongo 客户端探测实例版本
func (e *ExecScript) probeInstanceVersion() (string, error) {
	ret, err := e.newMongoCmd("--eval", "db.version()").Run(60 * time.Second)
	if err != nil {
		return "", fmt.Errorf(
			"probe instance version fail: exit=%d err=%v stdout=%q stderr=%q",
			ret.ExitCode, err, ret.GetStdout(), ret.GetStderr(),
		)
	}
	version := strings.TrimSpace(ret.GetStdout())
	if version == "" {
		return "", fmt.Errorf("probe instance version returned empty")
	}
	return version, nil
}

// normalizeScriptCompatibility 执行前兼容老 mongo shell 脚本写法
// 替换 getSisterDB 为 getSiblingDB
// 因为 mongosh 5.0 开始弃用 getSisterDB，改为 getSiblingDB
func (e *ExecScript) normalizeScriptCompatibility() error {
	for _, script := range e.ScriptFilePathList {
		content, err := os.ReadFile(script)
		if err != nil {
			e.runtime.Logger.Error("read script file %s fail, error:%s", script, err)
			return fmt.Errorf("read script file %s fail, error:%s", script, err)
		}
		normalized := strings.ReplaceAll(string(content), "getSisterDB", "getSiblingDB")
		if normalized == string(content) {
			continue
		}
		if err := os.WriteFile(script, []byte(normalized), DefaultPerm); err != nil {
			e.runtime.Logger.Error("normalize script file %s fail, error:%s", script, err)
			return fmt.Errorf("normalize script file %s fail, error:%s", script, err)
		}
		e.runtime.Logger.Info("normalize getSisterDB to getSiblingDB for script file %s successfully", script)
	}
	return nil
}

// execDoneMarkerPath 单脚本完成标记：.script_exec_done_{port}_{idx}_{脚本名}
// ExecuteDir 只按 taskid（单据 uid）命名，同一单据在同一台机器上的多个实例、多个脚本会共用该目录；
// 因此按「端口 + 脚本编号(1-based) + 脚本名」隔离，避免误判跳过。
func (e *ExecScript) execDoneMarkerPath(scriptNo int, scriptPath string) string {
	base := filepath.Base(scriptPath)
	base = strings.TrimSuffix(base, filepath.Ext(base))
	// 文件名整体不能超过文件系统上限，脚本名由用户上传，做一次截断
	if len(base) > 180 {
		base = base[:180]
	}
	return filepath.Join(e.ExecuteDir,
		fmt.Sprintf("%s_%d_%d_%s", scriptExecDoneMarker, e.ConfParams.Port, scriptNo, base))
}

// isOneScriptDone 判断第 index（0-based）个脚本是否已成功执行。
func (e *ExecScript) isOneScriptDone(index int) bool {
	if index < 0 || index >= len(e.ScriptFilePathList) || index >= len(e.ResultFilePathList) {
		return false
	}
	scriptNo := index + 1
	if !util.FileExists(e.execDoneMarkerPath(scriptNo, e.ScriptFilePathList[index])) {
		return false
	}
	fi, err := os.Stat(e.ResultFilePathList[index])
	return err == nil && fi.Size() > 0
}

// canSkipRunScripts 判断上次全部脚本是否已成功执行，用于上传失败后的重试。
func (e *ExecScript) canSkipRunScripts() bool {
	// 跳过重跑只为「脚本已成功、仅上传失败」的重试服务；没有制品库时上传是空操作，
	// 重试必然是脚本本身失败，必须重跑。
	if e.ConfParams.RepoUrl == "" {
		return false
	}
	if e.ExecuteDir == "" || len(e.ResultFilePathList) == 0 {
		return false
	}
	for i := range e.ScriptFilePathList {
		if !e.isOneScriptDone(i) {
			return false
		}
	}
	return true
}

// writeOneExecDoneMarker 单个脚本成功后写入完成标记，供重试时跳过该脚本。
func (e *ExecScript) writeOneExecDoneMarker(scriptNo int, scriptPath string) error {
	marker := e.execDoneMarkerPath(scriptNo, scriptPath)
	content := fmt.Sprintf("taskid=%s\nport=%d\nscriptNo=%d\nscript=%s\n",
		e.ConfParams.TaskId, e.ConfParams.Port, scriptNo, filepath.Base(scriptPath))
	if err := os.WriteFile(marker, []byte(content), DefaultPerm); err != nil {
		e.runtime.Logger.Error("write script exec done marker fail, error:%s", err)
		return fmt.Errorf("write script exec done marker fail, error:%s", err)
	}
	e.runtime.Logger.Info("write script exec done marker successfully: %s", marker)
	return nil
}

// runScripts 执行脚本（使用 mycmd 调用 mongo，避免 RunBashCmd 记录明文密码）
func (e *ExecScript) runScripts() error {
	e.runtime.Logger.Info("start to execute %d scripts on primary node %s:%d", len(e.ScriptFilePathList), e.execIP, e.execPort)
	timeout := 86400 * 3 * time.Second // 3天

	for index, script := range e.ScriptFilePathList {
		scriptNo := index + 1
		// 上传失败重试：已成功的脚本（完成标记 + 结果文件）可单独跳过
		if e.ConfParams.RepoUrl != "" && e.isOneScriptDone(index) {
			e.runtime.Logger.Info(
				"skip script #%d %s: done marker and result file exist",
				scriptNo, script)
			continue
		}
		if err := e.runOneScript(script, e.ResultFilePathList[index], timeout); err != nil {
			return err
		}
		if err := e.writeOneExecDoneMarker(scriptNo, script); err != nil {
			return err
		}
		if err := e.cleanupGeneratedScript(script); err != nil {
			return err
		}
	}

	e.runtime.Logger.Info("execute %d scripts on primary node %s:%d successfully", len(e.ScriptFilePathList), e.execIP, e.execPort)
	return nil
}

// cleanupGeneratedScript 删除安装流程现场生成的额外管理用户脚本，避免密码长期残留在磁盘。
// 制品库下发的脚本由其它流程管理，不在这里删除。
func (e *ExecScript) cleanupGeneratedScript(script string) error {
	if e.ConfParams.ScriptFile || !strings.HasPrefix(filepath.Base(script), "create_extra_user_") {
		return nil
	}
	if err := os.Remove(script); err != nil && !os.IsNotExist(err) {
		e.runtime.Logger.Error("remove generated script %s fail, error:%s", script, err)
		return fmt.Errorf("remove generated script %s fail: %w", script, err)
	}
	e.runtime.Logger.Info("remove generated script successfully: %s", script)
	return nil
}

func (e *ExecScript) runOneScript(script, resultFile string, timeout time.Duration) error {
	e.runtime.Logger.Info("start to execute %s", script)
	resultF, err := os.OpenFile(resultFile, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	if err != nil {
		e.runtime.Logger.Error("open result file fail:%s", err)
		return fmt.Errorf("open result file %s: %w", resultFile, err)
	}
	defer resultF.Close()

	cmdBuilder := e.newMongoCmd()
	// mongosh 需 --file；mongo shell 直接跟脚本路径
	if strings.HasSuffix(e.Mongo, "mongosh") {
		cmdBuilder.Append("--file")
	}
	cmdBuilder.Append(script)

	maskedCmdline := cmdBuilder.GetCmdLine("", true)
	var stderrBuf bytes.Buffer
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
	e.runtime.Logger.Info("execute cmd:%s successfully", maskedCmdline)
	return nil
}

// execScriptUploadResp 制品库上传响应
type execScriptUploadResp struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// uploadFile 上传结果文件
func (e *ExecScript) uploadFile() error {
	if e.ConfParams.RepoUrl == "" {
		return nil
	}
	e.runtime.Logger.Info("start to upload result file")
	client := &http.Client{Timeout: 5 * time.Minute}
	for _, resultFile := range e.ResultFilePathList {
		uploadURL := strings.Join([]string{
			strings.TrimRight(e.ConfParams.RepoUrl, "/"),
			"generic", e.ConfParams.RepoProject, e.ConfParams.RepoRepo,
			strings.Trim(e.ConfParams.RepoPath, "/"),
			filepath.Base(resultFile),
		}, "/")
		e.runtime.Logger.Info("upload file url: %s", uploadURL)

		file, err := os.ReadFile(resultFile)
		if err != nil {
			e.runtime.Logger.Error("get result file:%s content fail, error:%s", resultFile, err)
			return fmt.Errorf("get result file:%s content fail, error:%s", resultFile, err)
		}

		request, err := http.NewRequest(http.MethodPut, uploadURL, bytes.NewReader(file))
		if err != nil {
			e.runtime.Logger.Error("create request for uploading result file:%s fail, error:%s", resultFile, err)
			return fmt.Errorf("create request for uploading result file:%s fail, error:%s", resultFile, err)
		}
		auth := base64.StdEncoding.EncodeToString([]byte(
			e.ConfParams.RepoUsername + ":" + e.ConfParams.RepoToken))
		request.Header.Set("Authorization", "Basic "+auth)
		request.Header.Set("X-BKREPO-EXPIRES", "30")
		request.Header.Set("X-BKREPO-OVERWRITE", "true")
		request.Header.Set("Content-Type", "application/octet-stream")

		response, err := client.Do(request)
		if err != nil {
			e.runtime.Logger.Error("request server for uploading result file fail, error:%s", err)
			return fmt.Errorf("request server for uploading result file fail, error:%s", err)
		}
		respBody, err := io.ReadAll(response.Body)
		_ = response.Body.Close()
		if err != nil {
			e.runtime.Logger.Error("read data from response fail, error:%s", err)
			return fmt.Errorf("read data from response fail, error:%s", err)
		}
		if response.StatusCode < 200 || response.StatusCode >= 300 {
			return fmt.Errorf(
				"upload file:%s fail, http status=%d body=%s",
				resultFile, response.StatusCode, string(respBody))
		}
		var output execScriptUploadResp
		if err := json.Unmarshal(respBody, &output); err != nil {
			e.runtime.Logger.Warn("upload response not json, status=%d body=%s", response.StatusCode, string(respBody))
		} else if output.Code != 0 {
			e.runtime.Logger.Error("upload file:%s fail, code=%d message=%s", resultFile, output.Code, output.Message)
			return fmt.Errorf("upload file:%s fail, code=%d message=%s", resultFile, output.Code, output.Message)
		}
		e.runtime.Logger.Info("upload result file:%s successfully", resultFile)
	}

	e.runtime.Logger.Info("upload result file successfully")
	return nil
}
