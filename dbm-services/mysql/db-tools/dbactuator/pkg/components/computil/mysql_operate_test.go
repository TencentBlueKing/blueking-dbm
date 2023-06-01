package computil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
)

func TestShutDownMySQLByNormal(t *testing.T) {
	p := computil.ShutdownMySQLParam{
		Socket:    "/data/mysql/3306/mysql.sock",
		MySQLUser: "make",
		MySQLPwd:  "make",
	}
	err := p.ShutdownMySQLBySocket()
	if err != nil {
		t.Fatal(err)
	}
	t.Log("shutdown succcess")
}

func TestForceShutDownMySQL(t *testing.T) {
	p := computil.ShutdownMySQLParam{
		Socket:    "/data/mysql/3306/mysql.sock",
		MySQLUser: "make",
		MySQLPwd:  "xxx",
	}
	err := p.ForceShutDownMySQL()
	if err != nil {
		t.Fatal(err)
	}
	t.Log("shutdown succcess")
}

func TestKillReMindMySQLClient(t *testing.T) {
	t.Log("start testing  TestKillReMindMySQLClient")
	err := computil.KillReMindMySQLClient("3306")
	if err != nil {
		t.Fatalf("kill mysql client failed %s", err.Error())
		return
	}
	t.Log("ending...")
}
