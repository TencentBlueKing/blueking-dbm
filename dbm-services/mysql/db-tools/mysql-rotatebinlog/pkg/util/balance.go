package util

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
)

// DecideSizeToRemove 尽量保证每个 port 的 binlog 大小接近
// 输入单位 MB
func DecideSizeToRemove(ports map[int]int64, sizeToFree int64) map[int]int64 {
	sizeDeleted := int64(0)                  // 实际计划删除的总单位数
	var portSizeToFree = make(map[int]int64) // 实际计划的每个port删除的 MB
	if sizeToFree <= 0 {
		return portSizeToFree
	}
	for {
		port := reduceFromMax(ports, 1)
		if port == 0 {
			logger.Warn("没有找到完全满足删除条件的实例. portSizeToFree:%+v", portSizeToFree)
			return portSizeToFree
		}
		sizeDeleted += 1 // 每次删除一个单位
		portSizeToFree[port] += cst.ReduceStepSizeMB * 1

		if sizeDeleted*cst.ReduceStepSizeMB >= sizeToFree {
			break
		}
	}
	logger.Info("we got every instance binlog size to delete MB:%+v", portSizeToFree)
	return portSizeToFree
}

// reduceFromMax ports代表当前实例的binlog大小
// 会修改 ports map 里面端口对应的 size 大小
func reduceFromMax(ports map[int]int64, incr int) (port int) {
	maxSize := int64(0)
	var maxSizePort int = 0
	for p, s := range ports {
		if s > maxSize && s >= cst.ReserveMinSizeMB+cst.ReduceStepSizeMB {
			maxSize = s
			maxSizePort = p
		}
	}
	ports[maxSizePort] = ports[maxSizePort] - int64(incr*cst.ReduceStepSizeMB)
	if ports[maxSizePort] >= 0 {
		return maxSizePort
	} else {
		return 0
	}
}
