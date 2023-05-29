// Package backup TODO
package backup

// BackupClient TODO
type BackupClient interface {
	Init() error
	Upload(fileName string) (string, error)
	Query(taskId string) (int, error)
}
