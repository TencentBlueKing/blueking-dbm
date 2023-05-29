package native_test

import (
	"testing"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"

	"github.com/jmoiron/sqlx"
)

func TestConnByTcp(t *testing.T) {
	t.Log("start conn ... ")
}

func TestShowVersion(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	ver, err := d.SelectVersion()
	if err != nil {
		t.Fatalf("get version failed %s", err.Error())
		return
	}
	t.Logf("current version is %s", ver)
}

func TestShowSlaveStatus(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	s, err := d.ShowSlaveStatus()
	if err != nil {
		t.Fatalf("show slave status failed %s", err.Error())
		return
	}
	t.Logf("current version is %v", s)
}

func TestShowMasterStatus(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	s, err := d.ShowMasterStatus()
	if err != nil {
		t.Fatalf("show master status failed %s", err.Error())
		return
	}
	t.Logf("master status is %v", s)
}

func TestShowApplicationProcesslist(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	s, err := d.ShowApplicationProcesslist([]string{"root"})
	if err != nil {
		t.Fatalf("show processlist failed %s", err.Error())
		return
	}
	t.Log("ending ...", s)
}

func TestShowOpenTables(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	s, err := d.ShowOpenTables(time.Second * 1)
	if err != nil {
		t.Fatalf("show open tables failed %s", err.Error())
		return
	}
	t.Log("ending ...", s)
}

func TestShowDatabases(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	s, err := d.ShowServerCharset()
	if err != nil {
		t.Fatalf("ShowServerCharset failed %s", err.Error())
		return
	}
	t.Log("ending ...", s)
}

func TestShowTables(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	s, err := d.ShowTables(native.TEST_DB)
	if err != nil {
		t.Fatalf("ShowServerCharset failed %s", err.Error())
		return
	}
	t.Log("ending ...", s)
}

type TableElements struct {
	DbNname   string `db:"table_schema"`
	TableName string `db:"table_name"`
}

func TestQueryx(t *testing.T) {
	t.Log("start conn ... ")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	var data []TableElements
	sysdbs := []string{native.TEST_DB}
	q, args, err := sqlx.In(
		"select table_schema,table_name from information_schema.tables where engine <> 'innodb' and table_schema not in (?)",
		sysdbs,
	)
	if err != nil {
		t.Fatalf(err.Error())
		return
	}
	sqlxdb := sqlx.NewDb(d.Db, "mysql")
	query := sqlxdb.Rebind(q)
	err = d.Queryx(&data, query, args...)
	if err != nil {
		t.Fatalf("query table error %s", err.Error())
		return
	}
	var ts native.ShowTableStatusResp
	if err = d.Queryx(ts, "show table status from ? like ?", "mysql", "user"); err != nil {
		t.Fatalf("%s", err.Error())
		return
	}
	t.Log("show tables;", data)
	return
}

func TestGetSingleGlobalVar(t *testing.T) {
	t.Log("start testing ...")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	val, err := d.GetSingleGlobalVar("max_binlog_size")
	// d.Queryxs(&val, fmt.Sprintf("show global variables like '%s'", "max_binlog_size"))
	if err != nil {
		t.Fatalf(err.Error())
	}
	t.Log(val)
}

func TestShowAppProcessList(t *testing.T) {
	t.Log("start..")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	pls, err := d.SelectProcesslist([]string{"make"})
	if err != nil {
		t.Fatal(err)
	}
	t.Log(pls)
	t.Log("ending...")
}

func TestFindLongQuerySQL(t *testing.T) {
	t.Log("start...")
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	pls, err := d.SelectLongRunningProcesslist(0)
	for _, pl := range pls {
		// if !pl.DB.Valid {
		// 	continue
		// }
		//	t.Log(pl.DB.String)
		t.Log(pl.Info.String)
		t.Log(pl.State.String)
	}
	t.Log("ending...")
}

func TestExec(t *testing.T) {
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		t.Fatalf("connect failed %s", err.Error())
		return
	}
	_, err = d.Exec("drop database makee11")
	if err != nil {
		t.Fatalf(err.Error())
	}
}
