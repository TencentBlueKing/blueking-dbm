package dtsTask

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"dbm-services/redis/redis-dts/pkg/customtime"
	"dbm-services/redis/redis-dts/util"

	"go.uber.org/zap"
)

// SyncSeqItem redis-sync binlog seq & time
type SyncSeqItem struct {
	Time  customtime.CustomTime `json:"time"`
	RunID string                `json:"runID"`
	Seq   uint64                `json:"seq"`
}

// String ..
func (pos *SyncSeqItem) String() string {
	ret, _ := json.Marshal(pos)
	return string(ret)
}

// SyncSeqItemDecode string decode to SyncSeqItem
func SyncSeqItemDecode(str01 string) (item SyncSeqItem, err error) {
	str01 = strings.TrimSpace(str01)
	item = SyncSeqItem{}
	err = json.Unmarshal([]byte(str01), &item)
	if err != nil {
		err = fmt.Errorf("SyncPosDecode fail,err:%v,data:%s", err, str01)
		return item, nil
	}
	return
}

// ISaveSyncSeq save sync seq interface
type ISaveSyncSeq interface {
	HaveOldSyncSeq() bool
	SyncSeqWriter(posItem *SyncSeqItem, flushDisk bool) error
	GetLastSyncSeq() (latestPos SyncSeqItem, err error)
	GetSpecificTimeSyncSeq(time01 time.Time) (lastSeq SyncSeqItem, err error)
	Close() error
}

// SaveSyncSeqToFile TODO
// save redis-sync seq to local file
type SaveSyncSeqToFile struct {
	saveFile  string
	fileP     *os.File
	bufWriter *bufio.Writer
	logger    *zap.Logger
}

// NewSaveSyncSeqToFile new
func NewSaveSyncSeqToFile(saveFile string, logger *zap.Logger) (ret *SaveSyncSeqToFile, err error) {
	ret = &SaveSyncSeqToFile{}
	ret.logger = logger
	err = ret.SetSaveFile(saveFile)
	if err != nil {
		return nil, err
	}
	return
}

// SaveFile ..
func (f *SaveSyncSeqToFile) SaveFile() string {
	return f.saveFile
}

// SetSaveFile ..
func (f *SaveSyncSeqToFile) SetSaveFile(dstFile string) error {
	var err error
	err = f.Close()
	if err != nil {
		return err
	}
	if dstFile == "" {
		err = fmt.Errorf("saveFile(%s) cannot be empty", dstFile)
		f.logger.Error(err.Error())
		return err
	}
	f.saveFile = dstFile
	f.fileP, err = os.OpenFile(dstFile, os.O_APPEND|os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		err = fmt.Errorf("open file:%s fail,err:%v", dstFile, err)
		f.logger.Error(err.Error())
		return err
	}
	f.bufWriter = bufio.NewWriter(f.fileP)
	return nil
}

// HaveOldSyncSeq confirm that old sync seq exists
func (f *SaveSyncSeqToFile) HaveOldSyncSeq() bool {
	if f.saveFile == "" {
		return false
	}
	file01, err := os.Stat(f.saveFile)
	if err != nil && os.IsNotExist(err) == true {
		return false
	}
	if file01.Size() == 0 {
		return false
	}
	return true
}

// SyncSeqWriter syncSeq record to file
func (f *SaveSyncSeqToFile) SyncSeqWriter(seqItem *SyncSeqItem, flushDisk bool) error {
	line01 := seqItem.String()
	_, err := f.bufWriter.WriteString(line01 + "\n")
	if err != nil {
		f.logger.Error("write file fail", zap.Error(err),
			zap.String("line01", line01), zap.String("saveFile", f.saveFile))
		return err
	}
	if flushDisk == true {
		err = f.bufWriter.Flush()
		if err != nil {
			err = fmt.Errorf("bufio flush fail.err:%v,file:%s", err, f.saveFile)
			f.logger.Error(err.Error())
			return nil
		}
	}
	return nil
}

// GetLastSyncSeq get latest syncSeq
func (f *SaveSyncSeqToFile) GetLastSyncSeq() (lastSeq SyncSeqItem, err error) {
	f.bufWriter.Flush()
	tailCmd := fmt.Sprintf("tail -1 %s", f.saveFile)
	lastLine, err := util.RunLocalCmd("bash", []string{"-c", tailCmd}, "", nil, 30*time.Second, f.logger)
	if err != nil {
		return lastSeq, err
	}
	lastSeq, err = SyncSeqItemDecode(lastLine)
	if err != nil {
		f.logger.Error(err.Error())
		return lastSeq, err
	}
	return
}

// GetSpecificTimeSyncSeq get specific time sync seq
// 该函数会忽略time01 中'秒',只获取 time01 相同'分' 的第一条seq
func (f *SaveSyncSeqToFile) GetSpecificTimeSyncSeq(time01 time.Time) (lastSeq SyncSeqItem, err error) {
	f.bufWriter.Flush()
	layoutMin := "2006-01-02 15:04"
	timeStr := time01.Local().Format(layoutMin)
	grepCmd := fmt.Sprintf("grep -i %q %s| head -1", timeStr, f.saveFile)
	f.logger.Info("GetSpecificTimeSyncSeq " + grepCmd)

	firstLine, err := util.RunLocalCmd("bash", []string{"-c", grepCmd}, "", nil, 1*time.Minute, f.logger)
	if err != nil {
		return lastSeq, err
	}
	firstLine = strings.TrimSpace(firstLine)
	if firstLine == "" {
		f.logger.Warn(fmt.Sprintf("GetSpecificTimeSyncSeq not found %q seq record,file:%s", timeStr, f.saveFile))
		return lastSeq, util.NewNotFound()
	}
	lastSeq, err = SyncSeqItemDecode(firstLine)
	if err != nil {
		f.logger.Error(err.Error())
		return lastSeq, err
	}
	return
}

// Close file
func (f *SaveSyncSeqToFile) Close() error {
	var err error
	if f.saveFile == "" {
		return nil
	}
	f.saveFile = ""

	err = f.bufWriter.Flush()
	if err != nil {
		err = fmt.Errorf("bufio flush fail.err:%v,file:%s", err, f.saveFile)
		f.logger.Error(err.Error())
		return nil
	}
	err = f.fileP.Close()
	if err != nil {
		err = fmt.Errorf("file close fail.err:%v,file:%s", err, f.saveFile)
		f.logger.Error(err.Error())
		return nil
	}
	return nil
}
