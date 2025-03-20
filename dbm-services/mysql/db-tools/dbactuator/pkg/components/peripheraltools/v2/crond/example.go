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
			Ip:               "127.0.0.1",
			BkCloudId:        0,
			EventDataId:      123,
			EventDataToken:   "abc",
			MetricsDataId:    456,
			MetricsDataToken: "xyz",
			BeatPath:         "/a/bc",
			AgentAddress:     "127.0.0.1",
			BkBizId:          123,
		},
	}
}
