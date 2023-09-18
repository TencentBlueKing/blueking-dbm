/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package model

// // TbRpStorageItem TODO
// type TbRpStorageItem struct {
// 	DiskId      int       `gorm:"primaryKey;column:disk_id;type:int(11);not null" json:"disk_id"`
// 	BkCloudID   int       `gorm:"column:bk_cloud_id;type:int(11);not null;comment:'云区域 ID'" json:"bk_cloud_id"`
// 	BkHostID    int       `gorm:"index:idx_host_id;column:bk_host_id;type:int(11);not null" json:"bk_host_id"`
// 	MountPoint  string    `gorm:"column:mount_point;type:varchar(20);not null" json:"mount_point"`     // 磁盘挂载点
// 	CloudDiskId string    `gorm:"column:cloud_disk_id;type:varchar(32);not null" json:"cloud_disk_id"` // disk id
// 	DiskType    string    `gorm:"column:disk_type;type:varchar(32);not null" json:"disk_type"`         // disk_type
// 	FileType    string    `gorm:"column:file_type;type:varchar(32);not null" json:"file_type"`         // 文件系统类型
// 	Size        int       `gorm:"column:size;type:int(11);not null;" json:"size"`                      // 磁盘大小
// 	UpdateTime  time.Time `gorm:"column:update_time;type:timestamp" json:"update_time"`                // 最后修改时间
// 	CreateTime  time.Time `gorm:"column:create_time;type:datetime" json:"create_time"`                 // 创建时间
// }

// // TTbRpStorageItemName TODO
// func TTbRpStorageItemName() string {
// 	return "tb_rp_storage_item"
// }
