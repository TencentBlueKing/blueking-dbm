// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"dbm-services/common/reverseapi/define"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"

	meta "dbm-services/common/reverseapi/define/mysql"
)

// GetSelfInfo 获取本实例信息
func GetSelfInfo(host string, port int) (sii *meta.StorageInstanceInfo, err error) {
	filePath := filepath.Join(
		define.DefaultCommonConfigDir,
		define.DefaultInstanceInfoFileName,
	)
	f, err := os.OpenFile(filePath, os.O_RDONLY, os.ModePerm)
	if err != nil {
		return nil, err
	}

	b, err := io.ReadAll(f)
	if err != nil {
		return nil, err
	}

	var siis []meta.StorageInstanceInfo
	err = json.Unmarshal(b, &siis)
	if err != nil {
		return nil, err
	}

	idx := slices.IndexFunc(siis, func(ele meta.StorageInstanceInfo) bool {
		return ele.Ip == host && ele.Port == port
	})
	if idx < 0 {
		return nil, fmt.Errorf("can't find %s:%d in %v", host, port, siis)
	}
	return &siis[idx], nil
}
