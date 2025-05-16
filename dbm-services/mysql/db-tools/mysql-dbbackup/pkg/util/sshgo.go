/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

import (
	"strings"

	sshgo "github.com/melbahja/goph"
	"github.com/spf13/cast"
)

// CheckRemoteProcessRunning check remote process running via ssh
func CheckRemoteProcessRunning(sshClient *sshgo.Client, egrepProcess string) int {
	out, err := sshClient.Run("ps -ef | grep -E '" + egrepProcess + "' | grep -v grep | wc -l")
	if err != nil {
		return 0
	}
	cnt := cast.ToInt(strings.TrimSpace(string(out)))
	return cnt
}
