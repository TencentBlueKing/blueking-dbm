package checkhealthjob

import (
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"os"
	"strconv"
	"testing"

	"github.com/stretchr/testify/assert"
	"go.uber.org/zap"
)

func parsePort(t *testing.T, portStr string) int {
	port, err := strconv.Atoi(portStr)
	if err != nil {
		t.Errorf("parse port %s failed: %v", portStr, err)
		t.FailNow()
	}
	return port
}

func TestCheckService(t *testing.T) {
	mylog.InitLoggerStdout(false)
	var err error
	logger := mylog.Logger.With(zap.String("test", "TestCheckService"))
	svrItem := &config.ConfServerItem{
		BkDbmLabel: config.BkDbmLabel{
			IP:   os.Getenv("TestDump_HOST"),
			Port: parsePort(t, os.Getenv("TestDump_PORT")),
		},
		UserName: os.Getenv("TestDump_USER"),
		Password: os.Getenv("TestDump_PASS"),
	}
	err = checkService(mongoBin, 10, svrItem, logger)
	t.Logf("checkService result mongoBin: %v", err)
	assert.NoError(t, err)
	err = checkService(mongoshBin, 10, svrItem, logger)
	t.Logf("checkService result mongoshBin: %v", err)
	assert.NoError(t, err)
}

func TestCheckServiceConnectionFailed(t *testing.T) {
	mylog.InitLoggerStdout(false)

	logger := mylog.Logger.With(zap.String("test", "TestCheckServiceConnectionFailed"))
	port := 26999 // is a invalid port
	svrItem := &config.ConfServerItem{
		BkDbmLabel: config.BkDbmLabel{
			IP:   os.Getenv("TestDump_HOST"),
			Port: port,
		},
		UserName: os.Getenv("TestDump_USER"),
		Password: os.Getenv("TestDump_PASS"),
	}
	err := checkService(mongoBin, 10, svrItem, logger)
	t.Logf("checkService result mongoBin: %v", err)
	assert.ErrorIs(t, err, errConnectionFailed)

	err = checkService(mongoshBin, 10, svrItem, logger)
	t.Logf("checkService result mongoshBin: %v", err)
	assert.ErrorIs(t, err, errConnectionFailed)
}

func TestCheckServiceAuthenticationFailed(t *testing.T) {
	mylog.InitLoggerStdout(false)

	logger := mylog.Logger.With(zap.String("test", "TestCheckService"))
	var err error
	svrItem := &config.ConfServerItem{
		BkDbmLabel: config.BkDbmLabel{
			IP:   os.Getenv("TestDump_HOST"),
			Port: parsePort(t, os.Getenv("TestDump_PORT")),
		},
		UserName: "xxxxxx",
		Password: "xxYYxxxx",
	}

	err = checkService(mongoshBin, 10, svrItem, logger)
	t.Logf("checkService result mongoshBin: %v", err)
	assert.ErrorIs(t, err, errAuthenticationFailed)
	err = checkService(mongoBin, 10, svrItem, logger)
	t.Logf("checkService result mongoBin: %v", err)
	assert.ErrorIs(t, err, errAuthenticationFailed)

}
