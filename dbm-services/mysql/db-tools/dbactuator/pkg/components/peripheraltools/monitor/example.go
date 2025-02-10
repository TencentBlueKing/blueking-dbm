package monitor

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func (c *MySQLMonitorComp) Example() interface{} {
	return MySQLMonitorComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &MySQLMonitorParam{
			Medium: components.Medium{
				Pkg:    "mysql-monitor.tar.gz",
				PkgMd5: "12345",
			},
			SystemDbs: native.DBSys,
			ExecUser:  "whoru",
			ApiUrl:    `http://x.x.x.x:yyyy`,
			ItemsConfig: map[string]*config.MonitorItem{
				"character-consistency": {
					Name:        "",
					Enable:      nil,
					Schedule:    nil,
					MachineType: nil,
					Role:        nil,
				},
			},
			InstancesInfo: []*internal.InstanceInfo{
				{
					BkBizId:      1,
					Ip:           "127.0.0.1",
					Port:         123,
					Role:         "master",
					ClusterId:    12,
					ImmuteDomain: "aaa.bbb.com",
				},
			},
			MachineType: "backend",
			BkCloudId:   0,
		},
	}
}
