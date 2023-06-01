package osutil_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

func TestExecShellCommand(t *testing.T) {
	t.Log("start..")
	out, err := osutil.StandardShellCommand(false, "usermod -d /home/mysql  mysql")
	if err != nil {
		t.Fatal(err)
	}
	t.Log(out)
}
