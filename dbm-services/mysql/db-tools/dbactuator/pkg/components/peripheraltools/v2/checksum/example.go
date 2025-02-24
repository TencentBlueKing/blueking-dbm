package checksum

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

func (c *MySQLChecksumComp) Example() interface{} {
	return MySQLChecksumComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &MySQLChecksumParam{
			SystemDbs:      native.DBSys,
			ExecUser:       "whoru",
			ApiUrl:         "http://x.x.x.x:yyyy",
			BkBizId:        0,
			IP:             "127.0.0.1",
			Ports:          []int{3306, 3307},
			Role:           "",
			ClusterId:      0,
			ImmuteDomain:   "",
			DBModuleId:     0,
			Schedule:       "0 5 2 * * * 1-5",
			StageDBHeader:  "stage_header",
			RollbackDBTail: "rollback",
		},
	}
}
