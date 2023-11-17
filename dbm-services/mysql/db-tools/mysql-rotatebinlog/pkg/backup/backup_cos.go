package backup

import (
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/backupclient"
)

// BKBackupClient TODO
type BKBackupClient struct {
	ToolPath     string `mapstructure:"tool_path" json:"tool_path" validate:"required"`
	FileTag      string `mapstructure:"file_tag" json:"file_tag" validate:"required"`
	AuthFile     string `mapstructure:"auth_file" json:"auth_file"`
	StorageType  string `mapstructure:"storage_type" json:"storage_type"`
	backupClient *backupclient.BackupClient
}

// Init TODO
func (o *BKBackupClient) Init() error {
	if backupClient, err := backupclient.New(o.ToolPath, o.AuthFile, o.FileTag, o.StorageType); err != nil {
		return err
	} else {
		o.backupClient = backupClient
	}
	return nil
}

// Upload TODO
func (o *BKBackupClient) Upload(fileName string) (string, error) {
	if o.backupClient == nil {
		return "-1", errors.New("BKBackupClient need init first")
	}
	return o.backupClient.Upload(fileName)
}

// Query TODO
func (o *BKBackupClient) Query(taskId string) (int, error) {
	return o.backupClient.Query(taskId)
}
