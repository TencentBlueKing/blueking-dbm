// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ibdstatistic

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/exp/slog"
)

func collectResult(dataDir string) (map[string]map[string]int64, error) {
	result := make(map[string]map[string]int64)

	err := filepath.WalkDir(
		dataDir, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return fs.SkipDir
			}

			if !d.IsDir() && strings.ToLower(filepath.Ext(d.Name())) == ibdExt {
				dir := filepath.Dir(path)
				dbName := filepath.Base(dir)

				var tableName string

				match := partitionPattern.FindStringSubmatch(d.Name())

				if match == nil {
					tableName = strings.TrimSuffix(d.Name(), ibdExt)
				} else {
					tableName = match[1]
				}

				st, err := os.Stat(path)
				if err != nil {
					slog.Error("ibd-statistic collect result", err)
					return err
				}

				if _, ok := result[dbName]; !ok {
					result[dbName] = make(map[string]int64)
				}
				if _, ok := result[dbName][tableName]; !ok {
					result[dbName][tableName] = 0
				}

				result[dbName][tableName] += st.Size()
			}
			return nil
		},
	)

	if err != nil {
		slog.Error("ibd-statistic collect result", err)
		return nil, err
	}

	return result, nil
}
