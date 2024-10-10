/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package mock TODO
package mock

import (
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/db-resource/internal/svr/meta"
)

// GetDbmSpecListMock 获取dbm_spec列表的mock数据
func GetDbmSpecListMock() (dbmSpecList []dbmapi.DbmSpec) {
	return []dbmapi.DbmSpec{
		{
			SpecId:          1,
			SpecName:        "2核4G100G磁盘",
			SpecClusterType: "single",
			SpecMachineType: "single",
			DeviceClass:     []string{},
			Cpu: meta.MeasureRange{
				Min: 2,
				Max: 4,
			},
			Mem: meta.FloatMeasureRange{
				Min: 2000,
				Max: 8000,
			},
			StorageSpecs: []dbmapi.RealDiskSpec{
				{
					MountPoint: "/data",
					DiskType:   "ALL",
					Size:       10,
				},
			},
		},
		{
			SpecId:          2,
			SpecName:        "4核16G500G磁盘",
			SpecClusterType: "single",
			SpecMachineType: "single",
			DeviceClass:     []string{},
			Cpu: meta.MeasureRange{
				Min: 4,
				Max: 8,
			},
			Mem: meta.FloatMeasureRange{
				Min: 6000,
				Max: 16000,
			},

			StorageSpecs: []dbmapi.RealDiskSpec{
				{
					MountPoint: "/data",
					DiskType:   "ALL",
					Size:       100,
				},
			},
		},
		{
			SpecId:          3,
			SpecName:        "16核64G3000G磁盘",
			SpecClusterType: "single",
			SpecMachineType: "single",
			DeviceClass:     []string{},
			Cpu: meta.MeasureRange{
				Min: 16,
				Max: 16,
			},
			Mem: meta.FloatMeasureRange{
				Min: 60000,
				Max: 64000,
			},
			StorageSpecs: []dbmapi.RealDiskSpec{
				{
					MountPoint: "/data",
					DiskType:   "ALL",
					Size:       2900,
				},
			},
		},
	}
}
