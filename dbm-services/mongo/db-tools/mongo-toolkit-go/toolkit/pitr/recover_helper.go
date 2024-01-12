package pitr

import (
	"github.com/pkg/errors"
	"os"
	"time"
)

// ParseTimeStr 解析时间字符串 TODO: 改为RFC3339格式
func ParseTimeStr(timeStr string) (uint32, error) {
	var recoverTime uint32
	loc, _ := time.LoadLocation("Asia/Chongqing")
	if tv, err := time.ParseInLocation("2006-01-02T15:04:05", timeStr, loc); err == nil {
		recoverTime = uint32(tv.Unix())
		return recoverTime, nil
	} else {
		return 0, errors.Wrap(err, "time.ParseInLocation")
	}

}

// ParseSrcFileDir 解析源文件目录
func ParseSrcFileDir(srcAddr, dir string, recoverUnixTime uint32) (*BackupFileName, []*BackupFileName, error) {
	files, err := getFiles(dir)
	if err != nil {
		err = errors.Wrap(err, "getFiles")
		return nil, nil, err
	}

	var fileObjList []*BackupFileName
	for _, file := range files {
		fileObj, err := DecodeFilename(file)
		// 目录下可能存在非备份文件，忽略
		if err != nil {
			continue
		}
		// 目录下可能存在其它备份文件，忽略
		if srcAddr == fileObj.Host+":"+fileObj.Port {
			fileObjList = append(fileObjList, fileObj)
		}
	}
	return FindNeedFiles(fileObjList, recoverUnixTime)
}

func getFiles(dirPth string) (files []string, err error) {
	entries, err := os.ReadDir(dirPth)
	if err != nil {
		return nil, err
	}
	for _, fi := range entries {
		if fi.IsDir() { // 忽略 目录
			continue
		} else {
			files = append(files, fi.Name())
		}
	}
	return files, nil
}
