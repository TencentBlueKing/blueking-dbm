// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysqlerrlog

import (
	"fmt"
	"strings"

	"github.com/dlclark/regexp2"
)

func init() {
	mysqlCriticalExcludePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`^(?!.*(?:(%s)))`,
			strings.Join(
				[]string{
					"checkpoint",
					"server_errno=2013",
					"sort aborted",
					"restarting transaction",
					"slave SQL thread was killed",
					`\[Warning\]`,
					"Failed to execute mysql_file_stat on file",
					"DEPRECATED",
					"errno: 36",
					"Slave I/O",
					"mysqld_safe mysqld restarted",
					"Failed to open log",
					"Could not open log file",
					"Cannot open.*ib_buffer_pool.*No such file", // 物理备份恢复会产生这个日志
				},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)
}

func mysqlCritical() (string, error) {
	return scanSnapShot(nameMySQLErrCritical, mysqlCriticalExcludePattern)
}
