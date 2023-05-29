/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package osutil

import (
	"bytes"
	"os"
	"os/exec"
	"strings"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
)

// FileOutputCmd 封装exec.Command，用于执行命令并输出到文件的场景，支持自动将输出文件上传到文件服务器(尽可能上传，如果上传失败则返回原文件)
type FileOutputCmd struct {
	exec.Cmd
	StdOutFile string
	StdErrFile string

	stdOutFile         *os.File
	stdErrFile         *os.File
	stdOutDownloadLink string
	stdErrDownloadLink string
}

// GetStdOutDownloadLink TODO
func (c *FileOutputCmd) GetStdOutDownloadLink() string {
	return c.stdOutDownloadLink
}

// GetStdErrDownloadLink TODO
func (c *FileOutputCmd) GetStdErrDownloadLink() string {
	return c.stdErrDownloadLink
}

func (c *FileOutputCmd) initOutputFile() error {
	if c.StdErrFile == "" {
		c.StdErrFile = c.StdOutFile
	}
	if c.StdOutFile != "" {
		stdOutFile, err := os.OpenFile(c.StdOutFile, os.O_CREATE|os.O_WRONLY, os.ModePerm)
		if err != nil {
			return errors.Wrapf(err, "open std out log file %s failed", c.StdOutFile)
		}
		c.stdOutFile = stdOutFile
		c.Cmd.Stdout = stdOutFile
	}

	if c.StdOutFile == c.StdErrFile {
		c.stdErrFile = nil
		c.Cmd.Stderr = c.stdOutFile
		return nil
	}

	if c.StdErrFile != "" {
		stdErrFile, err := os.OpenFile(c.StdErrFile, os.O_CREATE|os.O_WRONLY, os.ModePerm)
		if err != nil {
			return errors.Wrapf(err, "open std err log file %s failed", c.StdErrFile)
		}
		c.stdErrFile = stdErrFile
		c.Cmd.Stderr = stdErrFile
	}
	return nil
}

func (c *FileOutputCmd) closeOutputFile() {
	if c.stdOutFile != nil {
		if err := c.stdOutFile.Close(); err != nil {
			logger.Warn("close %s failed, err:%s", c.StdOutFile, err.Error())
		}
	}
	if c.stdErrFile != nil {
		if err := c.stdErrFile.Close(); err != nil {
			logger.Warn("close %s failed, err:%s", c.StdErrFile, err.Error())
		}
	}
	// UploadPath?
}

// Run TODO
func (c *FileOutputCmd) Run() error {
	if err := c.initOutputFile(); err != nil {
		return err
	}

	defer func() {
		c.closeOutputFile()
	}()

	return c.Cmd.Run()
}

// Start TODO
func (c *FileOutputCmd) Start() error {
	if err := c.initOutputFile(); err != nil {
		return err
	}

	return c.Cmd.Start()
}

// Wait TODO
func (c *FileOutputCmd) Wait() error {
	defer func() {
		c.closeOutputFile()
	}()

	return c.Cmd.Wait()
}

// CleanExecOutput TODO
func CleanExecOutput(s string) string {
	return strings.ReplaceAll(strings.TrimSpace(s), "\n", "")
}

// StandardPowerShellCommand TODO
func StandardPowerShellCommand(param string) (stdoutStr string, err error) {
	var stdout, stderr bytes.Buffer
	cmd := exec.Command("powershell", "-Command", param)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	if err != nil {
		return stdout.String(), errors.WithMessage(err, stderr.String())
	}
	return stdout.String(), nil
}

// StandardPowerShellCommands TODO
func StandardPowerShellCommands(params []string) (stdoutStr string, err error) {
	for _, param := range params {
		ret, err := StandardPowerShellCommand(param)
		if err != nil {
			return ret, err
		}
	}
	return "", nil
}
