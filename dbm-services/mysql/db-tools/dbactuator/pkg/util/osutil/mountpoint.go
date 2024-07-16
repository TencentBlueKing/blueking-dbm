package osutil

import (
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"

	sigar "github.com/cloudfoundry/gosigar"
	"github.com/jaypipes/ghw"
	"github.com/jaypipes/ghw/pkg/block"
)

// IsDataDirOk TODO
func IsDataDirOk(filepath string) bool {
	mountPaths := GetMountPathInfo("")
	if m, ok := mountPaths[filepath]; ok {
		// 如果 /data 在根分区，并且根分区大于 60G，通过
		if m.AvailSizeMB > 6144 {
			return true
		} else {
			// not large enough
			return false
		}
	}
	// no mount point found
	return false
}

// MountPath TODO
type MountPath struct {
	Filesystem string
	// Type
	FileSystemType string
	TotalSizeMB    int64
	// Used
	UsedSizeMB int64
	// Available
	AvailSizeMB int64
	// UsePct Use%
	UsePct int
	// Path Mounted on
	Path string
}

// ParseDfOutput format like
// Filesystem     Type 1M-blocks  Used Available Use% Mounted on
// /dev/vda1      ext4    100669  9295     87161  10% /
func ParseDfOutput(rawOutput string) map[string]*MountPath {
	mountPaths := make(map[string]*MountPath)
	lines := strings.Split(rawOutput, "\n")
	for i, line := range lines {
		// skip headers
		if i == 0 {
			continue
		}

		fields := strings.Fields(line)
		if len(fields) == 0 || len(fields) != 7 {
			continue
		}
		mountPath := &MountPath{
			Path:           fields[6],
			Filesystem:     fields[0],
			FileSystemType: fields[1],
		}
		mountPath.TotalSizeMB, _ = strconv.ParseInt(fields[2], 10, 64)
		mountPath.UsedSizeMB, _ = strconv.ParseInt(fields[3], 10, 64)
		mountPath.AvailSizeMB, _ = strconv.ParseInt(fields[4], 10, 64)
		mountPath.UsePct, _ = strconv.Atoi(strings.TrimSuffix(fields[5], "%"))

		mountPaths[fields[6]] = mountPath
	}
	return mountPaths
}

// GetMountPathInfo TODO
func GetMountPathInfo(path string) map[string]*MountPath {
	cmd := "df -Thm"
	if path != "" {
		cmd = cmd + " " + path
	}
	cmdDfm, err := ExecShellCommand(false, cmd)
	mountPaths := make(map[string]*MountPath)
	mountPaths = ParseDfOutput(cmdDfm)
	if err != nil {
		return mountPaths // empty map
	}
	return mountPaths
}

// FileSystem TODO
type FileSystem struct {
	DiskName   string
	DiskType   string
	MountPoint string

	Total      uint64
	Used       uint64
	Free       uint64
	Avail      uint64
	UsePercent float64
}

func getDiskType(fs sigar.FileSystem, blk *block.Info) string {
	for _, item := range blk.Disks {
		for _, part := range item.Partitions {
			if part.MountPoint == fs.DirName && item.DriveType != block.DRIVE_TYPE_UNKNOWN {
				return item.DriveType.String()
			}
		}
	}
	return block.STORAGE_CONTROLLER_UNKNOWN.String()
}

// GetFileSystems 获取主机上的所有文件系统信息
func GetFileSystems() ([]FileSystem, error) {
	blk, err := ghw.Block()
	if err != nil {
		return nil, fmt.Errorf("get block storage info failed, err:%+v", err)
	}

	partitions := make([]FileSystem, 0)
	fslist := sigar.FileSystemList{}
	if err := fslist.Get(); err != nil {
		return nil, err
	}

	for _, fs := range fslist.List {
		dirName := fs.DirName

		usage := sigar.FileSystemUsage{}

		if err := usage.Get(dirName); err != nil {
			return nil, err
		}

		fmt.Printf("%+v", fs)
		partitions = append(partitions, FileSystem{
			DiskName:   fs.DevName,
			DiskType:   getDiskType(fs, blk),
			MountPoint: dirName,
			Total:      usage.Total,
			Used:       usage.Used,
			Free:       usage.Free,
			Avail:      usage.Avail,
			UsePercent: usage.UsePercent(),
		})
	}
	return partitions, nil
}

var (
	// DataMountPointRe TODO
	DataMountPointRe = regexp.MustCompile(`^` + string(os.PathSeparator) + `data\d*$`)
)

// GetMostSuitableMountPoint 获取哪个剩余磁盘最大的目录
func GetMostSuitableMountPoint() (FileSystem, error) {
	fsList, err := GetFileSystems()
	if err != nil {
		return FileSystem{}, err
	}
	var maxAvFs FileSystem
	for _, item := range fsList {
		if DataMountPointRe.MatchString(item.MountPoint) {
			if item.Free > maxAvFs.Free {
				maxAvFs = item
			}
		}
	}
	return maxAvFs, nil
}
