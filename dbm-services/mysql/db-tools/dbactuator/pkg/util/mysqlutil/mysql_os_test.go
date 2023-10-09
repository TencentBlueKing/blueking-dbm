package mysqlutil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func TestMySQLVersionParse(t *testing.T) {
	t.Log(" start mysql version Parse")
	ver := "mysql-5.6.24-linux-x86_64-tmysql-2.2.3-gcs.tar.gz"
	verNu := mysqlutil.MySQLVersionParse(ver)
	t.Logf("%s parse version is:%d", ver, verNu)
	ver_maria := "mariadb-10.3.7-linux-x86_64-tspider-3.7.6-gcs.tar.gz"
	verNu = mysqlutil.MySQLVersionParse(ver_maria)
	t.Logf("%s parse version is:%d", ver_maria, verNu)
}

func TestMajorVersion(t *testing.T) {
	t.Logf("major Version:%s", mysqlutil.GetMajorVersion(5006024))
}

func TestGenMysqlServerId(t *testing.T) {
	svrid, _ := mysqlutil.GenMysqlServerId("127.0.0.1", 3306)
	t.Logf("gen mysql server id:%d", svrid)
}
