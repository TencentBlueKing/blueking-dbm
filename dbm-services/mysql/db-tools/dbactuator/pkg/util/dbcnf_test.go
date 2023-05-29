package util_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

func TestGetMySQLDatadir(t *testing.T) {
	t.Log("start")
	c, err := util.LoadMyCnfForFile("/etc/my.cnf.20000")
	if err != nil {
		t.Fatal(err)
	}
	datadir, err := c.GetMySQLDataDir()
	if err != nil {
		t.Fatal(err)
	}
	t.Log("datadir path:", datadir)
	logdir, err := c.GetMySQLLogDir()
	if err != nil {
		t.Fatal(err)
	}
	t.Log("logdir path:", logdir)
}
