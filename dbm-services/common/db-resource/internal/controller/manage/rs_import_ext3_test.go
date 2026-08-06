/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import (
	"strings"
	"testing"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/svr/bk"
)

func ext3DataDiskMap() map[string]*bk.ShellResCollection {
	return map[string]*bk.ShellResCollection{
		"127.0.0.1": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/data", DiskDetail: bk.DiskDetail{FileType: "ext3"}},
			},
		},
	}
}

func TestMaybeCheckExt3DataDisk_DisabledSkip(t *testing.T) {
	orig := config.AppConfig.CheckExt3DataDisk
	config.AppConfig.CheckExt3DataDisk = false
	t.Cleanup(func() { config.AppConfig.CheckExt3DataDisk = orig })

	if err := maybeCheckExt3DataDisk(ext3DataDiskMap()); err != nil {
		t.Fatalf("disabled check should skip, got: %v", err)
	}
}

func TestMaybeCheckExt3DataDisk_EnabledReject(t *testing.T) {
	orig := config.AppConfig.CheckExt3DataDisk
	config.AppConfig.CheckExt3DataDisk = true
	t.Cleanup(func() { config.AppConfig.CheckExt3DataDisk = orig })

	if err := maybeCheckExt3DataDisk(ext3DataDiskMap()); err == nil {
		t.Fatal("enabled check should reject ext3 data disk")
	}
}

func TestCheckExt3DataDisk_RootExt3Allowed(t *testing.T) {
	diskMap := map[string]*bk.ShellResCollection{
		"127.0.0.1": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/", DiskDetail: bk.DiskDetail{FileType: "ext3"}},
				{MountPoint: "/data", DiskDetail: bk.DiskDetail{FileType: "ext4"}},
			},
		},
	}
	if err := checkExt3DataDisk(diskMap); err != nil {
		t.Fatalf("root ext3 should be ignored, got error: %v", err)
	}
}

func TestCheckExt3DataDisk_DataExt3Rejected(t *testing.T) {
	diskMap := map[string]*bk.ShellResCollection{
		"127.0.0.1": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/", DiskDetail: bk.DiskDetail{FileType: "ext4"}},
				{MountPoint: "/data", DiskDetail: bk.DiskDetail{FileType: "ext3"}},
			},
		},
	}
	err := checkExt3DataDisk(diskMap)
	if err == nil {
		t.Fatal("expected error when /data is ext3")
	}
	msg := err.Error()
	if !strings.Contains(msg, "导入失败") || !strings.Contains(msg, "均未入库") {
		t.Fatalf("error should be explicit import failure message, got: %v", err)
	}
	if !strings.Contains(msg, "127.0.0.1") || !strings.Contains(msg, "/data") {
		t.Fatalf("error should contain ip and mount point, got: %v", err)
	}
}

func TestCheckExt3DataDisk_Data1Data2Ext3Rejected(t *testing.T) {
	diskMap := map[string]*bk.ShellResCollection{
		"127.0.0.1": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/data1", DiskDetail: bk.DiskDetail{FileType: "ext3"}},
				{MountPoint: "/data2", DiskDetail: bk.DiskDetail{FileType: "EXT3"}},
			},
		},
	}
	err := checkExt3DataDisk(diskMap)
	if err == nil {
		t.Fatal("expected error when /data1 or /data2 is ext3")
	}
	msg := err.Error()
	if !strings.Contains(msg, "/data1") || !strings.Contains(msg, "/data2") {
		t.Fatalf("error should list /data1 and /data2, got: %v", err)
	}
}

func TestCheckExt3DataDisk_CaseInsensitive(t *testing.T) {
	diskMap := map[string]*bk.ShellResCollection{
		"127.0.0.2": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/data", DiskDetail: bk.DiskDetail{FileType: "EXT3"}},
			},
		},
	}
	if err := checkExt3DataDisk(diskMap); err == nil {
		t.Fatal("expected error when file_type is EXT3")
	}
}

func TestCheckExt3DataDisk_BatchFailOnOneViolation(t *testing.T) {
	diskMap := map[string]*bk.ShellResCollection{
		"127.0.0.1": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/data", DiskDetail: bk.DiskDetail{FileType: "xfs"}},
			},
		},
		"127.0.0.2": {
			Disk: []bk.DiskInfo{
				{MountPoint: "/data1", DiskDetail: bk.DiskDetail{FileType: "ext3"}},
			},
		},
	}
	err := checkExt3DataDisk(diskMap)
	if err == nil {
		t.Fatal("expected batch error when one host has ext3 data disk")
	}
	if !strings.Contains(err.Error(), "127.0.0.2") {
		t.Fatalf("error should contain violating ip, got: %v", err)
	}
}

func TestCheckExt3DataDisk_EmptyOrNilHostSkipped(t *testing.T) {
	if err := checkExt3DataDisk(nil); err != nil {
		t.Fatalf("nil map should pass, got: %v", err)
	}
	if err := checkExt3DataDisk(map[string]*bk.ShellResCollection{}); err != nil {
		t.Fatalf("empty map should pass, got: %v", err)
	}
	diskMap := map[string]*bk.ShellResCollection{
		"127.0.0.1": nil,
	}
	if err := checkExt3DataDisk(diskMap); err != nil {
		t.Fatalf("nil host shell result should pass, got: %v", err)
	}
}
