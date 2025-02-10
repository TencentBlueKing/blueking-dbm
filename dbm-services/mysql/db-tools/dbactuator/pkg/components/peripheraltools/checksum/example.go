package checksum

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/internal"
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
			Medium: components.Medium{
				Pkg:    "mysql-table-checksum.tar.gz",
				PkgMd5: "12345",
			},
			SystemDbs: native.DBSys,
			ExecUser:  "whoru",
			ApiUrl:    "http://x.x.x.x:yyyy",
			InstancesInfo: []*instanceInfo{
				{
					internal.InstanceInfo{
						BkBizId:      0,
						Ip:           "",
						Port:         0,
						Role:         "",
						ClusterId:    0,
						ImmuteDomain: "",
						BkInstanceId: 0,
						DBModuleId:   0,
					},
					"",
				},
			},
			StageDBHeader:  "stage_header",
			RollbackDBTail: "rollback",
		},
	}
}
