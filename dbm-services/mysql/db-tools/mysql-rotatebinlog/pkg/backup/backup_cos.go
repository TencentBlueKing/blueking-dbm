package backup

import (
	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/backupclient"
)

// COSBackupClient TODO
type COSBackupClient struct {
	ToolPath     string `mapstructure:"tool_path" json:"tool_path" validate:"required"`
	FileTag      string `mapstructure:"file_tag" json:"file_tag" validate:"required"`
	AuthFile     string `mapstructure:"auth_file" json:"auth_file"`
	backupClient *backupclient.BackupClient
}

// Init TODO
func (o *COSBackupClient) Init() error {
	if backupClient, err := backupclient.New(o.ToolPath, o.AuthFile, o.FileTag); err != nil {
		return err
	} else {
		o.backupClient = backupClient
	}
	return nil
}

// Upload TODO
func (o *COSBackupClient) Upload(fileName string) (string, error) {
	if o.backupClient == nil {
		return "-1", errors.New("COSBackupClient need init first")
	}
	return o.backupClient.Upload(fileName)
}

// Query TODO
func (o *COSBackupClient) Query(taskId string) (int, error) {
	return o.backupClient.Query(taskId)
}
