/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
)

// MoveBackupFileComp 移动备份文件
type MoveBackupFileComp struct {
	GeneralParam *components.GeneralParam
	Params       *MoveBackupFileParam
	result       []checkResult
}

// MoveBackupFileParam 参数
type MoveBackupFileParam struct {
	FileList   []checkFile `json:"file_list" validate:"required" `
	TargetPath string      `json:"target_path" validate:"required" `
}

type checkFile struct {
	FilePath string `json:"file_path"`
	FileName string `json:"file_name"`
	TaskId   string `json:"task_id"`
}

type checkResult struct {
	FileName  string `json:"file_name"`
	TaskId    string `json:"task_id"`
	IsInLocal bool   `json:"is_in_local"`
}

// Init 初始化
func (m *MoveBackupFileComp) Init() error {
	// 判断目标目录是否存在如果不存在，则创建
	d := osutil.WINSFile{FileName: m.Params.TargetPath}
	err, check := d.FileExists()
	if err != nil {
		return err
	}
	if !check {
		// 不存在则创建
		if !d.Create(0777) {
			return fmt.Errorf("create dir [%s] error", d.FileName)
		}
		logger.Info("create dir [%s] successfully", d.FileName)
	}
	return nil
}

// MoveBackupFile 判断备份文件是否存在，存在则移动
func (m *MoveBackupFileComp) MoveBackupFile() error {
	isErr := false

	for _, file := range m.Params.FileList {
		// 先判断目标目录是否存在文件
		checkfile := filepath.Join(m.Params.TargetPath, file.FileName)
		cf := osutil.WINSFile{FileName: checkfile}
		err, check := cf.FileExists()
		if err != nil {
			logger.Error(err.Error())
			isErr = true
			continue
		}
		if check {
			// 本地存在则强制copy文件
			logger.Info("the backup file [%s] exists in dir [%s]!", file, m.Params.TargetPath)
			// 插入结果
			m.result = append(m.result, checkResult{FileName: checkfile, IsInLocal: true, TaskId: file.TaskId})
			continue
		}
		// 如果不存在则判断原来的位置
		backupfile := filepath.Join(file.FilePath, file.FileName)
		f := osutil.WINSFile{FileName: backupfile}
		err, check = f.FileExists()
		if err != nil {
			logger.Error(err.Error())
			isErr = true
			continue
		}
		if check {
			// 本地存在则强制copy文件
			logger.Info("the backup file [%s] exists, move to this dir [%s]!", backupfile, m.Params.TargetPath)
			if err := f.CopyFile(m.Params.TargetPath); !err {
				// copy 文件失败
				isErr = true
				continue
			}
			// 插入结果
			m.result = append(m.result, checkResult{FileName: backupfile, IsInLocal: true, TaskId: file.TaskId})
			continue

		}
		logger.Info("The backup file [%s] not exists , pass", backupfile)
		m.result = append(m.result, checkResult{FileName: backupfile, IsInLocal: false, TaskId: file.TaskId})
	}
	if isErr {
		return fmt.Errorf("MoveBackupFile failed")
	}
	return nil
}

// MoveBackupFile 输出结果
func (m *MoveBackupFileComp) Output() error {
	err := components.PrintOutputCtx(m.result)
	if err != nil {
		logger.Error("output backup report failed: %s", err.Error())
		return err
	}
	return nil
}
