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

func TestCheckService(t *testing.T) {
	mylog.InitLoggerStdout(false)

	logger := mylog.Logger.With(zap.String("test", "TestCheckService"))
	port, err := strconv.Atoi(os.Getenv("TestDump_PORT"))
	if err != nil {
		t.Errorf("get MONGO_PORT failed: %v", err)
	}
	svrItem := &config.ConfServerItem{
		BkDbmLabel: config.BkDbmLabel{
			IP:   os.Getenv("TestDump_HOST"),
			Port: port,
		},
		UserName: os.Getenv("TestDump_USER"),
		Password: os.Getenv("TestDump_PASS"),
	}
	err = checkService(10, svrItem, logger)
	t.Logf("checkService result: %v", err)
	assert.NoError(t, err)
}

func TestCheckServiceConnectionFailed(t *testing.T) {
	mylog.InitLoggerStdout(false)

	logger := mylog.Logger.With(zap.String("test", "TestCheckServiceConnectionFailed"))
	port := 26999
	svrItem := &config.ConfServerItem{
		BkDbmLabel: config.BkDbmLabel{
			IP:   os.Getenv("TestDump_HOST"),
			Port: port,
		},
		UserName: os.Getenv("TestDump_USER"),
		Password: os.Getenv("TestDump_PASS"),
	}
	err := checkService(10, svrItem, logger)
	t.Logf("checkService result: %v", err)
	// require a error.
	assert.ErrorIs(t, err, errConnectionFailed)
}

func TestCheckServiceAuthenticationFailed(t *testing.T) {
	mylog.InitLoggerStdout(false)

	logger := mylog.Logger.With(zap.String("test", "TestCheckService"))
	port, err := strconv.Atoi(os.Getenv("TestDump_PORT"))
	if err != nil {
		t.Errorf("get MONGO_PORT failed: %v", err)
	}
	svrItem := &config.ConfServerItem{
		BkDbmLabel: config.BkDbmLabel{
			IP:   os.Getenv("TestDump_HOST"),
			Port: port,
		},
		UserName: "xxxxxx",
		Password: "xxYYxxxx",
	}
	err = checkService(10, svrItem, logger)
	t.Logf("checkService result: %v", err)
	assert.ErrorIs(t, err, errAuthenticationFailed)
}
