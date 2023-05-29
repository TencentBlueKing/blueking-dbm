package util

import (
	"fmt"
	"runtime"

	"github.com/shirou/gopsutil/v3/mem"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// GetTendisplusBlockcache 返回单位Mbyte
// 如果系统内存小于4GB,则 instBlockcache = 系统总内存 * 0.3 / 实例数
// 否则 instBlockcache = 系统总内存 * 0.5 / 实例数
func GetTendisplusBlockcache(instCount uint64) (instBlockcache uint64, err error) {
	if instCount <= 0 {
		err = fmt.Errorf("instCount==%d <=0", instCount)
		return
	}
	var vMem *mem.VirtualMemoryStat
	vMem, err = mem.VirtualMemory()
	if err != nil {
		err = fmt.Errorf("mem.VirtualMemory fail,err:%v", err)
		return
	}
	if vMem.Total < 4*consts.GiByte {
		instBlockcache = vMem.Total * 3 / (10 * instCount)
	} else {
		instBlockcache = vMem.Total * 5 / (10 * instCount)
	}
	if instBlockcache < 128*consts.MiByte {
		instBlockcache = 128 * consts.MiByte
	}
	instBlockcache = instBlockcache / consts.MiByte
	return
}

// GetTendisplusWriteBufferSize 返回单位是Byte
// 如果系统内存小于8GB,则 writeBufferSize = 8MB,否则 writeBufferSize = 32MB
func GetTendisplusWriteBufferSize(instCount uint64) (writeBufferSize uint64, err error) {
	if instCount <= 0 {
		err = fmt.Errorf("instCount==%d <=0", instCount)
		return
	}
	var vMem *mem.VirtualMemoryStat
	vMem, err = mem.VirtualMemory()
	if err != nil {
		err = fmt.Errorf("mem.VirtualMemory fail,err:%v", err)
		return
	}
	if vMem.Total <= 8*consts.GiByte {
		writeBufferSize = 8 * consts.MiByte
	} else {
		writeBufferSize = 32 * consts.MiByte
	}
	return
}

func mustBetweenMinAndMax(val, minVal, maxVal int) (ret int) {
	if val < minVal {
		ret = minVal
	} else if val > maxVal {
		ret = maxVal
	} else {
		ret = val
	}
	return
}

// GetTendisplusNetIOThreadNum 根据系统cpu核数,返回tendisplus net io线程数
func GetTendisplusNetIOThreadNum() int {
	var ret int
	minVal := 2
	maxVal := 12
	cpuCoresNum := runtime.NumCPU()
	if cpuCoresNum <= 4 {
		return 1
	}
	ret = cpuCoresNum / 4
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetTendisplusExeThreadNum 根据系统cpu核数,返回tendisplus executor线程数
func GetTendisplusExeThreadNum() int {
	var ret int
	minVal := 8
	maxVal := 56
	cpuCoresNum := runtime.NumCPU()
	if cpuCoresNum <= 4 {
		return cpuCoresNum
	}
	ret = cpuCoresNum * 3 / 4
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetTendisplusExeWorkPoolSize 根据系统cpu核数,返回tendisplus executor pool size
func GetTendisplusExeWorkPoolSize() int {
	var ret int
	minVal := 2
	maxVal := 8
	cpuCoresNum := runtime.NumCPU()
	if cpuCoresNum <= 2 {
		return 1
	} else if cpuCoresNum == 4 {
		return 2
	} else if cpuCoresNum > 4 {
		ret = cpuCoresNum / 4
	}
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetTendisplusMaxBGJobs  根据系统cpu核数,返回tendisplus rocks.max_background_jobs
func GetTendisplusMaxBGJobs() int {
	var ret int
	minVal := 2
	maxVal := 24
	cpuCoresNum := runtime.NumCPU()
	if cpuCoresNum <= 4 {
		return cpuCoresNum
	}
	ret = cpuCoresNum * 3 / 4
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetIncrPushThreadnum 根据系统cpu核数,返回tendisplus incrPushThreadnum
func GetIncrPushThreadnum() int {
	var ret int
	minVal := 2
	maxVal := 8
	cpuCoresNum := runtime.NumCPU()
	ret = cpuCoresNum / 4
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetMaxBgCompactions 根据系统cpu核数,返回tendisplus rocks.max_background_compactions
func GetMaxBgCompactions() int {
	return runtime.NumCPU()
}

// GetMigrateSenderThreadNum 根据系统cpu核数,返回tendisplus migrateSenderThreadnum
func GetMigrateSenderThreadNum() int {
	var ret int
	minVal := 4
	maxVal := 16
	cpuCoresNum := runtime.NumCPU()
	ret = cpuCoresNum / 3
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetMigrateReceiverThreadNum 根据系统cpu核数,返回tendisplus migrateReceiveThreadnum
func GetMigrateReceiverThreadNum() int {
	var ret int
	minVal := 4
	maxVal := 16
	cpuCoresNum := runtime.NumCPU()
	ret = cpuCoresNum / 3
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}

// GetMigrateClearTheadNum 根据系统cpu核数,返回tendisplus migrateClearThreadnum
func GetMigrateClearTheadNum() int {
	var ret int
	minVal := 1
	maxVal := 4
	cpuCoresNum := runtime.NumCPU()
	ret = cpuCoresNum / 16
	ret = mustBetweenMinAndMax(ret, minVal, maxVal)
	return ret
}
