package test

import (
	"fmt"
	"testing"
	"time"

	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule/dbmysql"
	"dbm-services/common/dbha/ha-module/dbutil"
)

func newTestInstance() *dbmysql.MySQLDetectInstance {
	return &dbmysql.MySQLDetectInstance{
		BaseDetectDB: dbutil.BaseDetectDB{
			Ip:             "xxxx",
			Port:           40000,
			App:            "test",
			DBType:         constvar.DetectTenDBHA,
			ReporterTime:   time.Unix(0, 0),
			ReportInterval: 10,
			Status:         constvar.DBCheckSuccess,
			SshInfo: dbutil.Ssh{
				Port:    36000,
				User:    "xxxx",
				Pass:    "xxxx",
				Dest:    "mysql",
				Timeout: 5,
			},
		},
		User:    "root",
		Pass:    "xxxx",
		Timeout: 10,
	}
}

func TestSSH(t *testing.T) {
	ins := newTestInstance()
	err := ins.CheckSSH()
	if err != nil {
		t.Errorf("detection failed.err:%s", err.Error())
	}
}

func TestDetectionSuccess(t *testing.T) {
	var d dbutil.DataBaseDetect
	d = newTestInstance()
	for i := 0; i <= 20; i++ {
		err := d.Detection()
		if err != nil {
			fmt.Println("detection failed.err:" + err.Error())
			t.Errorf("detection failed.err:%s", err.Error())
		}
		fmt.Printf("status: %s\n", d.GetStatus())
		if d.NeedReporter() {
			fmt.Println("need reporter")
			d.UpdateReporterTime()
		} else {
			fmt.Println("needn't reporter")
		}
		time.Sleep(time.Second)
	}
}
