package util

import (
	"fmt"
	"net"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
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

// GetReservedDiskSize return reserved disk size by hdfs service
func GetReservedDiskSize() int64 {
	// 获取目录空间大小，单位byte
	maxDiskSize := GetMaxSize()
	needReservedSize := int64(ReservedRatio * float64(maxDiskSize))
	if needReservedSize > DefaultDiskReservedSize {
		return needReservedSize
	} else {
		return DefaultDiskReservedSize
	}
}

// GetTolerateFailedVolumes return datanode tolerate failed volumes, greater than the num would be exit
func GetTolerateFailedVolumes() int {
	// 获取挂载数据目录数
	dirCount := len(GetHdfsDataMountDir())
	// 若 数据目录数少于默认容忍数 + 1，则返回数据目录数 - 1
	if dirCount > DefaultTolerateFailedVolumes+1 {
		return DefaultTolerateFailedVolumes
	} else {
		return dirCount - 1
	}
}

// GetLocalHostNameByMap 返回本地主机IP对应的主机名
func GetLocalHostNameByMap(hostMap map[string]string) string {
	addressArr, err := net.InterfaceAddrs()
	if err != nil {
		return DefaultDnHostName
	}
	for _, addr := range addressArr {
		if ipNet, ok := addr.(*net.IPNet); ok {
			if ipNet.IP.To4() != nil {
				localIP := ipNet.IP.String()
				value, exists := hostMap[localIP]
				if exists {
					return value
				}
			}
		}
	}
	err = fmt.Errorf("can't find local ip")
	return DefaultDnHostName
}

const (
	// ReservedRatio 磁盘保留比例
	ReservedRatio float64 = 0.05
	// DefaultDiskReservedSize 默认磁盘保留大小
	DefaultDiskReservedSize int64 = 1 * 1024 * 1024 * 1024
	// DefaultTolerateFailedVolumes 默认忍受坏盘个数
	DefaultTolerateFailedVolumes = 2
	// DefaultDnHostName 默认DN主机名
	DefaultDnHostName string = "0.0.0.0"
)
