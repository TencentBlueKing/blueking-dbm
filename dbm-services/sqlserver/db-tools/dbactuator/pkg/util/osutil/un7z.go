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
	"io"
	"os"
	"path/filepath"

	"github.com/bodgit/sevenzip"
)

// extractFile 根据解压文件留导入指定文件
func extractFile(file *sevenzip.File, destDir string) error {
	// 先判断是否是目录，如果是目录，则走目录创建模式
	info := file.FileInfo()
	if info.IsDir() {
		if err := os.MkdirAll(filepath.Join(destDir, file.Name), 0755); err != nil {
			return err
		}
		return nil
	}

	// 否则走文件创建模式
	rc, err := file.Open()
	if err != nil {
		return err
	}
	defer rc.Close()

	// Extract the file
	// 创建目标文件
	targetFilePath := filepath.Join(destDir, file.Name)
	targetFile, err := os.Create(targetFilePath)
	if err != nil {
		return err
	}
	defer targetFile.Close()

	// 将源文件内容复制到目标文件
	_, err = io.Copy(targetFile, rc)
	if err != nil {
		return err
	}

	return nil
}

// Extract7zArchive 解压7z文件包
func Extract7zArchive(archive string, destDir string) error {
	r, err := sevenzip.OpenReader(archive)
	if err != nil {
		return err
	}
	defer r.Close()

	for _, f := range r.File {
		if err = extractFile(f, destDir); err != nil {
			return err
		}
	}

	return nil
}
