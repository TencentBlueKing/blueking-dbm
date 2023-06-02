// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package ext3check

import (
	"io/fs"
	"os"
	"path/filepath"
)

func findHugeFile(dirs []string, threshold int64) (files []string, err error) {
	for _, dir := range dirs {
		err = filepath.WalkDir(
			dir, func(path string, d fs.DirEntry, err error) error {
				if err != nil {
					return filepath.SkipDir
				}

				st, sterr := os.Stat(path)
				if sterr != nil {
					return filepath.SkipDir
				}
				if !d.IsDir() && st.Size() >= threshold {
					files = append(files, path)
				}
				return nil
			},
		)
		if err != nil {
			return nil, err
		}
	}
	return files, nil
}
