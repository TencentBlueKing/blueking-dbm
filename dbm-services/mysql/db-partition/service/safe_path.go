/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// safeLocalFilename 约束外部参与拼接的文件名：只允许当前目录下的纯文件名，拒绝 ../ 与绝对路径。
func safeLocalFilename(filename string) (string, error) {
	if filename == "" {
		return "", fmt.Errorf("filename is empty")
	}
	if strings.Contains(filename, "..") {
		return "", fmt.Errorf("invalid filename: %s", filename)
	}
	if filepath.IsAbs(filename) {
		return "", fmt.Errorf("absolute path is not allowed: %s", filename)
	}
	base := filepath.Base(filename)
	if base == "." || base == ".." || base != filename {
		return "", fmt.Errorf("invalid filename: %s", filename)
	}
	return base, nil
}

// resolveSafeLocalPath 将合法文件名拼到进程工作目录下，并确认解析后仍落在该目录内。
func resolveSafeLocalPath(filename string) (string, error) {
	name, err := safeLocalFilename(filename)
	if err != nil {
		return "", err
	}
	workDir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	full := filepath.Join(workDir, name)
	rel, err := filepath.Rel(workDir, full)
	if err != nil || rel != name {
		return "", fmt.Errorf("path traversal is not allowed: %s", filename)
	}
	return full, nil
}

// sanitizeFileToken 去掉文件名片段中的路径分隔符，避免拼进分区文件名后产生穿越。
func sanitizeFileToken(s string) string {
	s = strings.ReplaceAll(s, "..", "")
	s = strings.ReplaceAll(s, "/", "_")
	s = strings.ReplaceAll(s, `\`, "_")
	return s
}
