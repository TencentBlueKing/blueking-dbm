/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package subcmd TODO
package subcmd

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"

	"github.com/caarlos0/env/v6"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
)

const (
	// CmdBaseExampleStr TODO
	CmdBaseExampleStr = "-u {uid} -n {node_id} -p {base64}"
	// PayloadFormatRaw TODO
	PayloadFormatRaw = "raw"
)

// GBaseOptions TODO
var GBaseOptions *BaseOptions

// GeneralRuntimeParam TODO
var GeneralRuntimeParam *components.GeneralParam

func init() {
	GBaseOptions = &BaseOptions{}
	GeneralRuntimeParam = &components.GeneralParam{}
}

// BaseOptions TODO
/*
	此参数是json字符串的base64编码之后的字符串
*/
type BaseOptions struct {
	Uid           string
	RootId        string
	NodeId        string
	VersionId     string
	Payload       string
	PayloadFormat string
	RollBack      bool
	Helper        bool
	// 是否为外部版本
	// on ON
	External string
}

// IsExternal 是否编译成外部版本
func (b *BaseOptions) IsExternal() bool {
	return strings.ToUpper(b.External) == "ON"
}

const (
	// StepStateDefault TODO
	StepStateDefault = "default"
	// StepStateRunning TODO
	StepStateRunning = "running"
	// StepStateSucc TODO
	StepStateSucc = "success"
	// StepStateSkip TODO
	StepStateSkip = "skipped" // 用户主动跳过该 step
	// StepStateStop TODO
	StepStateStop = "stopped" // 用户主动暂停，特殊形式的 failed
	// StepStateFail TODO
	StepStateFail = "failed"
)

// StepFunc TODO
type StepFunc struct {
	FunName      string
	Func         func() error
	State        string
	FuncRetry    func() error
	FuncRollback func() error
	FuncStop     func() error
	Retries      int
}

// Steps TODO
type Steps []StepFunc

// Run TODO
func (s Steps) Run() (err error) {
	for idx, step := range s {
		logMessage := fmt.Sprintf("step <%d>, ready start run [%s]", idx, step.FunName)
		logger.Info(logMessage)
		if err = step.Func(); err != nil {
			logger.Error("step<%d>: %s失败 , 错误: %s", idx, step.FunName, err)
			// @todo
			// 顺便输出接下来还有哪些 step 未允许
			return err
		}
		logger.Info("step <%d>, start run [%s] successfully", idx, step.FunName)
	}
	return nil
}

// DeserializeNonStandard TODO
/*
	反序列化payload,并校验参数
	ps: 参数校验 from golang validate v10
*/
func (b *BaseOptions) DeserializeNonStandard(s interface{}) (err error) {
	var bp []byte
	if b.PayloadFormat == PayloadFormatRaw {
		bp = []byte(b.Payload)
	} else {
		// logger.Info("DeserializeAndValidate payload body: %s", b.Payload)
		bp, err = base64.StdEncoding.DecodeString(b.Payload)
		if err != nil {
			return err
		}
	}

	// 如果 s 里面的 sub struct 是 pointer，要初始化后再传进来才能解析到环境变量
	if err := env.Parse(s); err != nil {
		logger.Warn("env parse error, ignore environment variables for payload:%s", err.Error())
		// env: expected a pointer to a Struct
	}
	if err = json.Unmarshal(bp, s); err != nil {
		logger.Error("json.Unmarshal failed, %v", s, err)
		return
	}
	if err = validate.GoValidateStruct(s, false, true); err != nil {
		logger.Error("validate struct failed, %v", s, err)
		return
	}
	return nil
}

// Deserialize TODO
func Deserialize(s interface{}) (p *BaseOptions, err error) {
	var bp []byte
	if err = GBaseOptions.Validate(); err != nil {
		return nil, err
	}
	if GBaseOptions.PayloadFormat == PayloadFormatRaw {
		bp = []byte(GBaseOptions.Payload)
	} else {
		// logger.Debug("Deserialize payload body: %s", GBaseOptions.Payload)
		bp, err = base64.StdEncoding.DecodeString(GBaseOptions.Payload)
		if err != nil {
			return nil, err
		}
	}
	if err := env.Parse(s); err != nil {
		logger.Warn("env parse error, ignore environment variables for payload:%s", err.Error())
	}
	g := components.RuntimeAccountParam{}
	if err := env.Parse(&g); err != nil {
		logger.Warn("env parse error, ignore environment variables for payload:%s", err.Error())
	}
	// logger.Info("Account from env: %+v", g)
	bip := components.BaseInputParam{
		ExtendParam:  s,
		GeneralParam: &components.GeneralParam{RuntimeAccountParam: g},
	}
	defer logger.Info("payload parsed: %+v", bip)
	if err = json.Unmarshal(bp, &bip); err != nil {
		logger.Error("json.Unmarshal failed, %v", s, err)
		err = errors.WithMessage(err, "参数解析错误")
		return nil, err
	}
	if err = validate.GoValidateStruct(bip, false, true); err != nil {
		logger.Error("validate struct failed, %v", s, err)
		err = errors.WithMessage(err, "参数输入错误")
		return nil, err
	}
	GeneralRuntimeParam = bip.GeneralParam
	return GBaseOptions, nil
}

// Deserialize 反序列化payload,并校验参数
//
//	ps: 参数校验 from golang validate v10
func (b *BaseOptions) Deserialize(s interface{}) (err error) {
	var bp []byte
	if err = b.Validate(); err != nil {
		return err
	}
	if b.PayloadFormat == PayloadFormatRaw {
		bp = []byte(b.Payload)
	} else {
		//	logger.Info("Deserialize payload body: %s", b.Payload)
		bp, err = base64.StdEncoding.DecodeString(b.Payload)
		if err != nil {
			return err
		}
	}
	if err := env.Parse(s); err != nil {
		logger.Warn("env parse error, ignore environment variables for payload:%s", err.Error())
	}
	g := components.RuntimeAccountParam{}
	if err := env.Parse(&g); err != nil {
		logger.Warn("env parse error, ignore environment variables for payload:%s", err.Error())
	}
	bip := components.BaseInputParam{
		ExtendParam:  s,
		GeneralParam: &components.GeneralParam{RuntimeAccountParam: g},
	}
	if err = json.Unmarshal(bp, &bip); err != nil {
		logger.Error("json.Unmarshal failed, %v", s, err)
		err = errors.WithMessage(err, "参数解析错误")
		return err
	}
	s = bip.ExtendParam
	if err = validate.GoValidateStruct(bip, false, true); err != nil {
		logger.Error("validate struct failed, %v", s, err)
		err = errors.WithMessage(err, "参数输入错误")
		return err
	}
	GeneralRuntimeParam = bip.GeneralParam
	return nil
}

// DeserializeSimple 简单 payload 不需要 {"extend":{body}}，直接传入 body
func (b *BaseOptions) DeserializeSimple(s interface{}) (err error) {
	var body []byte
	if b.PayloadFormat == PayloadFormatRaw {
		body = []byte(b.Payload)
	} else {
		logger.Info("DeserializeSimple payload body: %s", b.Payload)
		body, err = base64.StdEncoding.DecodeString(b.Payload)
		if err != nil {
			return err
		}
	}

	// 如果 s 里面的 sub struct 是 pointer，要初始化后再传进来才能解析到环境变量
	if err := env.Parse(s); err != nil {
		logger.Warn("env parse error, ignore environment variables for payload:%s", err.Error())
	}

	defer logger.Info("payload parsed: %+v", s)
	if err = json.Unmarshal(body, &s); err != nil {
		logger.Error("json.Unmarshal failed, %v", s, err)
		err = errors.WithMessage(err, "参数解析错误")
		return
	}
	if err = validate.GoValidateStruct(s, false, true); err != nil {
		logger.Error("validate struct failed, %v", s, err)
		err = errors.WithMessage(err, "参数输入错误")
		return
	}
	return nil
}

// Validate TODO
func (b *BaseOptions) Validate() (err error) {
	if len(b.Payload) == 0 {
		return fmt.Errorf("payload need input")
	}
	return nil
}

// OutputCtx TODO
//
//	@receiver b
func (b *BaseOptions) OutputCtx(ctx string) {
	fmt.Printf("<ctx>%s</ctx>", ctx)
}

// SetLogger will mkdir logs/
func SetLogger(cmd *cobra.Command, opt *BaseOptions) {
	var file *os.File
	var err error
	var format = true

	executable, _ := os.Executable()
	// executeName := filepath.Base(executable)
	executeDir := filepath.Dir(executable)
	if err = os.Chdir(executeDir); err != nil {
		os.Stderr.WriteString(err.Error())
		os.Exit(1)
	}

	mode := os.Getenv("MODE")
	lgn := ""
	if cmd != nil && cmd.Parent() != nil {
		lgn = fmt.Sprintf("%s-%s", cmd.Parent().Name(), cmd.Name())
	}
	switch mode {
	case "dev":
		file = os.Stdout
		format = false
	default:
		logFileDir := filepath.Join(executeDir, "logs")
		_ = os.MkdirAll(logFileDir, 0755)
		fileName := filepath.Join(logFileDir, fmt.Sprintf("actuator_%s_%s_%s.log", opt.Uid, lgn, opt.NodeId))
		file, err = os.OpenFile(fileName, os.O_CREATE|os.O_APPEND|os.O_WRONLY, os.ModePerm)
		if err != nil {
			os.Stderr.WriteString(err.Error())
			os.Exit(1)
		}
	}

	extMap := map[string]string{
		"uid":        opt.Uid,
		"node_id":    opt.NodeId,
		"root_id":    opt.RootId,
		"version_id": opt.VersionId,
	}
	l := logger.New(file, format, logger.InfoLevel, extMap)
	logger.ResetDefault(l)
	defer logger.Sync()
}

// ValidateSubCommand TODO
func ValidateSubCommand() func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		if len(args) <= 0 {
			return fmt.Errorf(
				"You must specify the type of Operation Describe. %s\n",
				suggestAPIResources(cmd.Parent().Name()),
			)
		}
		curName := args[0]
		var subCommands []string
		for _, c := range cmd.Commands() {
			subCommands = append(subCommands, c.Name())
		}
		if len(subCommands) <= 0 {
			return nil
		}
		if !util.StringsHas(subCommands, curName) {
			return fmt.Errorf("Unknown subcommand %s\n", curName)
		}
		return nil
	}
}

// PrintSubCommandHelper 返回是否成功打印 helper
// 如果打印，同时运行下 runHelp
func PrintSubCommandHelper(cmd *cobra.Command, opt *BaseOptions) bool {
	if opt.Helper {
		if cmd.Parent().Name() == "dbactuator" {
			fmt.Println("--helper need sub-command to show payload parameter")
			os.Exit(1)
		}
		if cmd.Name() != "" {
			subcmdPath := fmt.Sprintf("%s %s", cmd.Parent().Name(), cmd.Name())
			if err := GetPathDefinitionHelper(subcmdPath); err != nil {
				fmt.Println(err)
				os.Exit(1)
			}
			return true
		}
		fmt.Println("--example need sub-command")
	}
	return false
}

// suggestAPIResources returns a suggestion to use the "api-resources" command
// to retrieve a supported list of resources
func suggestAPIResources(parent string) string {
	return templates.LongDesc(
		fmt.Sprintf(
			"Use \"%s {Operation Type}\" for a complete list of supported resources.",
			parent,
		),
	)
}
