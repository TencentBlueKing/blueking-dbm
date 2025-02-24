package monitor

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
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

			MachineType: "backend",
			BkCloudId:   0,
			PortBkInstanceList: []portBkInstancePair{
				{
					Port: 20000, BkInstanceId: 123,
				},
			},
			IP:           "127.0.0.1",
			Role:         "master",
			ImmuteDomain: "db.local",
			ClusterId:    123,
			DBModuleId:   234,
		},
	}
}
