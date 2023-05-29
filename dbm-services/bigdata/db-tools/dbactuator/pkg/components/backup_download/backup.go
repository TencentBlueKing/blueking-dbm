package backup_download

// DownloadFile TODO
type DownloadFile interface {
	Init() error
	PreCheck() error
	Start() error
	Pause() error
	Stop() error
	Resume() error
	Rollback() error
	GetStatus() error
	GetAction() error
}

// DFBase TODO
type DFBase struct {
	BKBizID int `json:"bk_biz_id"`
	// 单文件下载限速,单位 MB/s
	BWLimitMB int64 `json:"bwlimit_mb"`
	// 并发下载数
	Concurrency int `json:"max_concurrency"` // @todo 同时下载最大并发
}
