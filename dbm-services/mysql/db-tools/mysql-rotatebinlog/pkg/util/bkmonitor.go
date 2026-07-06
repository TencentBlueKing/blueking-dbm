package util

import (
	"github.com/spf13/viper"

	ma "dbm-services/mysql/db-tools/mysql-crond/api"
)

// SendMonitorMetrics TODO
func SendMonitorMetrics(name string, value int64, dimensions map[string]interface{}) error {
	crondManager := ma.NewManager(viper.GetString("crond.api_url"))

	err := crondManager.SendMetrics(
		name,
		value,
		dimensions,
	)
	if err != nil {
		return err
	}
	return nil
}
