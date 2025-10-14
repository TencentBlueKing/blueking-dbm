// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmutil

import (
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// DirDuSize get directory size like du
// 单位 bytes
func DirDuSize(path string) (int64, error) {
	var totalSize int64
	err := filepath.Walk(path, func(_ string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			totalSize += info.Size()
		}
		return err
	})
	return totalSize, err
}

// DirFileStatsList get directory file list and size
// 升序
func DirFileStatsList(path string) (int64, []os.FileInfo, error) {
	var totalSize int64
	var fileInfoList []os.FileInfo
	err := filepath.Walk(path, func(_ string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			totalSize += info.Size()
			fileInfoList = append(fileInfoList, info)
		}
		return err
	})
	sort.Slice(fileInfoList, func(i, j int) bool {
		seqI := cast.ToInt(strings.LastIndex(fileInfoList[i].Name(), ".")) + 1
		seqJ := cast.ToInt(strings.LastIndex(fileInfoList[j].Name(), ".")) + 1
		return seqI < seqJ
	})
	return totalSize, fileInfoList, err
}

// DoDuCmd 执行du命令
// du xxx -sm 单位 MB
func DoDuCmd(pathList []string) (ret float64, err error) {
	if len(pathList) == 0 {
		ret = 0
		return
	}

	args := []string{"-sm"}
	args = append(args, pathList...)
	cmd := exec.Command("du", args...)
	out, err := cmd.Output()
	if err != nil {
		return 0, errors.Errorf("fail to get size %v: %v", pathList, err.Error())
	}
	buff := string(out)
	lines := strings.Split(buff, "\n")
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		kv := strings.Fields(line)
		if value, err := strconv.ParseFloat(kv[0], 64); err == nil {
			ret += value
		} else {
			return 0, errors.Errorf("fail to parse size %s: %v", kv[0], err.Error())
		}
	}
	return
}
