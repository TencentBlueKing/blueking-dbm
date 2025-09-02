package import_grants_file

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
)

func (c *ImportGrantsFile) Example() interface{} {
	return ImportGrantsFile{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
		Params: &ImportGrantsFileParam{
			SourceIp:      "1.1.1.1",
			SourceVersion: "5.7.20-tmysql-3.4.4-log",
			DestAddress:   "2.2.2.2:20000",
			Filename:      "source-grants.priv",
			IgnoreUsers:   []string{"u1", "u2", "u3"},
			MachineType:   "backend",
		},
	}
}
