// Package report ....
package report

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/fileperm"
	"encoding/json"
	"fmt"
	"os"
	"path"

	"github.com/pkg/errors"
)

// report，是一个日志文件，这个文件会由其它Agent发送到Kfk. 格式都是json.

// Report 用于存储备份文件的详细信息.
type Report struct {
	FilePath string
}

// NewReport New Report
func NewReport(filePath string) *Report {
	return &Report{FilePath: filePath}
}

// Append 追加一条记录
func (r *Report) Append(json []byte) error {
	f, err := os.OpenFile(r.FilePath, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0755)
	if err != nil {
		return err
	}
	defer f.Close()
	json = append(json, []byte("\n")...)
	if _, err = f.Write(json); err != nil {
		return err
	}
	return nil
}

// AppendObject 追加一条记录
func (r *Report) AppendObject(v interface{}) error {
	content, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return r.Append(content)
}

// AppendObjectToFile  追加一条记录
func AppendObjectToFile(reportFilePath string, v interface{}) error {
	r := NewReport(reportFilePath)
	return r.AppendObject(v)
}

// PrepareReportPath 准备report文件: 如果文件不存在:创建目录，创建文件. 如果文件存在，测试是否有写入权限.
func PrepareReportPath(filePath string) error {
	fileDir := path.Dir(filePath)
	_, err := os.Stat(fileDir)
	if err != nil {
		if os.IsNotExist(err) == true {
			if err = os.MkdirAll(fileDir, os.FileMode(0755)); err != nil {
				return errors.Wrap(err, fmt.Sprintf("MkdirAll fail,err:%v,dir:%s", err, fileDir))
			}
		} else {
			return errors.Wrap(err, fmt.Sprintf("Stat dir %s fail,err:%v", fileDir, err))
		}
	}

	var file os.FileInfo
	file, err = os.Stat(filePath)
	// 如果文件不存在，创建文件.
	if err != nil {
		if os.IsNotExist(err) == true {
			f, err := os.OpenFile(filePath, os.O_RDWR|os.O_CREATE, 0666)
			if err == nil {
				f.Close()
			}
			return errors.Wrap(err, fmt.Sprintf("Create file %s fail,err:%v", filePath, err))
		} else {
			return errors.Wrap(err, fmt.Sprintf("Stat file %s fail,err:%v", filePath, err))
		}
	}
	// 如果文件存在，测试文件是否文件File，且可写.
	if file.IsDir() {
		return errors.Errorf("file %s is not a file", filePath)
	}
	if !fileperm.IsFileWritable(filePath) {
		return errors.Errorf("file %s is not writable", filePath)
	}
	return nil

}
