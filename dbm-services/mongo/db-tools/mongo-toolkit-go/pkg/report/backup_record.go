package report

import (
	"dbm-services/mongo/db-tools/dbmon/config"
)

// BackupRecord 包括
// 备份文件本身的内容 Name, Size
// 关联实例的维度信息
// 备份系统中的关联信息 TaskId,是否已完成
// 发起备份关联信息
// 来自单据. 1. ReleateBillId, ReleateBillInfo:一个打包的Json
// 来自日常备份:
type BackupRecord struct {
	config.BkDbmLabel
	ReportType string `json:"report_type"` // mongo_backup_result 日志平台
	// File Info
	StartTime string `json:"start_time"` // 备份起始时间，格式为"2023-12-27T13:00:15+08:00"
	EndTime   string `json:"end_time"`   // 备份结束时间，格式为"2023-12-27T13:00:15+08:00"
	FilePath  string `json:"file_path"`  // 文件路径
	FileName  string `json:"file_name"`  //
	FileSize  int64  `json:"file_size"`  //
	FileMd5   string `json:"-"`          //
	// BackupSys Info
	BsTaskID string `json:"bs_taskid"` // 关联的备份系统的TaskId
	BsTag    string `json:"bs_tag"`    // 关联的备份系统的Tag MONGO_INCR_BACKUP MONGO_FULL_BACKUP
	BsStatus string `json:"bs_status"` // to_backup_system_start | to_backup_system_sucess | error
	// Releate Req
	Src string `json:"src"` // daily 日常备份. bill: 来自单据的需求
	// if src == daily
	PitrFullname    string `json:"pitr_fullname"`     // 全备UniqId src == daily时有值
	PitrDate        string `json:"pitr_date"`         // 一般一天只有一个全备.
	PitrFileType    string `json:"pitr_file_type"`    // full or incr
	PitrBinlogIndex uint32 `json:"pitr_binlog_index"` // 增量备份的index，是一个递增数字
	PitrLastPos     uint32 `json:"pitr_last_pos"`     // UnixTime. binlog_last_time. src == daily时有值
	// if src == bill
	ReleateBillId   string `json:"releate_bill_id"`   //
	TotalFileNum    int    `json:"total_file_num"`    //
	MyFileNum       int    `json:"my_file_num"`       //
	ReleateBillInfo string `json:"releate_bill_info"` // 关联的Bill的内容，是一个Json数据.
}

// NewBackupRecord new backup record
func NewBackupRecord() *BackupRecord {
	return &BackupRecord{}
}

// AppendFileInfo add file info
func (b *BackupRecord) AppendFileInfo(startTime, endTime string, filePath, fileName string, fileSize int64) error {
	b.FilePath = filePath
	b.StartTime = startTime
	b.EndTime = endTime
	b.FileName = fileName
	b.FileSize = fileSize
	return nil
}

// AppendMetaLabel 追加元数据，如果meta == nil，不追加
func (b *BackupRecord) AppendMetaLabel(meta *config.BkDbmLabel) error {
	if meta == nil {
		return nil
	}
	b.BkDbmLabel = *meta
	return nil
}

// AppendBsInfo append backup system info
func (b *BackupRecord) AppendBsInfo(taskId, tag string) {
	b.BsTaskID = taskId
	b.BsTag = tag
}

// AppendBillSrc append bill src info
func (b *BackupRecord) AppendBillSrc(billId, releateBillInfo string, totalFileNum, myFileIdx int) error {
	b.Src = "bill"
	b.ReleateBillId = billId
	b.ReleateBillInfo = releateBillInfo
	b.TotalFileNum = totalFileNum
	b.MyFileNum = myFileIdx
	return nil
}

// AppendDailySrc append daily src info
func (b *BackupRecord) AppendDailySrc(pitrName, pitrDate, pitrFileType string, pitrBinlogIndex, pitrLastPos uint32) error {
	b.Src = "daily"
	b.PitrFullname = pitrName
	b.PitrDate = pitrDate
	b.PitrFileType = pitrFileType
	b.PitrBinlogIndex = pitrBinlogIndex
	b.PitrLastPos = pitrLastPos
	return nil
}
