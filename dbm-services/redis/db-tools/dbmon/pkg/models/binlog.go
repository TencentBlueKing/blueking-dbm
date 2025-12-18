package models

import (
	"regexp"
	"strconv"
	"time"
)

// RedisBinlogHistorySchema TODO
type RedisBinlogHistorySchema struct {
	ID         int64  `json:"-" gorm:"primaryKey;column:id;not null`
	ReportType string `json:"report_type" gorm:"type:varchar(64);column:report_type;not null;default:''"`
	BkBizID    string `json:"bk_biz_id" gorm:"type:varchar(64);column:bk_biz_id;not null;default:''"`
	BkCloudID  int64  `json:"bk_cloud_id" gorm:"column:bk_cloud_id;not null;default:0"`
	ServerIP   string `json:"server_ip" gorm:"type:varchar(128);column:server_ip;not null;default:''"`
	ServerPort int    `json:"server_port" gorm:"column:server_port;not null;default:0"`
	Domain     string `json:"domain" gorm:"type:varchar(128);column:domain;not null;default:'';index"`
	// TendisplusInstance or TendisSSDInstance
	DbType   string `json:"db_type" gorm:"type:varchar(64);column:db_type;not null;default:''"`
	RealRole string `json:"role" gorm:"type:varchar(64);column:role;not null;default:''"`
	// 备份路径,如 /data/dbbak/binlog/30000
	BackupDir string `json:"backup_dir" gorm:"column:backup_dir;not null;default:''"`
	// 备份的目标文件(已压缩)
	BackupFile string `json:"backup_file" gorm:"column:backup_file;not null;default:''"`
	// binlog对应的 kvstoreidx
	KvstoreIdx int `json:"kvstoreidx" gorm:"column:kvstoreidx;not null;default:0"`
	// 备份文件大小(已压缩)
	BackupFileSize int64 `json:"backup_file_size" gorm:"column:backup_file_size;not null;default:0"`
	// binlog文件生成时间(非压缩)
	StartTime time.Time `json:"start_time" gorm:"column:start_time;not null;default:'';index"`
	// binlog文件最后修改时间(非压缩)
	EndTime      time.Time `json:"end_time" gorm:"column:end_time;not null;default:'';index"`
	TimeZone     string    `json:"time_zone" gorm:"type:varchar(64);column:time_zone;not null;default:''"`
	BackupTaskID string    `json:"backup_taskid" gorm:"type:varchar(128);column:backup_taskid;not null;default:''"`
	// 目前为空
	BackupMD5 string `json:"backup_md5" gorm:"type:varchar(128);column:backup_md5;not null;default:''"`
	// REDIS_BINLOG
	BackupTag string `json:"backup_tag" gorm:"type:varchar(128);column:backup_tag;not null;default:''"`
	// shard值
	ShardValue string `json:"shard_value" gorm:"type:varchar(128);column:shard_value;not null;default:''"`
	Status     string `json:"status" gorm:"type:varchar(128);column:status;not null;default:''"`
	Message    string `json:"message" gorm:"column:message;not null;default:''"`
	// 本地文件是否已删除,未被删除为0,已被删除为1
	LocalFileRemoved int `json:"-" gorm:"column:local_file_removed;not null;default:0"`
}

// tendisssd binlog文件正则
// 例如: binlog-30000-0007426-20221109221541.log
// tendisplus binlog文件正则
// 例如: binlog-0-0000887-20221107123830.log
var TendisBinlogReg = regexp.MustCompile(`binlog-(\d+)-(\d+)-(\d+).log`)

// TableName TODO
func (r *RedisBinlogHistorySchema) TableName() string {
	return "redis_binlog_history"
}

// Addr string
func (r *RedisBinlogHistorySchema) Addr() string {
	return r.ServerIP + ":" + strconv.Itoa(r.ServerPort)
}
