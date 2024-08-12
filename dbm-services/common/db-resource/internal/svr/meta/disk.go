/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package meta

import (
	"path"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// MeasureRange cpu spec range

// DiskSpec disk spec param
type DiskSpec struct {
	DiskType   string `json:"disk_type"`
	MinSize    int    `json:"min"`
	MaxSize    int    `json:"max"`
	MountPoint string `json:"mount_point"`
}

// MountPointIsEmpty determine whether the disk parameter is empty
func (d DiskSpec) MountPointIsEmpty() bool {
	return cmutil.IsEmpty(d.MountPoint)
}

// GetEmptyDiskSpec  get empty disk spec info
func GetEmptyDiskSpec(ds []DiskSpec) (dms []DiskSpec) {
	for _, v := range ds {
		if v.MountPointIsEmpty() {
			dms = append(dms, v)
		}
	}
	return
}

// GetDiskSpecMountPoints get disk mount point
func GetDiskSpecMountPoints(ds []DiskSpec) (mountPoints []string) {
	for _, v := range ds {
		logger.Info("disk info %v", v)
		if v.MountPointIsEmpty() {
			continue
		}
		mountPoints = append(mountPoints, path.Clean(v.MountPoint))
	}
	return
}
