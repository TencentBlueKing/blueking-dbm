package backupclient

import (
	"time"
)

// TaskObject object in redis queue
type TaskObject struct {
	TaskID string `gorm:"primaryKey;column:task_id;type:varchar(64);not null" json:"task_id" db:"task_id"`
	StorageObject
	// Status 文件上传状态, ref cst.FileStatus
	Status       int       `gorm:"column:status;type:tinyint(128)" json:"status" db:"status"`
	Uptime       time.Time `gorm:"index:Uptime;index:file_tag;index:file_name2;column:uptime;type:timestamp;not null;default:'1970-01-02 00:00:01'" json:"uptime" db:"uptime"`
	StartTime    time.Time `gorm:"column:start_time;type:timestamp;not null;default:'1970-01-02 00:00:01'" json:"start_time" db:"start_time"`
	CompleteTime time.Time `gorm:"column:complete_time;type:timestamp;not null;default:'1970-01-02 00:00:01'" json:"complete_time" db:"complete_time"`
	Speed        string    `gorm:"-" json:"speed"` // object upload limit
	ChunkSize    string    `gorm:"-" json:"chunk_size"`
	// Retries upload retries
	Retries int `gorm:"column:retries" db:"retries" json:"retries"`
}

// StorageObject TODO
type StorageObject struct {
	SourceIP     string `gorm:"column:source_ip;type:varchar(15);not null" json:"source_ip" db:"source_ip" validate:"required"`
	BkBizId      int    `gorm:"column:bk_biz_id;type:int;not null" json:"bk_biz_id" db:"bk_biz_id" validate:"required"`
	BkCloudId    int    `gorm:"column:bk_cloud_id;type:int;not null" json:"bk_cloud_id" db:"bk_cloud_id" validate:"required"`
	BucketName   string `gorm:"column:bucket_name;type:varchar(127);not null" db:"bucket_name" json:"bucket_name"`
	SourceOstype string `gorm:"column:source_ostype;type:varchar(7)" json:"source_ostype" db:"source_ostype" validate:"required"`
	// 对象名称
	ObjectName string `gorm:"column:object_name;type:varchar(1024)" json:"object_name" db:"object_name" validate:"required"`
	// 两种，之时对象名称是文件还是文件夹
	ObjectType string `gorm:"column:object_type;type:varchar(30)" json:"object_type" db:"object_type" validate:"required"`
	// 对象的路径
	ObjectPath string `gorm:"column:object_path;type:varchar(1024)" db:"object_path" json:"object_path"`
	// 文件绝对路径
	FilePath string `gorm:"column:file_path;type:varchar(1024)" db:"file_path" json:"file_path"`
	// 文件名称
	FileName  string    `gorm:"column:file_name;type:varchar(1024)" db:"file_name" json:"file_name"`
	FileMtime time.Time `gorm:"index:ind_ip_mtime;column:file_mtime;type:timestamp;not null;default:'1970-01-02 00:00:01'" db:"file_mtime" json:"file_mtime"`
	// 文件大小
	FileSize string `gorm:"column:file_size;type:bigint(20)" db:"file_size" json:"file_size"`
	// 文件MD5值
	FileMD5 string `gorm:"column:file_md5;type:varchar(64)" db:"file_md5" json:"file_md5"`
	// 文件保留天数tag
	FileTag string `gorm:"column:file_tag;type:varchar(128)" db:"file_tag" json:"file_tag"`
	// 对象标签，做页面分类查找用
	CosTag       string `gorm:"column:cos_tag;type:text" db:"cos_tag" json:"cos_tag"`
	RegisterUser string `gorm:"column:register_user;type;varchar" db:"register_user" json:"register_user"`
}
