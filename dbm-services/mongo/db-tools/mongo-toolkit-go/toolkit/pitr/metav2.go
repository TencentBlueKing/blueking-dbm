package pitr

import (
	"bufio"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/backupsys"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/disk"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"strconv"
	"strings"
	"time"

	log "github.com/sirupsen/logrus"
)

// BackupMetaV2 保存最近15天或者备份记录
// 将Full和Incr的备份合在一起记录.

// BackupMetaV2 the BackupMetaV2。 暂时不用
type BackupMetaV2 struct {
	MetaDir  string             `json:"meta_dir"`
	ConnInfo *mymongo.MongoHost `json:"connInfo"`
	Records  []BackupFileName   `json:"records"`
}

// getDiskUsage 获取磁盘使用率
func getDiskUsage(path string) (diskUsage int, err error) {
	diskInfo, err := disk.GetInfo(path)
	if err != nil {
		return
	}
	diskUsage = int(diskInfo.Used * 100 / diskInfo.Total)
	return
}

const disStateEmergency = "emergency"
const disStateWarning = "warning"
const disStateNormal = "normal"

func getDiskState(path string) (state string, err error) {
	diskUsage, err := getDiskUsage(path)
	if err != nil {
		return
	}
	if diskUsage > MaxDiskUsage {
		state = disStateEmergency
	} else if diskUsage < MinDiskUsage {
		state = disStateNormal
	} else {
		state = disStateWarning
	}
	return

}

const MaxSaveTime = time.Hour * 24 * 2
const MaxDiskUsage = 50 // 高于此值为磁盘紧急状态
const MinDiskUsage = 25 // 低于此值为磁盘正常状态

type deleteReasonFlag uint8

const deleteReasonFlagNone deleteReasonFlag = 0
const deleteReasonFlagTrue deleteReasonFlag = 1
const deleteReasonFlagFalse deleteReasonFlag = 2

type deleteReason struct {
	Flag   deleteReasonFlag `json:"flag"`
	Reason string           `json:"reason"`
}

func (d deleteReason) String() string {
	return fmt.Sprintf("%s:%t", d.Reason, d.Flag)
}

// RemoveOldFileFirst 删除过期的备份文件
// 磁盘紧急状态: >  MaxDiskUsage 50 -> 同步完成就删除
// 磁盘正常状态: < MinDiskUsage 25  -> 超过2天的文件且同步完成就删除
func (b *BackupMetaV2) RemoveOldFileFirst() {
	b.Load()
	log.Infof("RemoveOldFileFirst. start")
	var total, deleted int
	total = len(b.Records)
	for _, r := range b.Records {
		fullPath, taskInfo, doDelete, _ := canDelete(b.MetaDir, &r)
		if doDelete {
			deleted += 1
			doRemoveFile(fullPath)
			doRemoveInfoFile(&r, taskInfo)
		}
	}
	log.Infof("RemoveOldFileFirst done. total: %d, deleted: %d", total, deleted)
}

// needDelete 是否需要删除
func canDelete(metaDir string, r *BackupFileName) (fullPath string, taskInfo *backupsys.TaskInfo, doDelete bool, err error) {
	// 紧急状态，备份完了就删除
	// 正常状态，超过2天的文件，且备份完了就删除
	// deleteReasonFlagNone 是指没有taskinfo的文件，无法判断是否已经备份完成. 在紧急状态下，会直接删除
	// 是否已经备份完成
	doDelete = false
	fullPath = path.Join(metaDir, r.FileName)
	fileInfo, err := os.Stat(fullPath)
	if err != nil {
		err = nil // 文件不存在，不需要删除. 这是正常情况
		return
	}
	taskInfo, _ = backupsys.LoadInfoFile(fullPath)
	// 是否已经备份完成
	taskDoneReason := getTaskDoneReason(fullPath, taskInfo)
	modTimeReason := getModTimeReason(fileInfo, r)
	diskState, err := getDiskState(fullPath)
	if err != nil {
		// 如果获取磁盘状态失败，这是异常情况。退出
		log.Fatalf("RemoveOldFileFirst getDiskState failed, file: %s, err: %v", r.FileName, err)
	}
	// 紧急状态，备份完了就删除
	// 正常状态，超过2天的文件，且备份完了就删除
	// deleteReasonFlagNone 是指没有taskinfo的文件，无法判断是否已经备份完成. 在紧急状态下，会直接删除
	switch diskState {
	case disStateEmergency:
		if taskDoneReason.Flag == deleteReasonFlagTrue || taskDoneReason.Flag == deleteReasonFlagNone {
			doDelete = true
		}
	case disStateNormal:
		if modTimeReason.Flag == deleteReasonFlagTrue && taskDoneReason.Flag == deleteReasonFlagTrue {
			doDelete = true
		}
	}
	log.Printf("RemoveOldFileFirst, file: %s, diskState: %s reason: %s %s, doDelete: %v",
		r.FileName, diskState, taskDoneReason, modTimeReason, doDelete)
	return
}

// getTaskDoneReason 是否已经备份完成
func getTaskDoneReason(fullPath string, taskInfo *backupsys.TaskInfo) *deleteReason {
	taskDoneReason := deleteReason{Flag: deleteReasonFlagNone, Reason: "taskDone"}
	if taskInfo == nil {
		log.Warnf("RemoveOldFileFirst Get InfoFile failed. file: %s", fullPath)
	} else if taskInfo.Status == backupsys.TaskStatusDone {
		taskDoneReason.Flag = deleteReasonFlagTrue
	} else {
		backupInfo, err := backupsys.GetTaskInfo(taskInfo.TaskId)
		log.Printf("RemoveOldFileFirst TaskId %s TaskInfo %+v err %v", taskInfo.TaskId, backupInfo, err)
		if backupInfo == nil {
			log.Warnf("RemoveOldFileFirst %s, err : %v", fullPath, err)
		} else if backupInfo.Status == backupsys.TaskStatusDone {
			taskDoneReason.Flag = deleteReasonFlagTrue
			backupInfo.SaveToFile()
		}
	}
	return &taskDoneReason
}

// getModTimeReason 按照文件的修改时间判断是否可以删除.
func getModTimeReason(fileInfo os.FileInfo, r *BackupFileName) *deleteReason {
	modTimeReason := deleteReason{Flag: deleteReasonFlagNone, Reason: "mTime"}
	if fileInfo.ModTime().Before(time.Now().Add(-MaxSaveTime)) {
		modTimeReason.Flag = deleteReasonFlagTrue
	} else {
		modTimeReason.Flag = deleteReasonFlagFalse
	}
	return &modTimeReason
}

func doRemoveFile(filePath string) {
	if err := os.Remove(filePath); err == nil {
		log.Printf("RemoveOldFileFirst remove file succ, file: %q ", filePath)
	} else {
		log.Printf("RemoveOldFileFirst remove file failed, file:%s err:%v", filePath, err)
	}
}

func doRemoveInfoFile(r *BackupFileName, taskInfo *backupsys.TaskInfo) {
	var err error
	if taskInfo == nil {
		log.Warnf("RemoveOldFileFirst Get InfoFile failed. file: %s", r.FileName)
	} else {
		if err = os.Remove(taskInfo.GetInfoFilePath()); err == nil {
			log.Printf("RemoveOldFileFirst remove file succ file: %s backupFile: %s",
				taskInfo.GetInfoFilePath(), taskInfo.FilePath)
		} else {
			log.Printf("RemoveOldFileFirst remove file failed file: %s backupFile: %s err:%v",
				taskInfo.GetInfoFilePath(), taskInfo.FilePath, err)
		}
	}
}

// NewBackupMetaV2 创建一个新的BackupMetaV2
func NewBackupMetaV2(dir string, conn *mymongo.MongoHost) (*BackupMetaV2, error) {
	m := new(BackupMetaV2)
	m.MetaDir = dir
	m.ConnInfo = new(mymongo.MongoHost)
	*m.ConnInfo = *conn

	if false == TestFileWriteable(m.GetMetaFileName()) {
		return nil, fmt.Errorf("write %s err", m.GetMetaFileName())
	}
	return m, nil
}

// GetMetaFileName 获取meta文件名
func (b *BackupMetaV2) GetMetaFileName() string {
	MetaFileName := fmt.Sprintf("meta.%s-%s.json", b.ConnInfo.Host, b.ConnInfo.Port)
	return path.Join(b.MetaDir, MetaFileName)
}

func parseUint32(s string) (uint32, error) {
	v, err := strconv.ParseUint(s, 10, 32)
	return uint32(v), err

}
func splitTs(ts string) (*TS, error) {
	fs := strings.Split(ts, "|")
	if len(fs) != 2 {
		return nil, fmt.Errorf("splitTs failed, ts: %s", ts)
	}
	ts1, err := parseUint32(fs[0])
	if err != nil {
		return nil, fmt.Errorf("splitTs failed, ts: %s, err: %v", ts, err)
	}
	ts2, err := parseUint32(fs[1])
	if err != nil {
		return nil, fmt.Errorf("splitTs failed, ts: %s, err: %v", ts, err)
	}
	return &TS{ts1, ts2}, nil
}

func parseOplogPosLine(line string) (row *BackupFileName, err error) {
	fs := strings.Fields(line)
	if len(fs) != 3 {
		err = fmt.Errorf("parseOplogPosLine failed, line: %s", line)
		return
	}

	row, err = DecodeFilename(fs[0])
	if err != nil {
		log.Warnf("LoadOplogPos %s format err", line)
		return nil, err
	}

	if startTs, err := splitTs(fs[1]); err == nil {
		row.FirstTs = *startTs
	} else {
		log.Warnf("LoadOplogPos %s format err", line)
		return nil, err
	}

	if endTs, err := splitTs(fs[2]); err == nil {
		row.LastTs = *endTs
	} else {
		log.Warnf("LoadOplogPos %s format err", line)
		return nil, err
	}

	return
}

// LoadOplogPos 加载gcs的oplog.pos文件。 这个文件和meta文件是冲突的. 但为了兼容，继续写一段时间.
// tail  /data/mongolog/27000/oplog.pos
func LoadOplogPos(oplogPosFile string) (rows []BackupFileName, err error) {

	file, err := os.Open(oplogPosFile)
	if err != nil {
		log.Warnf("LoadOplogPos open %s failed, err: %v", oplogPosFile, err)
		return nil, err
	}

	var scanner = bufio.NewScanner(file)
	defer file.Close()
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		line := scanner.Text()
		row, err := parseOplogPosLine(line)
		if err != nil {
			log.Warnf("LoadOplogPos %q format err %v", line, err)
			continue
		}
		rows = append(rows, *row)
	}
	return
}

// Load 加载meta文件
func (b *BackupMetaV2) Load() error {
	contentByte, err := os.ReadFile(b.GetMetaFileName())
	if err != nil {
		contentByte = []byte(`{}`)
	}
	if err := json.Unmarshal(contentByte, b); err != nil {
		return err
	}
	return nil
}

// GetLastFull 获取最近的Full备份
func (b *BackupMetaV2) GetLastFull() (*BackupFileName, error) {
	b.Load()

	for i := len(b.Records) - 1; i >= 0; i-- {
		if b.Records[i].Type == BackupTypeFull {
			return &b.Records[i], nil
		}
	}

	// 找不到Full Backup
	return nil, nil
}

// GetLastIncr 获取最近的增量备份
func (b *BackupMetaV2) GetLastIncr(full *BackupFileName) (*BackupFileName, error) {
	b.Load()
	for i := len(b.Records) - 1; i >= 0; i-- {
		if b.Records[i].V0FullStr == full.V0FullStr {
			return &b.Records[i], nil
		}
	}

	// 找不到Full Backup
	return nil, nil
}

// GetLastBackup 获取最近的备份
func (b *BackupMetaV2) GetLastBackup() (*BackupFileName, *BackupFileName, error) {
	b.Load()
	// 如果当前记录为0，尝试加载oplog.pos文件中的内容，后面写入时，也会将Gcs的oplog.pos文件写入meta文件中
	oplogPath := path.Join("/data/mongolog/", b.ConnInfo.Port, "oplog.pos")
	oplogFileExists, _ := FileExists(oplogPath)
	if oplogFileExists && len(b.Records) == 0 {
		gcsRecords, err := LoadOplogPos(oplogPath)
		log.Infof("LoadOplogPos return %d records, err: %v", len(gcsRecords), err)
		if err == nil {
			b.Records = append(b.Records, gcsRecords...)
		}
	}

	var full *BackupFileName
	var incr *BackupFileName
	for i := len(b.Records) - 1; i >= 0; i-- {
		if b.Records[i].Type == BackupTypeFull {
			full = &b.Records[i]
			break
		}
	}

	// 找不到Full Backup
	if full == nil {
		return nil, nil, nil
	}

	for i := len(b.Records) - 1; i >= 0; i-- {
		if b.Records[i].V0FullStr == full.V0FullStr && b.Records[i].Type == BackupTypeIncr {
			incr = &b.Records[i]
			break
		}
	}

	// 找不到Full Backup
	return full, incr, nil
}

// Append 将备份结果追加到文件中. 只保留最近2000条记录
func (b *BackupMetaV2) Append(result *BackupFileName) error {
	metaPath := b.GetMetaFileName()
	b.Records = append(b.Records, *result)
	if len(b.Records) > 1000 {
		b.Records = b.Records[len(b.Records)-1000:]
	}

	contentBytes, err := json.Marshal(b)
	// log.Infof("metaPath: %s %s", metaPath, contentBytes)
	if err == nil {
		err = os.WriteFile(metaPath, contentBytes, 0644)
	}

	gcsOpLogPosFile := path.Join("/data/mongolog/", b.ConnInfo.Port, "oplog.pos")
	warnErr := SaveToGcsOpLogFile(gcsOpLogPosFile, result)
	log.Infof("SaveToGcsOpLogFile %s err: %v", gcsOpLogPosFile, warnErr)

	return err

}

// SaveToGcsOpLogFile 将OpLogPos写入到gcs的oplog.pos文件中，是为了准备回退为旧的备份工具
func SaveToGcsOpLogFile(filePath string, result *BackupFileName) error {
	file, err := os.OpenFile(filePath, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0666)
	if err != nil {
		log.Errorf("open %s failed, err: %v", filePath, err)
		return err
	}
	//及时关闭file句柄
	defer file.Close()
	//写入文件时，使用带缓存的 *Writer
	write := bufio.NewWriter(file)
	_, err = write.WriteString(fmt.Sprintf("%s %d|%d %d|%d\n", result.FileName,
		result.FirstTs.Sec, result.FirstTs.I, result.LastTs.Sec, result.LastTs.I))
	if err != err {
		return err
	}
	//Flush将缓存的文件真正写入到文件中
	return write.Flush()
}
