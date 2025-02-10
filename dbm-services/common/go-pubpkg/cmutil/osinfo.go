/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmutil

import (
	"path/filepath"
	"regexp"
	"strings"

	"github.com/pkg/errors"
	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

// MemoryInfo return memory info
type MemoryInfo struct {
	Total     uint64 `json:"total"`
	Free      uint64 `json:"free"`
	Shared    uint64 `json:"shared"`
	Buffer    uint64 `json:"buffer"`
	SwapTotal uint64 `json:"swap_total"`
	SwapFree  uint64 `json:"swap_free"`
}

// GetMemoryInfo Get Memory Info
func GetMemoryInfo() (*MemoryInfo, error) {
	memStat, err := mem.VirtualMemory()
	if err != nil {
		return nil, errors.Wrap(err, "fail to get memory")
	}
	memInfo := MemoryInfo{
		Total:     memStat.Total,
		Free:      memStat.Free,
		Shared:    memStat.Shared,
		Buffer:    memStat.Buffers,
		SwapTotal: memStat.SwapTotal,
		SwapFree:  memStat.SwapFree,
	}
	return &memInfo, nil
}

// DiskPartInfo return disk partition info
type DiskPartInfo struct {
	Device     string `json:"device"`
	Mountpoint string `json:"mountpoint"`
	Fstype     string `json:"fstype"`

	Path  string `json:"path"`
	Total uint64 `json:"total"`
	// Free 真实可用量，不包括 fs reserved 部分，相当于 available
	Free uint64 `json:"free"`
	// Used 真实使用量, 不包含 fs reserved
	Used uint64 `json:"used"`
	// UsedTotal 总使用量，Used + Reserved
	UsedTotal uint64 `json:"used_total"`
	// Reserved = Total - Free - Used
	Reserved uint64 `json:"reserved"`
	// UsedPercent 在os层面看到的磁盘利用率，包括 reserved (Used + Reserved) / Total
	UsedPercent float64 `json:"used_percent"`
	// UsedPercentReal Used / (Total - Reserved), stat.UsedPercent
	// UsedPercentReal   float64 `json:"used_percent_real"`
	InodesTotal       uint64  `json:"inodes_total"`
	InodesUsed        uint64  `json:"inodes_used"`
	InodesUsedPercent float64 `json:"inodes_used_percent"`
}

// GetDiskPartInfo 获取目录的信息
// 空间使用，挂载设备。比如 path = /data/dbbak/123，获取的是目录对应的挂载设备的信息
func GetDiskPartInfo(path string, checkDevice bool) (*DiskPartInfo, error) {
	info := DiskPartInfo{Path: path}
	if checkDevice {
		// 获取目录对应的挂载点
		osStatArgs := []string{"--format", "%m", path}
		if stdout, stderr, err := ExecCommand(false, "", "stat", osStatArgs...); err != nil {
			return nil, errors.Wrapf(err, "stat to get path mount %s", stderr)
		} else {
			info.Mountpoint = strings.TrimSpace(stdout)
		}
		// get more mountpoint device info
		partInfo, err := disk.Partitions(false)
		if err != nil {
			return nil, errors.Wrap(err, "get disk partitions")
		}
		for _, p := range partInfo {
			if p.Mountpoint == info.Mountpoint {
				info.Device = p.Device
				info.Fstype = p.Fstype
			}
		}
		if info.Device == "" {
			// CentOS6.2 stat --format has no %m
			return nil, errors.Errorf("fail to get device(mounted %s) for path %s", info.Mountpoint, info.Path)
		}
		if info.Mountpoint != info.Path {
			// use du to get directory used size?
		}
	}

	// 获取挂载点的分区使用信息
	pathInfo, err := disk.Usage(path)
	if err != nil {
		return nil, errors.Wrap(err, "get disk info")
	}
	info.Total = pathInfo.Total
	info.Free = pathInfo.Free
	info.Used = pathInfo.Used
	info.Reserved = pathInfo.Total - pathInfo.Used - pathInfo.Free
	info.UsedTotal = pathInfo.Total - pathInfo.Free                  // = pathInfo.Used + info.Reserved
	info.UsedPercent = float64(info.UsedTotal) / float64(info.Total) // not pathInfo.UsedPercent
	info.InodesTotal = pathInfo.InodesTotal
	info.InodesUsed = pathInfo.InodesUsed
	info.InodesUsedPercent = float64(100.0*pathInfo.InodesUsed) / float64(pathInfo.InodesTotal)
	return &info, nil
}

// CPUInfo return cpu processor info
type CPUInfo struct {
	CoresLogical int `json:"cores_logical"`
}

// GetCPUInfo Get CPU Info
func GetCPUInfo() (*CPUInfo, error) {
	cores, err := cpu.Counts(true)
	if err != nil {
		return nil, errors.Wrap(err, "cpu.Counts")
	}
	return &CPUInfo{CoresLogical: cores}, nil
}

// GetTopLevelDir returns the top-level directory of a given path.
func GetTopLevelDir(path string) (string, error) {
	realPath, err := filepath.EvalSymlinks(path) // resolve symlinks to their real paths
	if err != nil {
		return "", err
	}
	realPath = filepath.Clean(realPath)
	// Extract the top-level directory
	parentDir := filepath.Dir(realPath)
	for parentDir != "/" && parentDir != "." {
		realPath = parentDir
		parentDir = filepath.Dir(realPath)
	}
	return realPath, nil
}

// IsSameTopLevelDir 判断dir1 和  dir2是否是同一个顶级目录
// 1. dir1 dir2 必须是存在的
// 2. 比如 dir1 = /home/abc, dir2 = /home/abc/def,顶级目录都是 /home,所以返回true
func IsSameTopLevelDir(dir1, dir2 string) (bool, error) {
	topDir1, err1 := GetTopLevelDir(dir1)
	if err1 != nil {
		return false, err1
	}
	topDir2, err2 := GetTopLevelDir(dir2)
	if err2 != nil {
		return false, err2
	}
	return topDir1 == topDir2, nil
}

// GetGlibcVersion get os glibc version using ExeCommand("ldd --version |grep libc")
func GetGlibcVersion() (string, error) {
	outStr, errStr, err := ExecCommand(false, "",
		"/usr/bin/ldd", "--version", "|", "grep", "libc")
	if err != nil {
		return "", errors.WithMessage(err, errStr)
	}
	verMatch := regexp.MustCompile(`ldd \(.*\) (\d+\.\d+)`)
	ms := verMatch.FindStringSubmatch(outStr)
	if len(ms) == 2 {
		return ms[1], nil
	}
	return "", errors.New("ldd --version | grep glibc fail to get glibc version")
}
