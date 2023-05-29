/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package codes TODO
package codes

/*
@description: 相关错误码及对应错误类型
@rules:
1. 初始化类的错误码使用					30000-39999
2. 操作系统的错误码使用					40000-49999
3. MySQL、Redis、Mongo实例操作的错误码	50000-59999
*/

const (
	// Unauthorized TODO
	Unauthorized = 10001
	// UnmarshalFailed TODO
	UnmarshalFailed = 10002
	// NotExistMountPoint TODO
	NotExistMountPoint = 20001
	// NotExistUser TODO
	NotExistUser = 20002
	// PermissionDeny TODO
	PermissionDeny = 20003

	// RenderConfigFailed TODO
	RenderConfigFailed = 30001
	// InitParamFailed TODO
	InitParamFailed = 30002
	// InitMySQLDirFailed TODO
	InitMySQLDirFailed = 30003

	// InstallMySQLFailed TODO
	InstallMySQLFailed = 40001
	// ExecuteShellFailed TODO
	ExecuteShellFailed = 40002
	// DecompressPkgFailed TODO
	DecompressPkgFailed = 40003
	// StartMySQLFailed TODO
	StartMySQLFailed = 40004
	// NotAvailableMem TODO
	NotAvailableMem = 40005

	// ImportPrivAndSchemaFailed TODO
	ImportPrivAndSchemaFailed = 50001
)

// ErrorCodes TODO
var ErrorCodes = map[int]string{
	Unauthorized:              "没有进行用户认证",
	UnmarshalFailed:           "反序列化失败",
	NotExistMountPoint:        "没有可用的挂载点",
	NotExistUser:              "用户不存在",
	PermissionDeny:            "权限不足",
	RenderConfigFailed:        "初始化配置失败",
	InitParamFailed:           "初始化参数失败",
	InitMySQLDirFailed:        "初始化MySQL目录失败",
	InstallMySQLFailed:        "安装实例失败",
	ExecuteShellFailed:        "执行Shell脚本失败",
	DecompressPkgFailed:       "解压文件失败",
	StartMySQLFailed:          "启动MySQL失败",
	NotAvailableMem:           "内存不可用",
	ImportPrivAndSchemaFailed: "导入权限和库失败",
}
