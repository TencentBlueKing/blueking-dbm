// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

// BackupClient the config of backup_client
type BackupClient struct {
	// EnableBackupClient 是否启用备份上传，默认为 auto，自动根据 is_standby 判断
	// is_standby 为 true 则为 yes，否则为 no
	// 如果手动指定 yes/no，则忽略 is_standby 判断
	EnableBackupClient string `ini:"EnableBackupClient" enum:",auto,yes,no"`
	// FileTag 启用备份时上报文件使用哪个 FileTag
	FileTag     string `ini:"FileTag"`
	StorageType string `ini:"StorageType"`
	DoChecksum  bool   `ini:"DoChecksum"`
	// BackupClientBin 备份客户端路径，默认 /usr/local/backup_client/bin/backup_client
	BackupClientBin string `ini:"BackupClientBin"`
}
