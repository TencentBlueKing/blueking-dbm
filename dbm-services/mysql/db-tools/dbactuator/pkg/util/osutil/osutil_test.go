package osutil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func TestIsFileExist(t *testing.T) {
	f := "/tmp/1.txt"
	d := "/tmp/asdad/"
	exist_f := osutil.FileExist(f)
	exist_d := osutil.FileExist(d)
	t.Log("f exist", exist_f)
	t.Log("d exist", exist_d)
	return
}

func TestCreateLink(t *testing.T) {
	t.Log("start..")
	err := osutil.CreateSoftLink("/data/mysql/3306/mysql.sock", "/tmp/mysql.sock")
	if err != nil {
		t.Log(err.Error())
		return
	}
	t.Log("end..")
}
