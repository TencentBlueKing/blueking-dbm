package checksum

import (
	"fmt"
	"path/filepath"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

func NewRuntimeConfig(
	bkBizId, clusterId, port int,
	role, schedule, immuteDomain, ip, user, password, apiUrl, logDir string,
	runtimeHour int,
	tl *tools.ToolSet) *config.Config {
	cfg := config.Config{
		BkBizId: bkBizId,
		Cluster: config.Cluster{
			Id:           clusterId,
			ImmuteDomain: immuteDomain,
		},
		Host: config.Host{
			Ip:       ip,
			Port:     port,
			User:     user,
			Password: password,
		},
		InnerRole:  config.InnerRoleEnum(role),
		ReportPath: filepath.Join(cst.DBAReportBase, "checksum"),
		Slaves:     nil,
		Filter:     config.Filter{},
		PtChecksum: config.PtChecksum{
			Path:     tl.MustGet(tools.ToolPtTableChecksum),
			Switches: []string{},
			Args: []map[string]interface{}{
				{
					"name":  "run-time",
					"value": fmt.Sprintf("%dh", runtimeHour),
				},
			},
			Replicate: fmt.Sprintf("%s.checksum", native.INFODBA_SCHEMA),
		},
		Log: &config.LogConfig{
			Console:    false,
			LogFileDir: &logDir,
			Debug:      false,
			Source:     true,
			Json:       true,
		},
		Schedule: schedule,
		ApiUrl:   apiUrl,
	}

	return &cfg
}
