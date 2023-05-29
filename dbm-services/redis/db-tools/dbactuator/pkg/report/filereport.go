// Package report  (备份等)记录上报
package report

import (
	"bufio"
	"fmt"
	"os"
	"sync"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

var _ Reporter = (*FileReport)(nil)

// FileReport 文件上报
type FileReport struct {
	saveFile  string
	fileP     *os.File
	bufWriter *bufio.Writer
	mux       sync.Mutex // 并发安全写入
}

// NewFileReport new
func NewFileReport(savefile string) (ret *FileReport, err error) {
	ret = &FileReport{}
	err = ret.SetSaveFile(savefile)
	return ret, err
}

// AddRecord 新增记录
func (f *FileReport) AddRecord(item string, flush bool) (err error) {
	if f.saveFile == "" {
		err = fmt.Errorf("saveFile(%s) can't be empty", f.saveFile)
		mylog.Logger.Error(err.Error())
		return
	}
	_, err = f.bufWriter.WriteString(item)
	if err != nil {
		err = fmt.Errorf("bufio.Writer WriteString fail,err:%v,saveFile:%s", err, f.saveFile)
		mylog.Logger.Error(err.Error())
		return
	}
	if flush == true {
		f.bufWriter.Flush()
	}
	return nil
}

// SaveFile ..
func (f *FileReport) SaveFile() string {
	return f.saveFile
}

// SetSaveFile set方法
func (f *FileReport) SetSaveFile(savefile string) error {
	var err error
	err = f.Close()
	if err != nil {
		return err
	}
	if savefile == "" {
		err = fmt.Errorf("saveFile(%s) cannot be empty", savefile)
		mylog.Logger.Error(err.Error())
		return err
	}
	f.saveFile = savefile
	f.fileP, err = os.OpenFile(savefile, os.O_APPEND|os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		err = fmt.Errorf("open file:%s fail,err:%v", savefile, err)
		mylog.Logger.Error(err.Error())
		return err
	}
	f.bufWriter = bufio.NewWriter(f.fileP)
	return nil
}

// Close file
func (f *FileReport) Close() error {
	f.mux.Lock()
	defer f.mux.Unlock()

	var err error
	if f.saveFile == "" {
		return nil
	}
	f.saveFile = ""

	err = f.bufWriter.Flush()
	if err != nil {
		err = fmt.Errorf("bufio flush fail.err:%v,file:%s", err, f.saveFile)
		mylog.Logger.Error(err.Error())
		return nil
	}
	err = f.fileP.Close()
	if err != nil {
		err = fmt.Errorf("file close fail.err:%v,file:%s", err, f.saveFile)
		mylog.Logger.Error(err.Error())
		return nil
	}
	return nil
}
