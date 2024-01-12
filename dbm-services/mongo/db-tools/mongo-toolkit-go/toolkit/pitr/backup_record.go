package pitr

// BackupRecord 备份记录，每次备份都会产生一个BackupRecord
type BackupRecord struct {
	// 文件所属
	BkBizId  string `json:"bk_biz_id"`
	App      string `json:"app"`      //
	Cluster  string `json:"cluster"`  //
	SetName  string `json:"set_name"` //
	Instance string `json:"instance"` //
	Ip       string `json:"ip"`
	Port     string `json:"port"`
	// 数据库类型
	BackupType string `json:"backup_type"` // MongoDB
	// FileInfo
	// 文件名
	FileName string `json:"filename"`
	// 文件大小
	FileSize int64 `json:"filesize"`
	// 文件最后修改时间
	FileLastMtime string `json:"file_last_mtime"`
	// 文件md5
	Md5 string `json:"md5"`
	// 任务ID
	FileLastTime     uint64 `json:"file_last_time"`  // 文件中的Oplog的最后时间 毫秒
	FileStartTime    uint64 `json:"file_start_time"` // 文件中的Oplog的开始时间 毫秒
	BackupSysTaskID  int64  `json:"task_id"`         // 0 未接入, -1 发起失败. >0 则是备份系统返回的I
	BackupSysTileTag string `json:"file_tag"`        // 上报备份系统用的Tag
}
