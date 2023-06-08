package dbareport

// BackupStatus the status of backup
type BackupStatus struct {
	BackupId   string `json:"backup_id"`
	BillId     string `json:"bill_id"`
	ClusterId  string `json:"cluster_id"`
	Status     string `json:"status"`
	ReportTime string `json:"report_time"`
}
