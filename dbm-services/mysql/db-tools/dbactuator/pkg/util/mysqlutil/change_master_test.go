package mysqlutil

import (
	"testing"

	. "github.com/smartystreets/goconvey/convey"
)

func TestChangeMasterParseSQL(t *testing.T) {
	Convey("Parse change master sql", func() {
		changeSQL1 := "-- CHANGE MASTER TO MASTER_LOG_FILE='binlog20000.004450', MASTER_LOG_POS=63779;"
		cm1 := ChangeMaster{ChangeSQL: changeSQL1}
		cm1.ParseChangeSQL()
		So("binlog20000.004450", ShouldEqual, cm1.MasterLogFile)
		So(63779, ShouldEqual, cm1.MasterLogPos)

		changeSQL2 := "change master to master_log_file='xxx.100', master_log_pos = 123, master_host= \"1.1.1.1\", master_port =3306"
		cm2 := ChangeMaster{ChangeSQL: changeSQL2}
		cm2.ParseChangeSQL()
		So("1.1.1.1", ShouldEqual, cm2.MasterHost)
		So(3306, ShouldEqual, cm2.MasterPort)
	})
}
