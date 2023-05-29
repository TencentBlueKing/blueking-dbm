package util

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"strings"
)

// GetMaxSize TODO
func GetMaxSize() int64 {
	mountPaths := osutil.GetMountPathInfo()
	var maxSize int64 = 0
	for k, v := range mountPaths {
		// 仅判断挂盘/data目录
		if strings.HasPrefix(k, "/data") && v.TotalSizeMB > maxSize {
			maxSize = v.TotalSizeMB
		}
	}
	return maxSize
}

// GetHdfsDataMountDir TODO
func GetHdfsDataMountDir() []string {
	var dirs []string
	dirMaxSize := GetMaxSize()
	mountPaths := osutil.GetMountPathInfo()
	for k, v := range mountPaths {
		// 仅判断挂盘/data目录
		if strings.HasPrefix(k, "/data") && v.TotalSizeMB == dirMaxSize {
			dirs = append(dirs, k)
		}
	}
	if dirs == nil {
		// default hdfs data dir
		dirs = append(dirs, "/data")
	}
	return dirs
}
