// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

// PhysicalBackup the config of physical backup
type PhysicalBackup struct {
	Threads      int    `ini:"Threads"`  // parallel to copy files
	Throttle     int    `ini:"Throttle"` // limits the number of chunks copied per second. The chunk size is 10 MB, 0 means no limit
	DefaultsFile string `ini:"DefaultsFile" validate:"required,file"`
	ExtraOpt     string `ini:"ExtraOpt"` // other xtrabackup options string to be appended
	// DisableSlaveMultiThread 在 slave并行多线程复制，且未开启 gtid 时，是否可临时关闭并行复制。默认值 false
	// 解决 The --slave-info option requires GTID enabled for a multi-threaded slave
	DisableSlaveMultiThread bool `ini:"DisableSlaveMultiThread"`
}

// PhysicalLoad the config of physical loading
type PhysicalLoad struct {
	MysqlLoadDir  string `ini:"MysqlLoadDir" validate:"required"`
	Threads       int    `ini:"Threads"`
	CopyBack      bool   `ini:"CopyBack"` // use copy-back or move-back
	IndexFilePath string `ini:"IndexFilePath" validate:"required,file"`
	DefaultsFile  string `ini:"DefaultsFile" validate:"required"`
	ExtraOpt      string `ini:"ExtraOpt"` // other xtrabackup recover options string to be appended
}
