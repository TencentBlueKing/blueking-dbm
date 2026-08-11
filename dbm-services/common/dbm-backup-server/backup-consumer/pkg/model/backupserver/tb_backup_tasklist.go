package backupserver

import (
	"time"
)

// TbBackupTasklist 备份任务流水表
type TbBackupTasklist struct {
	Uptime        time.Time `gorm:"column:uptime;type:timestamp;not null;default:1970-01-02 00:00:01"`
	SourceIP      string    `gorm:"index:source_ip;index:ind_ip_mtime;column:source_ip;type:varchar(15);not null"`
	SourceOstype  string    `gorm:"column:source_ostype;type:varchar(7)"`
	ObjectName    string    `gorm:"column:object_name;type:varchar(1024)"`
	ObjectType    string    `gorm:"column:object_type;type:varchar(30)"`
	ObjectPath    string    `gorm:"column:object_path;type:varchar(1024)"`
	FilePath      string    `gorm:"index:source_ip;column:file_path;type:varchar(1024)"`
	FileName      string    `gorm:"index:file_name;index:file_name2;column:file_name;type:varchar(1024)"`
	FileLastMtime time.Time `gorm:"index:ind_ip_mtime;column:file_last_mtime;type:datetime"`
	Size          int64     `gorm:"column:size;type:bigint(20)"`
	Md5           string    `gorm:"column:md5;type:varchar(64)"`
	Speed         int       `gorm:"column:speed;type:int(11)"` // MB
	FileTag       string    `gorm:"index:file_tag;column:file_tag;type:varchar(128)"`
	CosTag        string    `gorm:"column:cos_tag;type:text" json:"cosTag"`
	//Location      string    `gorm:"column:Location;type:varchar(200)"`
	Etag string `gorm:"column:etag;type:varchar(100)"`
	// 备份状态 0-3是任务转换，4成功 5失败
	Status       int8      `gorm:"index:status;column:status;type:tinyint(128)"`
	StartTime    time.Time `gorm:"column:start_time;type:timestamp;not null;default:1970-01-02 00:00:01"`
	CompleteTime time.Time `gorm:"column:complete_time;type:timestamp;not null;default:1970-01-02 00:00:01"`
	ExpireTime   time.Time `gorm:"column:expire_time;type:timestamp;not null;default:1970-01-02 00:00:01"`
	RetryTimes   int       `gorm:"column:retry_times;type:int(11)"`
	BucketName   string    `gorm:"column:bucket_name;type:varchar(255);not null" `
	TaskID       string    `gorm:"primaryKey;column:task_id;type:varchar(64);not null"`
	// 备份的业务ID
	BkBizID int `gorm:"column:bk_biz_id;type:int(11);not null"`
	// 备份的云区域ID
	BkCloudID int `gorm:"column:bk_cloud_id;type:int(11);not null"`
}

// TableName get sql table name.获取数据库表名
func (m *TbBackupTasklist) TableName() string {
	return "tb_backup_tasklist"
}
