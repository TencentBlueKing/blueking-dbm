package dorisutil

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"os"
	"strings"
)

// GetAllDataDir 获取所有/data*的路径
func GetAllDataDir() ([]string, error) {
	files, err := os.ReadDir("/")
	if err != nil {
		logger.Error("[%s] execute failed, %v", err)
		return nil, err
	}

	var dataDir []string
	for _, file := range files {
		if file.IsDir() && strings.HasPrefix(file.Name(), "data") {
			dataDir = append(dataDir, "/"+file.Name())
		}
	}
	return dataDir, nil
}

// GetDataMountDir 获取挂载的/data开头目录，若无则默认返回/data
func GetDataMountDir() []string {
	var dirs []string
	mountPaths := osutil.GetMountPathInfo()
	for k, _ := range mountPaths {
		// 仅判断挂盘/data目录
		if strings.HasPrefix(k, "/data") {
			dirs = append(dirs, k)
		}
	}
	if dirs == nil {
		// default data dir
		dirs = append(dirs, "/data")
	}
	return dirs
}

// GetMaxSize 获取挂载data目录中最大的磁盘容量
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

// GetDorisDataMountDir 获取Doris数据节点挂载data目录
func GetDorisDataMountDir() []string {
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
		// default doris data dir
		dirs = append(dirs, "/data")
	}
	return dirs
}
