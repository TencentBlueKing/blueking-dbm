package osutil_test

import (
	"fmt"
	"testing"

	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
)

func TestIsFileExist(t *testing.T) {
	fmt.Printf("%s\\%s\\\\%d", cst.BASE_DATA_PATH, cst.MSSQL_DATA_NAME, 111)
}
