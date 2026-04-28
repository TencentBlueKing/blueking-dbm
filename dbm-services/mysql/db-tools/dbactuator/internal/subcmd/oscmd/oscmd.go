/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package oscmd 操作系统层面通用 OS 操作 (与具体数据库产品无关)
package oscmd

import (
	"github.com/spf13/cobra"

	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/templates"
)

// NewOSCommand os 顶级子命令组
func NewOSCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use:   "os [os operation]",
		Short: "OS Layer Operation Command Line Interface",
		RunE:  subcmd.ValidateSubCommand(),
	}
	groups := templates.CommandGroups{
		{
			Message: "os operation sets",
			Commands: []*cobra.Command{
				NewDiskBenchmarkCommand(),
			},
		},
	}
	groups.Add(cmds)
	return cmds
}
