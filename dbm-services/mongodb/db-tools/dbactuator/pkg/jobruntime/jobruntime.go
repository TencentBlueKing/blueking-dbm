// Package jobruntime 全局操作、全局变量
package jobruntime

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mongodb/db-tools/dbactuator/mylog"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
)

const (
	logDir = "logs/"
)

// JobGenericRuntime job manager
type JobGenericRuntime struct {
	UID            string `json:"uid"`            // 单据ID
	RootID         string `json:"rootId"`         // 流程ID
	NodeID         string `json:"nodeId"`         // 节点ID
	VersionID      string `json:"versionId"`      // 运行版本ID
	PayloadEncoded string `json:"payloadEncoded"` // 参数encoded
	PayloadDecoded string `json:"payloadDecoded"` // 参数decoded
	PayLoadFormat  string `json:"payloadFormat"`  // payload的内容格式,raw/base64
	AtomJobList    string `json:"atomJobList"`    // 原子任务列表,逗号分割
	BaseDir        string `json:"baseDir"`
	// ShareData保存多个atomJob间的中间结果,前后atomJob可通过ShareData通信
	ShareData interface{} `json:"shareData"`
	// PipeContextData保存流程调用,上下文结果
	// PipeContextData=>json.Marshal=>Base64=>标准输出打印<ctx>{Result}</ctx>
	PipeContextData interface{}        `json:"pipeContextData"`
	Logger          *logger.Logger     `json:"-"` // 线程安全日志输出
	ctx             context.Context    `json:"-"`
	cancelFunc      context.CancelFunc `json:"-"`
	Err             error
}

// NewJobGenericRuntime new
func NewJobGenericRuntime(uid, rootID string,
	nodeID, versionID, payload, payloadFormat, atomJobs, baseDir string) (ret *JobGenericRuntime, err error) {
	ret = &JobGenericRuntime{
		UID:            uid,
		RootID:         rootID,
		NodeID:         nodeID,
		VersionID:      versionID,
		PayloadEncoded: payload,
		PayLoadFormat:  payloadFormat,
		AtomJobList:    atomJobs,
		BaseDir:        baseDir,
		ShareData:      nil,
	}

	if ret.PayLoadFormat == consts.PayloadFormatRaw {
		ret.PayloadDecoded = ret.PayloadEncoded
	} else {
		var decodedStr []byte
		decodedStr, err = base64.StdEncoding.DecodeString(ret.PayloadEncoded)
		if err != nil {
			log.Printf("Base64.DecodeString failed,err:%v,encodedString:%s", err, ret.PayloadEncoded)
			os.Exit(0)
		}
		ret.PayloadDecoded = string(decodedStr)
	}
	ret.ctx, ret.cancelFunc = context.WithCancel(context.TODO())
	ret.SetLogger()
	return
}

// SetLogger set logger
func (r *JobGenericRuntime) SetLogger() {
	var err error
	logFile := fmt.Sprintf("redis_actuator_%s_%s.log", r.UID, r.NodeID)
	err = util.MkDirsIfNotExists([]string{logDir})
	if err != nil {
		panic(err)
	}

	logFilePath := filepath.Join(logDir, logFile)
	file, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, os.ModePerm)
	if err != nil {
		panic(err)
	}
	extMap := map[string]string{
		"uid":        r.UID,
		"node_id":    r.NodeID,
		"root_id":    r.RootID,
		"version_id": r.VersionID,
	}
	r.Logger = logger.New(file, true, logger.InfoLevel, extMap)
	r.Logger.Sync()
	mylog.SetDefaultLogger(r.Logger)

	// 修改日志目录owner
	chownCmd := fmt.Sprintf("chown -R %s.%s %s", consts.MysqlAaccount, consts.MysqlGroup, logDir)
	cmd := exec.Command("bash", "-c", chownCmd)
	cmd.Run()
}

// PrintToStdout 打印到标准输出
func (r *JobGenericRuntime) PrintToStdout(format string, args ...interface{}) {
	fmt.Fprintf(os.Stdout, format, args...)
}

// PrintToStderr 打印到标准错误
func (r *JobGenericRuntime) PrintToStderr(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format, args...)
}

// OutputPipeContextData PipeContextData=>json.Marshal=>Base64=>标准输出打印<ctx>{Result}</ctx>
func (r *JobGenericRuntime) OutputPipeContextData() {
	if r.PipeContextData == nil {
		r.Logger.Info("no PipeContextData to output")
		return
	}
	tmpBytes, err := json.Marshal(r.PipeContextData)
	if err != nil {
		r.Err = fmt.Errorf("json.Marshal PipeContextData failed,err:%v", err)
		r.Logger.Error(r.Err.Error())
		return
	}
	// decode函数: base64.StdEncoding.DecodeString
	base64Ret := base64.StdEncoding.EncodeToString(tmpBytes)
	r.PrintToStdout("<ctx>" + base64Ret + "</ctx>")
}

// StartHeartbeat 开始心跳
func (r *JobGenericRuntime) StartHeartbeat(period time.Duration) {
	go func() {
		ticker := time.NewTicker(period)
		defer ticker.Stop()
		var heartbeatTime string
		for {
			select {
			case <-ticker.C:
				heartbeatTime = time.Now().Local().Format(consts.UnixtimeLayout)
				r.PrintToStdout("[" + heartbeatTime + "]heartbeat\n")
			case <-r.ctx.Done():
				r.Logger.Info("stop heartbeat")
				return
			}
		}
	}()
}

// StopHeartbeat 结束心跳
func (r *JobGenericRuntime) StopHeartbeat() {
	r.cancelFunc()
}
