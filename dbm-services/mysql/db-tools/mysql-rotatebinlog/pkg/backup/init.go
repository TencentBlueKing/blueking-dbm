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
		if name == "bkbs" { // blueking backup system
			if !viper.GetBool("backup_client.bkbs.enable") {
				continue
			}
			var bkbsClient BKBackupClient
			if err := mapstructure.Decode(cfgClient, &bkbsClient); err != nil {
				return nil, err
			} else {
				backupClient = &bkbsClient
			}

		} else if name == "ibs" {
			if !viper.GetBool("backup_client.ibs.enable") {
				continue
			}
			var ibsClient IBSBackupClient
			if err := mapstructure.Decode(cfgClient, &ibsClient); err != nil {
				return nil, err
			} else {
				backupClient = &ibsClient
			}
		} else {
			logger.Error("unknown backup_client %s", name)
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
