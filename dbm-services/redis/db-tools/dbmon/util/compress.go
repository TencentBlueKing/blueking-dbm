package util

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"

	"github.com/dustin/go-humanize"
)

// IsZstdExecutable 通过'zstd -V'命令确定本地zstd工具是能正常运行的
func IsZstdExecutable() (ok bool) {
	var err error
	if !FileExists(consts.ZstdBin) {
		return false
	}
	cmd := exec.Command(consts.ZstdBin, "-V")
	if err = cmd.Start(); err != nil {
		// err = fmt.Errorf("'%s -V' cmd.Start fail,err:%v", zstdBin, err)
		return false
	}
	if err = cmd.Wait(); err != nil {
		// err = fmt.Errorf("'%s -V' cmd.Wait fail,err:%v", zstdBin, err)
		return false
	}
	return true
}

// CompressFile 压缩文件
// 优先使用zstd 做压缩,zstd无法使用则使用gzip
func CompressFile(file, targetDir string, rmOrigin bool) (retFile string, err error) {
	var compressCmd string
	fileDir := filepath.Dir(file)
	filename := filepath.Base(file)
	if targetDir == "" {
		targetDir = fileDir
	}
	if IsZstdExecutable() {
		retFile = filepath.Join(targetDir, filename+".zst")
		if rmOrigin {
			compressCmd = fmt.Sprintf(`cd %s && %s --rm -T4 %s -o %s`, fileDir, consts.ZstdBin, filename, retFile)
		} else {
			compressCmd = fmt.Sprintf(`cd %s && %s -T4 %s -o %s`, fileDir, consts.ZstdBin, filename, retFile)
		}
		_, err = RunBashCmd(compressCmd, "", nil, 6*time.Hour)
		if err != nil {
			return
		}
	} else {
		retFile = filepath.Join(targetDir, filename+".gz")
		if rmOrigin {
			compressCmd = fmt.Sprintf(`gzip < %s >%s && rm -f %s`, file, retFile, file)
		} else {
			compressCmd = fmt.Sprintf(`gzip < %s >%s`, file, retFile)
		}
		_, err = RunBashCmd(compressCmd, "", nil, 6*time.Hour)
		if err != nil {
			return
		}
	}
	return
}

// SplitLargeFile 切割大文件为小文件,并返回切割后的结果
// 参数file须是全路径;
// 如果file大小 小于  splitTargetSize,则返回值splitTargetSize只包含 file 一个元素
func SplitLargeFile(file, splitTargetSize string, rmOrigin bool) (splitedFiles []string, err error) {
	var fileSize int64
	var splitLimit uint64
	var cmdRet string
	if file == "" {
		return
	}
	fileSize, err = GetFileSize(file)
	if err != nil {
		return
	}
	splitLimit, err = humanize.ParseBytes(splitTargetSize)
	if err != nil {
		err = fmt.Errorf("humanize.ParseBytes fail,err:%v,splitTargetSize:%s", err, splitTargetSize)
		return
	}
	if fileSize < int64(splitLimit) {
		splitedFiles = append(splitedFiles, file)
		return
	}
	fileDir := filepath.Dir(file)
	fileBase := filepath.Base(file)
	fileBase = strings.TrimSuffix(fileBase, ".tar")
	fileBase = strings.TrimSuffix(fileBase, ".tar.gz")
	fileBase = fileBase + ".split."
	splitCmd := fmt.Sprintf(`cd %s && split --verbose -a 3 -b %s -d %s %s|grep -i --only-match -E "%s[0-9]+"`,
		fileDir, splitTargetSize, file, fileBase, fileBase)
	mylog.Logger.Info(splitCmd)
	cmdRet, err = RunBashCmd(splitCmd, "", nil, 6*time.Hour)
	if err != nil {
		return
	}
	l01 := strings.Split(cmdRet, "\n")
	for _, item := range l01 {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		splitedFiles = append(splitedFiles, filepath.Join(fileDir, item))
	}
	if rmOrigin {
		err = os.Remove(file)
		mylog.Logger.Info(fmt.Sprintf("rm %s", file))
		if err != nil {
			err = fmt.Errorf("os.Remove fail,err:%v,file:%s", err, file)
			return
		}
	}
	return
}

// TarADir 对一个目录进行tar打包,
// 如打包 /data/dbbak/REDIS-FULL-rocksdb-1.1.1.1-30000 为 /tmp/REDIS-FULL-rocksdb-1.1.1.1-30000.tar
// 参数: originDir 为 /data/dbbak/REDIS-FULL-rocksdb-1.1.1.1-30000
// 参数: tarSaveDir 为 /tmp/
// 返回值: tarFile 为  /tmp/REDIS-FULL-rocksdb-1.1.1.1-30000.tar
func TarADir(originDir, tarSaveDir string, rmOrigin bool) (tarFile string, err error) {
	var tarCmd, rmCmd string
	basename := filepath.Base(originDir)
	baseDir := filepath.Dir(originDir)
	if tarSaveDir == "" {
		tarSaveDir = filepath.Dir(originDir)
	}
	tarFile = filepath.Join(tarSaveDir, basename+".tar")

	if rmOrigin {
		tarCmd = fmt.Sprintf(`cd %s && tar --remove-files  -cf %s  %s && rm -rf %s`,
			baseDir, filepath.Base(tarFile), basename, basename)
		rmCmd = fmt.Sprintf("rm -f %s", tarFile)
	} else {
		tarCmd = fmt.Sprintf(`cd %s && tar -cf %s %s`, baseDir, filepath.Base(tarFile), basename)
		rmCmd = fmt.Sprintf("rm -f %s", tarFile)
	}
	mylog.Logger.Info(tarCmd)
	maxRetryTimes := 5
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		err = nil
		_, err = RunBashCmd(tarCmd, "", nil, 6*time.Hour)
		if err != nil {
			// 如果报错则删除tar文件然后重试
			mylog.Logger.Info(rmCmd)
			RunBashCmd(rmCmd, "", nil, 10*time.Minute)
			continue
		}
		// tar命令成功了,则退出
		break
	}
	if err != nil {
		return
	}
	return
}

// TarAndSplitADir 对目录tar打包并执行split
func TarAndSplitADir(originDir, targetSaveDir, splitTargetSize string, rmOrigin bool) (
	splitedFiles []string, err error) {
	var tarFile string
	tarFile, err = TarADir(originDir, targetSaveDir, rmOrigin)
	if err != nil {
		return
	}
	splitedFiles, err = SplitLargeFile(tarFile, splitTargetSize, rmOrigin)
	if err != nil {
		return
	}
	return
}
