package osutil_test

import (
	"testing"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
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
