package backup

import (
	"dbm-services/common/go-pubpkg/logger"

	"github.com/mitchellh/mapstructure"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

// InitBackupClient init backup client
func InitBackupClient() (backupClient BackupClient, err error) {
	backupClients := viper.GetStringMap("backup_client")
	for name, cfgClient := range backupClients {
		if name == "ibs" && viper.GetBool("backup_client.ibs.enable") {
			var ibsClient IBSBackupClient
			if err := mapstructure.Decode(cfgClient, &ibsClient); err != nil {
				return nil, err
			} else {
				backupClient = &ibsClient
			}
		} else if name == "cos" && viper.GetBool("backup_client.cos.enable") {
			var ibsClient COSBackupClient
			if err := mapstructure.Decode(cfgClient, &ibsClient); err != nil {
				return nil, err
			} else {
				backupClient = &ibsClient
			}
		} else {
			logger.Warn("unknown backup_client", name)
			// return nil, errors.Errorf("unknown backup_client: %s", name)
		}
	}
	if backupClient == nil {
		logger.Warn("backup_client config failed")
	} else if err = backupClient.Init(); err != nil {
		backupClient = nil
		return nil, errors.Wrapf(err, "backup_client init failed: %+v", backupClient)
	}
	return backupClient, nil
}
