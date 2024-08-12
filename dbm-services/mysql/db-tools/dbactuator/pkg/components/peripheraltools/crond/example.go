package crond

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
)

func (c *MySQLCrondComp) Example() interface{} {
	return MySQLCrondComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &MySQLCrondParam{
			Medium: components.Medium{
				Pkg:    "mysql-crond.tar.gz",
				PkgMd5: "12345",
			},
			Ip:               "127.0.0.1",
			BkCloudId:        0,
			EventDataId:      123,
			EventDataToken:   "abc",
			MetricsDataId:    456,
			MetricsDataToken: "xyz",
		},
	}
}
