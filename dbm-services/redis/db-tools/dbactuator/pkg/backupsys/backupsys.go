// Package backupsys 备份系统
package backupsys

// DstIPBackupUser TODO
var DstIPBackupUser string

// DstIPBackupPassword TODO
var DstIPBackupPassword string

// BackupURL TODO
var BackupURL string

// BackupSysID TODO
var BackupSysID string

// BackupKey TODO
var BackupKey string

// IBSBaseInfo godoc
type IBSBaseInfo struct {
	// 备份系统 api url 地址，会在后面拼接 /query /recover 后缀进行请求
	Url string `json:"url" validate:"required" example:"http://127.0.0.x/backupApi" env:"IBS_INFO_url" envDefault:"http://127.0.0.x/backupApi"`
	// application标识，亦即哪个系统需要访问本接口，可从环境变量获取 IBS_INFO_sys_id
	SysID string `json:"sys_id" validate:"required" env:"IBS_INFO_sys_id"`
	// 16位字串，由备份系统分配，可从环境变量获取 IBS_INFO__key
	Key string `json:"key" validate:"required" env:"IBS_INFO_key,unset"`
	// OA验证的ticket，一个长串，通常附加在访问内网应用的URL上，主要用来验证用户身份，可以留空
	Ticket string `json:"ticket"`
}

// SetUserPassword for  rollback
func SetUserPassword(user, password string) {
	DstIPBackupUser = user
	DstIPBackupPassword = password
}

// SetIBSBaseInfo for  backupsys
func SetIBSBaseInfo(url, sysId, key string) {
	BackupURL = url
	BackupSysID = sysId
	BackupKey = key
}
