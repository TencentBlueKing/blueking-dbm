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

// GetLocalHostNameByMap 根据IP-主机名映射表解析本地主机的主机名
//
// 函数逻辑：获取本机所有网络接口地址，遍历IPv4非回环地址，优先返回在hostMap中匹配的主机名，
// 若无匹配则返回第一个非回环IP作为兜底，若无可用的非回环IPv4地址则返回错误。
//
// 参数:
//
//	hostMap - IP地址到主机名的映射表，key为IP字符串，value为主机名
//
// 返回值:
//
//	string - 解析到的主机名或IP地址
//	error  - 错误信息，包括无法获取网络接口地址或本机无可用的非回环IPv4地址
//
// 使用场景: 用于HDFS DataNode注册时确定自身的主机标识，避免使用0.0.0.0等无效地址
func GetLocalHostNameByMap(hostMap map[string]string) (string, error) {
	addressArr, err := net.InterfaceAddrs()
	if err != nil {
		return "", fmt.Errorf("get local interface addrs failed: %w", err)
	}
	var firstNonLoopBackIP string
	for _, addr := range addressArr {
		if ipNet, ok := addr.(*net.IPNet); ok {
			// 跳过回环地址，避免误返回127.0.0.1
			if ipNet.IP.To4() != nil && !ipNet.IP.IsLoopback() {
				localIP := ipNet.IP.String()
				// 记录第一个非回环IP作为兜底
				if firstNonLoopBackIP == "" {
					firstNonLoopBackIP = localIP
				}
				// 在hostMap中找到映射则立即返回对应主机名
				if value, exists := hostMap[localIP]; exists {
					return value, nil
				}
			}
		}
	}
	// 兜底：返回第一个非回环IP，若无则返回错误
	if firstNonLoopBackIP != "" {
		return firstNonLoopBackIP, nil
	}
	return "", fmt.Errorf("can not resolve local hostname: no non-loopback IPv4 found, hostMap=%v", hostMap)
}

const (
	// ReservedRatio 磁盘保留比例
	ReservedRatio float64 = 0.05
	// DefaultDiskReservedSize 默认磁盘保留大小
	DefaultDiskReservedSize int64 = 1 * 1024 * 1024 * 1024
	// DefaultTolerateFailedVolumes 默认忍受坏盘个数
	DefaultTolerateFailedVolumes = 2
)
