package mysqlutil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func TestDumpTogether(t *testing.T) {
	t.Log("start testing dump")
	var dumper mysqlutil.Dumper
	dumper = &mysqlutil.MySQLDumperTogether{
		MySQLDumper: mysqlutil.MySQLDumper{
			DumpDir:      "/data/",
			Ip:           "127.0.0.1",
			Port:         3306,
			DbBackupUser: "make",
			DbBackupPwd:  "make",
			DbNames:      []string{"bk-dbm", "test", "cmdb"},
			DumpCmdFile:  "/usr/local/mysql/bin/mysqldump",
			Charset:      "utf8",
			MySQLDumpOption: mysqlutil.MySQLDumpOption{
				// NoData:       true,
				AddDropTable: true,
				DumpRoutine:  true,
				DumpTrigger:  false,
			},
		},
		OutputfileName: "make.sql",
	}
	if err := dumper.Dump(); err != nil {
		t.Fatal("dump failed: ", err.Error())
	}
	t.Log("ending backup...")
}
