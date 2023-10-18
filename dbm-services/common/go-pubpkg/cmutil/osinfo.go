package cmutil

import (
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
	//UsedPercentReal   float64 `json:"used_percent_real"`
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
