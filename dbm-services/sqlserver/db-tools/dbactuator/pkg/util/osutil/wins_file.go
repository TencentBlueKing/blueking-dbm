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
	"fmt"
	"os"
	"os/exec"

	"dbm-services/common/go-pubpkg/logger"
)

// WINSFile 定义window文件/目录的结构体
type WINSFile struct {
	FileName string
}

// FileExists 判断文件是否存在
func (f *WINSFile) FileExists() (error, bool) {
	_, err := os.Stat(f.FileName)
	if os.IsNotExist(err) {
		return nil, false
	} else if err != nil {
		return err, false
	}
	return nil, true
}

// Create 文件/目录创建
func (f *WINSFile) Create(mode os.FileMode) bool {
	err := os.MkdirAll(f.FileName, mode)
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	return true
}

// SetChmod 设置目录/文件权限
func (f *WINSFile) SetChmod(mode os.FileMode) bool {
	err := os.Chmod(f.FileName, mode)
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	return true
}

// SetChown 设置目录/文件的所属者
func (f *WINSFile) SetChown(user string) bool {
	cmd := exec.Command(
		"powershell",
		"-Command",
		fmt.Sprintf("icacls %s /setowner %s /T /C", f.FileName, user),
	)
	err := cmd.Run()
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	logger.Info(fmt.Sprintf("icacls %s /setowner %s /T /C successfully", f.FileName, user))
	return true
}

// CopyFile copy 文件 到已存在的目录下
func (f *WINSFile) CopyFile(targetPath string) bool {
	cmd := exec.Command(
		"powershell",
		"-Command",
		fmt.Sprintf("Copy-Item -Path '%s' -Destination '%s' -Force ", f.FileName, targetPath),
	)
	err := cmd.Run()
	if err != nil {
		logger.Error(err.Error())
		return false
	}
	logger.Info(fmt.Sprintf("Copy-Item [%s]->[%s] successfully", f.FileName, targetPath))
	return true
}
