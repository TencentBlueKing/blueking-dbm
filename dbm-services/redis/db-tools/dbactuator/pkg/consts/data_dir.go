package consts

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
)

// fileExists 检查目录是否已经存在
func fileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

// IsMountPoint2 Determine if a directory is a mountpoint, by comparing the device for the directory
// with the device for it's parent.  If they are the same, it's not a mountpoint, if they're
// different, it is.
// reference: https://github.com/cnaize/kubernetes/blob/master/pkg/util/mount/mountpoint_unix.go#L29
// 该函数与util/util.go 中 IsMountPoint()相同,但package consts 不建议依赖其他模块故拷贝了实现
func IsMountPoint2(file string) bool {
	stat, err := os.Stat(file)
	if err != nil {
		return false
	}
	rootStat, err := os.Lstat(file + "/..")
	if err != nil {
		return false
	}
	// If the directory has the same device as parent, then it's not a mountpoint.
	return stat.Sys().(*syscall.Stat_t).Dev != rootStat.Sys().(*syscall.Stat_t).Dev
}

// SetRedisDataDir 设置环境变量 REDIS_DATA_DIR,并持久化到/etc/profile中
// 如果函数参数 dataDir 不为空,则 REDIS_DATA_DIR = {dataDir}
// 否则,如果环境变量 REDIS_DATA_DIR 不为空,则直接读取;
// 否则,如果 /data1/redis 存在, 则 REDIS_DATA_DIR=/data1
// 否则,如果 /data/redis, 则 REDIS_DATA_DIR=/data
// 否则,如果 /data1 是挂载点, 则 REDIS_DATA_DIR=/data1
// 否则,如果 /data 是挂载点, 则 REDIS_DATA_DIR=/data
// 否则,REDIS_DATA_DIR=/data1
func SetRedisDataDir(dataDir string) (err error) {
	if dataDir == "" {
		envDir := os.Getenv("REDIS_DATA_DIR")
		if envDir != "" { // 环境变量 REDIS_DATA_DIR 不为空
			dataDir = envDir
		} else {
			if fileExists(filepath.Join(Data1Path, "redis")) {
				// /data1/redis 存在
				dataDir = Data1Path
			} else if fileExists(filepath.Join(DataPath, "redis")) {
				// /data/redis 存在
				dataDir = DataPath
			} else if IsMountPoint2(Data1Path) {
				// /data1是挂载点
				dataDir = Data1Path
			} else if IsMountPoint2(DataPath) {
				// /data是挂载点
				dataDir = DataPath
			} else {
				// 函数参数 dataDir为空, 环境变量 REDIS_DATA_DIR 为空
				// /data1 和 /data 均不是挂载点
				// 强制指定 REDIS_DATA_DIR=/data1
				dataDir = Data1Path
			}
		}
	}
	dataDir = strings.TrimSpace(dataDir)
	var ret []byte
	shCmd := fmt.Sprintf(`
ret=$(grep '^export REDIS_DATA_DIR=' /etc/profile)
if [[ -z $ret ]]
then
echo "export REDIS_DATA_DIR=%s">>/etc/profile
fi
	`, dataDir)
	ret, err = exec.Command("bash", "-c", shCmd).Output()
	if err != nil {
		err = fmt.Errorf("SetRedisDataDir failed,err:%v,ret:%s,shCmd:%s", err, string(ret), shCmd)
		return
	}
	os.Setenv("REDIS_DATA_DIR", dataDir)
	return nil
}

// GetRedisDataDir 获取环境变量 REDIS_DATA_DIR,不为空直接返回,
// 否则,如果目录 /data1/redis存在,返回 /data1;
// 否则,如果目录 /data/redis存在,返回 /data;
// 否则,返回 /data1
func GetRedisDataDir() string {
	dataDir := os.Getenv("REDIS_DATA_DIR")
	if dataDir == "" {
		if fileExists(filepath.Join(Data1Path, "redis")) {
			// /data1/redis 存在
			dataDir = Data1Path
		} else if fileExists(filepath.Join(DataPath, "redis")) {
			// /data/redis 存在
			dataDir = DataPath
		} else {
			dataDir = Data1Path
		}
	}
	return dataDir
}

// SetRedisBakcupDir 设置环境变量 REDIS_BACKUP_DIR ,并持久化到/etc/profile中
// 如果函数参数 backupDir 不为空,则 REDIS_BACKUP_DIR = {backupDir}
// 否则,如果环境变量 REDIS_BACKUP_DIR 不为空,则直接读取;
// 否则,如果 /data/dbbak 存在, 则 REDIS_BACKUP_DIR=/data
// 否则,如果 /data1/dbbak 存在, 则 REDIS_BACKUP_DIR=/data1
// 否则,如果 /data 是挂载点, 则 REDIS_BACKUP_DIR=/data
// 否则,如果 /data1 是挂载点, 则 REDIS_BACKUP_DIR=/data1
// 否则,REDIS_BACKUP_DIR=/data
func SetRedisBakcupDir(backupDir string) (err error) {
	if backupDir == "" {
		envDir := os.Getenv("REDIS_BACKUP_DIR")
		if envDir != "" {
			backupDir = envDir
		} else {
			if fileExists(filepath.Join(DataPath, "dbbak")) {
				// /data/dbbak 存在
				backupDir = DataPath
			} else if fileExists(filepath.Join(Data1Path, "dbbak")) {
				// /data1/dbbak 存在
				backupDir = Data1Path
			} else if IsMountPoint2(DataPath) {
				// /data是挂载点
				backupDir = DataPath
			} else if IsMountPoint2(Data1Path) {
				// /data1是挂载点
				backupDir = Data1Path
			} else {
				// 函数参数 backupDir 为空, 环境变量 REDIS_BACKUP_DIR 为空
				// /data1 和 /data 均不是挂载点
				// 强制指定 REDIS_BACKUP_DIR=/data
				backupDir = DataPath
			}
		}
	}
	backupDir = strings.TrimSpace(backupDir)
	var ret []byte
	shCmd := fmt.Sprintf(`
ret=$(grep '^export REDIS_BACKUP_DIR=' /etc/profile)
if [[ -z $ret ]]
then
echo "export REDIS_BACKUP_DIR=%s">>/etc/profile
fi
	`, backupDir)
	ret, err = exec.Command("bash", "-c", shCmd).Output()
	if err != nil {
		err = fmt.Errorf("SetRedisBakcupDir failed,err:%v,ret:%s", err, string(ret))
		return
	}
	os.Setenv("REDIS_BACKUP_DIR", backupDir)
	return nil
}

// GetRedisBackupDir 获取环境变量 REDIS_BACKUP_DIR,默认值 /data
// 否则,如果目录 /data/dbbak 存在,返回 /data;
// 否则,如果目录 /data1/dbbak 存在,返回 /data1;
// 否则,返回 /data
func GetRedisBackupDir() string {
	dataDir := os.Getenv("REDIS_BACKUP_DIR")
	if dataDir == "" {
		if fileExists(filepath.Join(DataPath, "dbbak")) {
			// /data/dbbak 存在
			dataDir = DataPath
		} else if fileExists(filepath.Join(Data1Path, "dbbak")) {
			// /data1/dbbak 存在
			dataDir = Data1Path
		} else {
			dataDir = DataPath
		}
	}
	return dataDir
}

// SetMongoDataDir 设置环境变量 MONGO_DATA_DIR,并持久化到/etc/profile中
// 如果函数参数 dataDir 不为空,则 MONGO_DATA_DIR = {dataDir}
// 否则,如果环境变量 MONGO_DATA_DIR 不为空,则直接读取;
// 否则,如果 /data1/redis 存在, 则 MONGO_DATA_DIR=/data1
// 否则,如果 /data/redis, 则 MONGO_DATA_DIR=/data
// 否则,如果 /data1 是挂载点, 则 MONGO_DATA_DIR=/data1
// 否则,如果 /data 是挂载点, 则 MONGO_DATA_DIR=/data
// 否则,MONGO_DATA_DIR=/data1
func SetMongoDataDir(dataDir string) (err error) {
	if dataDir == "" {
		envDir := os.Getenv("MONGO_DATA_DIR")
		if envDir != "" { // 环境变量 REDIS_DATA_DIR 不为空
			dataDir = envDir
		} else {
			if fileExists(filepath.Join(Data1Path, "mongodata")) {
				// /data1/mongodata 存在
				dataDir = Data1Path
			} else if fileExists(filepath.Join(DataPath, "mongodata")) {
				// /data/mongodata 存在
				dataDir = DataPath
			} else if IsMountPoint2(Data1Path) {
				// /data1是挂载点
				dataDir = Data1Path
			} else if IsMountPoint2(DataPath) {
				// /data是挂载点
				dataDir = DataPath
			} else {
				// 函数参数 dataDir为空, 环境变量 MONGO_DATA_DIR 为空
				// /data1 和 /data 均不是挂载点
				// 强制指定 MONGO_DATA_DIR=/data1
				dataDir = Data1Path
			}
		}
	}
	dataDir = strings.TrimSpace(dataDir)
	var ret []byte
	shCmd := fmt.Sprintf(`
ret=$(grep '^export MONGO_DATA_DIR=' /etc/profile)
if [[ -z $ret ]]
then
echo "export MONGO_DATA_DIR=%s">>/etc/profile
fi
	`, dataDir)
	ret, err = exec.Command("bash", "-c", shCmd).Output()
	if err != nil {
		err = fmt.Errorf("SetMongoDataDir failed,err:%v,ret:%s,shCmd:%s", err, string(ret), shCmd)
		return
	}
	os.Setenv("MONGO_DATA_DIR", dataDir)
	return nil
}

// GetMongoDataDir 获取环境变量 MONGO_DATA_DIR,不为空直接返回,
// 否则,如果目录 /data1/mongodata存在,返回 /data1;
// 否则,如果目录 /data/mongodata存在,返回 /data;
// 否则,返回 /data1
func GetMongoDataDir() string {
	dataDir := os.Getenv("MONGO_DATA_DIR")
	if dataDir == "" {
		if fileExists(filepath.Join(Data1Path, "mongodata")) {
			// /data1/mongodata 存在
			dataDir = Data1Path
		} else if fileExists(filepath.Join(DataPath, "mongodata")) {
			// /data/mongodata 存在
			dataDir = DataPath
		} else {
			dataDir = Data1Path
		}
	}
	return dataDir
}

// SetMongoBackupDir 设置环境变量 MONGO_BACKUP_DIR ,并持久化到/etc/profile中
// 如果函数参数 backupDir 不为空,则 MONGO_BACKUP_DIR = {backupDir}
// 否则,如果环境变量 MONGO_BACKUP_DIR 不为空,则直接读取;
// 否则,如果 /data/dbbak 存在, 则 MONGO_BACKUP_DIR=/data
// 否则,如果 /data1/dbbak 存在, 则 MONGO_BACKUP_DIR=/data1
// 否则,如果 /data 是挂载点, 则 MONGO_BACKUP_DIR=/data
// 否则,如果 /data1 是挂载点, 则 MONGO_BACKUP_DIR=/data1
// 否则,MONGO_BACKUP_DIR=/data
func SetMongoBackupDir(backupDir string) (err error) {
	if backupDir == "" {
		envDir := os.Getenv("MONGO_BACKUP_DIR")
		if envDir != "" {
			backupDir = envDir
		} else {
			if fileExists(filepath.Join(DataPath, "dbbak")) {
				// /data/dbbak 存在
				backupDir = DataPath
			} else if fileExists(filepath.Join(Data1Path, "dbbak")) {
				// /data1/dbbak 存在
				backupDir = Data1Path
			} else if IsMountPoint2(DataPath) {
				// /data是挂载点
				backupDir = DataPath
			} else if IsMountPoint2(Data1Path) {
				// /data1是挂载点
				backupDir = Data1Path
			} else {
				// 函数参数 backupDir 为空, 环境变量 MONGO_BACKUP_DIR 为空
				// /data1 和 /data 均不是挂载点
				// 强制指定 MONGO_BACKUP_DIR=/data
				backupDir = DataPath
			}
		}
	}
	backupDir = strings.TrimSpace(backupDir)
	var ret []byte
	shCmd := fmt.Sprintf(`
ret=$(grep '^export MONGO_BACKUP_DIR=' /etc/profile)
if [[ -z $ret ]]
then
echo "export MONGO_BACKUP_DIR=%s">>/etc/profile
fi
	`, backupDir)
	ret, err = exec.Command("bash", "-c", shCmd).Output()
	if err != nil {
		err = fmt.Errorf("SetMongoBakcupDir failed,err:%v,ret:%s", err, string(ret))
		return
	}
	os.Setenv("MONGO_BACKUP_DIR", backupDir)
	return nil
}

// GetMongoBackupDir 获取环境变量 MONGO_BACKUP_DIR,默认值 /data
// 否则,如果目录 /data/dbbak 存在,返回 /data;
// 否则,如果目录 /data1/dbbak 存在,返回 /data1;
// 否则,返回 /data
func GetMongoBackupDir() string {
	dataDir := os.Getenv("MONGO_BACKUP_DIR")
	if dataDir == "" {
		if fileExists(filepath.Join(DataPath, "dbbak")) {
			// /data/dbbak 存在
			dataDir = DataPath
		} else if fileExists(filepath.Join(Data1Path, "dbbak")) {
			// /data1/dbbak 存在
			dataDir = Data1Path
		} else {
			dataDir = DataPath
		}
	}
	return dataDir
}
