package rotatebinlog

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
	"encoding/json"
	"path/filepath"
)

func (c *MySQLRotateBinlogComp) Example() interface{} {
	ibsExample := `{
	"enable": true,
	"ibs_mode": "hdfs",
	"with_md5": true,
	"file_tag": "INCREMENT_BACKUP",
	"tool_path": "backup_client"
}`
	return MySQLRotateBinlogComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: MySQLRotateBinlogParam{
			Configs: rotate.Config{
				Public: rotate.PublicCfg{
					KeepPolicy:         "most",
					MaxBinlogTotalSize: "200g",
					MaxDiskUsedPct:     80,
					MaxKeepDuration:    "61d",
					PurgeInterval:      "4h",
					RotateInterval:     "10m",
					BackupEnable:       "false",
				},
				Crond: rotate.ScheduleCfg{
					Schedule: "*/10 * * * *",
					ApiUrl:   "http://127.0.0.1:9999",
					ItemName: "mysql-rotatebinlog",
				},
				Servers: nil,
				Report: rotate.ReportCfg{
					Enable:     true,
					Filepath:   filepath.Join(cst.DBAReportBase, "mysql/binlog"),
					LogMaxsize: 5, LogMaxbackups: 10, LogMaxage: 30,
				},
				Encrypt: rotate.EncryptCfg{Enable: false},
				BackupClient: map[string]interface{}{
					"ibs": json.RawMessage(ibsExample),
				},
			},
			IP:            "127.0.0.1",
			Ports:         []int{20000, 20001},
			Role:          "master",
			BkBizId:       1,
			ClusterDomain: "cluster.local",
			ClusterId:     123,
			ExecUser:      "sys",
		},
	}
}
