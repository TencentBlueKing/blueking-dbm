package osutil

import (
	"strconv"
	"strings"
)

// IsDataDirOk TODO
func IsDataDirOk(filepath string) bool {
	mountPaths := GetMountPathInfo()
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
	Filesystem  string
	TotalSizeMB int64
	UsedSizeMB  int64
	AvailSizeMB int64
	UsePct      int
	Path        string
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
		if len(fields) == 0 || len(fields) != 6 {
			continue
		}
		mountPath := &MountPath{
			Path:       fields[5],
			Filesystem: fields[0],
		}
		mountPath.TotalSizeMB, _ = strconv.ParseInt(fields[1], 10, 64)
		mountPath.UsedSizeMB, _ = strconv.ParseInt(fields[2], 10, 64)
		mountPath.AvailSizeMB, _ = strconv.ParseInt(fields[3], 10, 64)
		mountPath.UsePct, _ = strconv.Atoi(strings.TrimSuffix(fields[4], "%"))

		mountPaths[fields[5]] = mountPath
	}
	return mountPaths
}

// GetMountPathInfo TODO
func GetMountPathInfo() map[string]*MountPath {
	cmdDfm, err := ExecShellCommand(false, "df -hm")
	mountPaths := ParseDfOutput(cmdDfm)
	if err != nil {
		return nil
	}
	return mountPaths
}
