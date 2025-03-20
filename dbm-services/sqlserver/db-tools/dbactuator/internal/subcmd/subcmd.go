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
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/templates"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/validate"

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
	Uid               string
	RootId            string
	NodeId            string
	VersionId         string
	GeneralPayload    string
	ExtendPayload     string
	ExtendPayloadFile string
	RollBackPayload   string
	RollBack          bool
	Helper            bool
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

// 根据payload_file获取payload内容
func (b *BaseOptions) GetExtendPayloadFormFile() error {
	if b.ExtendPayloadFile == "" {
		return fmt.Errorf("ExtendPayloadFile文件为空")
	}
	content, err := os.ReadFile(b.ExtendPayloadFile)
	if err != nil {
		return fmt.Errorf("读取extend_Payload文件失败: %v\n", err)

	}
	b.ExtendPayload = string(content)
	return nil
}

// DeserializeAndValidate TODO
/*
	反序列化回滚的payload,并校验参数
	ps: 参数校验 from golang validate v10
*/
func (b *BaseOptions) RollBackDeserializeAndValidate(s interface{}) (err error) {
	var bp []byte
	if len(b.RollBackPayload) == 0 {
		// 可以接受为空
		logger.Info("RollBackPayload is null")
		return nil
	}
	bp, err = base64.StdEncoding.DecodeString(b.RollBackPayload)
	if err != nil {
		return err
	}

	// logger.Info("payload received: %s", bp)
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
/*
	{
		"general":{} //
		"extend":{}  // 实际参数
	}
	反序列化payload,并校验参数
	ps: 参数校验 from golang validate v10
*/
func (b *BaseOptions) Deserialize(s interface{}) (err error) {
	var extendBp []byte
	var generalBp []byte

	bip := components.BaseInputParam{
		ExtendParam:  s,
		GeneralParam: &components.GeneralParam{RuntimeAccountParam: components.RuntimeAccountParam{}},
	}

	// 解析ExtendPayload
	if err = b.GetExtendPayloadFormFile(); err != nil {
		return err
	}

	extendBp, err = base64.StdEncoding.DecodeString(b.ExtendPayload)
	if err != nil {
		fmt.Println("ExtendPayload err")
		return err
	}
	if err = json.Unmarshal(extendBp, &bip); err != nil {
		logger.Error("[ExtendPayload] json.Unmarshal failed, %v", s, err)
		err = errors.WithMessage(err, "参数解析错误")
		return
	}

	// 解析GeneralPayload
	generalBp, err = base64.StdEncoding.DecodeString(b.GeneralPayload)
	if err != nil {
		fmt.Println("GeneralPayload err")
		return err
	}
	if err = json.Unmarshal(generalBp, &bip); err != nil {
		logger.Error("[GeneralPayload] json.Unmarshal failed, %v", s, err)
		err = errors.WithMessage(err, "参数解析错误")
		return
	}

	defer logger.Info("payload parsed: %+v", bip)
	// logger.Info("params after unmarshal %+v", bip)
	if err = validate.GoValidateStruct(bip, false, true); err != nil {
		logger.Error("validate struct failed, %v", s, err)
		err = errors.WithMessage(err, "参数输入错误")
		return
	}
	GeneralRuntimeParam = bip.GeneralParam

	return nil
}

// Validate TODO
func (b BaseOptions) Validate() (err error) {
	if len(b.ExtendPayloadFile) == 0 {
		return fmt.Errorf("ExtendPayloadFile need input")
	}
	if len(b.GeneralPayload) == 0 {
		return fmt.Errorf("GeneralPayload need input")
	}
	return nil
}

// OutputCtx TODO
//
//	@receiver b
func (b BaseOptions) OutputCtx(ctx string) {
	fmt.Printf("<ctx>%s</ctx>", ctx)
}

// SetLogger will mkdir logs/
func SetLogger(cmd *cobra.Command, opt *BaseOptions) {
	var file *os.File
	var err error
	var format = true

	// executable, _ := os.Executable()
	// executeName := filepath.Base(executable)
	// executeDir := filepath.Dir(executable)
	executeDir, _ := os.Getwd()
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
				SuggestAPIResources(cmd.Parent().Name()),
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
			} else {
				return true
			}
		} else {
			fmt.Println("--example need sub-command")
		}
	}
	return false
}

// SuggestAPIResources returns a suggestion to use the "api-resources" command
// to retrieve a supported list of resources
func SuggestAPIResources(parent string) string {
	return templates.LongDesc(
		fmt.Sprintf(
			"Use \"%s {Operation Type}\" for a complete list of supported resources.",
			parent,
		),
	)
}

// PKCS5Padding TODO
func PKCS5Padding(ciphertext []byte, blockSize int) []byte {
	padding := blockSize - len(ciphertext)%blockSize
	padtext := bytes.Repeat([]byte{byte(padding)}, padding)
	return append(ciphertext, padtext...)
}

// PKCS5UnPadding TODO
func PKCS5UnPadding(origData []byte) []byte {
	length := len(origData)
	unpadding := int(origData[length-1])
	return origData[:(length - unpadding)]
}

// AesEncrypt TODO
//
//	增加加密函数，加密的key必须是16,24,32位长
func AesEncrypt(origData, key []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	blockSize := block.BlockSize()
	origData = PKCS5Padding(origData, blockSize)
	fmt.Println(origData)
	blockMode := cipher.NewCBCEncrypter(block, key[:blockSize])
	crypted := make([]byte, len(origData))
	blockMode.CryptBlocks(crypted, origData)
	return crypted, nil
}

// AesDecrypt 增加解密函数
func AesDecrypt(crypted string, key []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	data, err1 := base64.StdEncoding.DecodeString(crypted)
	if err1 != nil {
		return nil, err1
	}
	blockSize := block.BlockSize()
	blockMode := cipher.NewCBCDecrypter(block, key[:blockSize])
	origData := make([]byte, len(data))
	blockMode.CryptBlocks(origData, data)
	origData = PKCS5UnPadding(origData)
	return origData, nil
}
