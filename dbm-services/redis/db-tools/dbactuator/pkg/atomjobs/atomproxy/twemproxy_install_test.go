package atomproxy

import (
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"log"
	"testing"
)

func TestGetDataDir(t *testing.T) {
	mylog.UnitTestInitLog()
	o1, o2, err := getDataDir("./xxx", []string{""}, "mysql.mysql")
	log.Printf("getDataDir return %s %s %v", o1, o2, err)
}
