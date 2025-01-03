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
	// LockDDL 备份期间是否允许 ddl, >=5.7 参数有效
	// 默认 false，表示用户的 ddl 优先，备份无效。如果存在 Non-InnoDB 表，在拷贝这些非事务引擎表的时候，会阻塞对 Non-InnoDB dml
	// 为 true 时，备份一开始就发送 lock tables for backup，全程不允许 ddl 和 Non-InnoDB dml
	LockDDL bool `ini:"LockDDL"`
	// DisableSlaveMultiThread 在 slave并行多线程复制，且未开启 gtid 时，是否可临时关闭并行复制。默认值 false
	// 解决 The --slave-info option requires GTID enabled for a multi-threaded slave
	DisableSlaveMultiThread bool `ini:"DisableSlaveMultiThread"`
	// MaxMyisamTables 最大允许的 myisam tables 数量，默认 10，设置 大于 99999 表示不检查。不包含系统库
	// 只有在 master 上进行物理备份数据时，才执行检查
	MaxMyisamTables int `int:"MaxMyisamTables"`
}
