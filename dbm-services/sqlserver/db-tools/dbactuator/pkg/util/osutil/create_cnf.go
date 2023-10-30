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
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// CreateInstallConf 根据传入的配置json,以及配置文件位置，本地生成配置文件
func CreateInstallConf(conf []byte, confFile string, version string) error {
	var m map[string]interface{}
	err := json.Unmarshal(conf, &m)
	if err != nil {
		return err
	}

	file, err := os.Create(confFile)
	if err != nil {
		return err
	}
	defer file.Close()

	// 这里写入配置文件的类别，不同版本类别名称都不一样
	title := "[OPTIONS]"
	if strings.Contains(version, "2008") {
		title = "[SQLSERVER2008]"
	}
	file.WriteString(title)

	for key, value := range m {
		line := fmt.Sprintf("%s=\"%v\"\n", key, value)
		_, err = file.WriteString(line)
		if err != nil {
			return err
		}
	}
	return nil
}
