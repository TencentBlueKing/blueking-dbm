package util

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"

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
		retFile = filepath.Join(fileDir, filename+".gz")
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
	var tarCmd string
	basename := filepath.Base(originDir)
	baseDir := filepath.Dir(originDir)
	if tarSaveDir == "" {
		tarSaveDir = filepath.Dir(originDir)
	}
	tarFile = filepath.Join(tarSaveDir, basename+".tar")

	if rmOrigin {
		tarCmd = fmt.Sprintf(`tar --remove-files  -cf %s  -C %s %s`, tarFile, baseDir, basename)
	} else {
		tarCmd = fmt.Sprintf(`tar -cf %s  -C %s %s`, tarFile, baseDir, basename)
	}
	mylog.Logger.Info(tarCmd)
	_, err = RunBashCmd(tarCmd, "", nil, 6*time.Hour)
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

// UnionSplitFiles 合并多个split文件为一个tar文件
func UnionSplitFiles(dir string, splitFiles []string) (tarfile string, err error) {
	if len(splitFiles) == 0 {
		err = fmt.Errorf("splitFiles:%+v empty list", splitFiles)
		return
	}
	if len(splitFiles) == 1 && strings.HasSuffix(splitFiles[0], ".tar") {
		return splitFiles[0], nil
	}
	var name string
	var fullpath string
	var cmd01 string
	reg01 := regexp.MustCompile(`.split.\d+$`)
	baseNames := make([]string, 0, len(splitFiles))
	for _, file01 := range splitFiles {
		name = filepath.Base(file01)
		baseNames = append(baseNames, name)
		if !reg01.MatchString(file01) {
			err = fmt.Errorf("%+v not split files?", splitFiles)
			return
		}
		fullpath = filepath.Join(dir, name)
		if !FileExists(fullpath) {
			err = fmt.Errorf("%s not exists", fullpath)
			return
		}
	}

	prefix := reg01.ReplaceAllString(baseNames[0], "")
	tarfile = prefix + ".tar"
	if len(baseNames) == 1 {
		cmd01 = fmt.Sprintf("cd %s && mv %s %s", dir, baseNames[0], tarfile)
	} else {
		cmd01 = fmt.Sprintf("cd %s && cat %s.split* > %s", dir, prefix, tarfile)
	}
	mylog.Logger.Info(cmd01)
	_, err = RunBashCmd(cmd01, "", nil, 2*time.Hour)
	tarfile = filepath.Join(dir, tarfile)
	return
}
