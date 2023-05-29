package osutil

import (
	"dbm-services/common/go-pubpkg/logger"
	"strconv"
	"strings"
)

// IsDataDirOk TODO
func IsDataDirOk(filepath string) bool {
	mountPaths := GetMountPathInfo()
	if m, ok := mountPaths[filepath]; ok {
		// 大于150GB
		if m.AvailSizeMB > 153600 {
			return true
		} else {
			logger.Error("%s available disk size is less than 150GB", filepath)
			return false
		}
	}
	logger.Error("GetMountPathInfo not found mount point: %s", filepath)
	return false
}

// MountPath TODO
type MountPath struct {
	Filesystem     string
	FileSystemType string
	TotalSizeMB    int64
	UsedSizeMB     int64
	AvailSizeMB    int64
	UsePct         int
	Path           string
}

// ParseDfOutput TODO
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
			Path:       fields[5],
			Filesystem: fields[0],
		}
		mountPath.FileSystemType = fields[1]
		mountPath.TotalSizeMB, _ = strconv.ParseInt(fields[2], 10, 64)
		mountPath.UsedSizeMB, _ = strconv.ParseInt(fields[3], 10, 64)
		mountPath.AvailSizeMB, _ = strconv.ParseInt(fields[4], 10, 64)
		mountPath.UsePct, _ = strconv.Atoi(strings.TrimSuffix(fields[5], "%"))

		mountPaths[fields[6]] = mountPath
	}
	return mountPaths
}

// GetMountPathInfo TODO
func GetMountPathInfo() map[string]*MountPath {
	cmdDfm, err := ExecShellCommand(false, "df -Thm")
	mountPaths := ParseDfOutput(cmdDfm)
	if err != nil {
		return nil
	}
	return mountPaths
}
