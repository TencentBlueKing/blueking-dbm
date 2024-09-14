package common

import (
	"os/exec"
	"strconv"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// GetDatadir Get the datadir of mysql server
func GetDatadir(port int) (string, error) {
	cnfFileName := util.GetMyCnfFileName(port)
	cnfFile := &util.CnfFile{FileName: cnfFileName}
	if err := cnfFile.Load(); err != nil {
		return "", errors.WithMessage(err, "get data dir")
	}
	return cnfFile.GetMySQLDataDir()
}

// GetTableNum get table number of mysql server
func GetTableNum(port int) int {
	datadir, err := GetDatadir(port)
	if err != nil {
		return -1
	}
	cmdStr := "find " + datadir + "|grep -c frm"
	res, err := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
	if err != nil {
		logger.Log.Error("cant get mysql tableNum")
		return -1
	}

	tableNum, _ := strconv.Atoi(strings.Replace(string(res), "\n", "", -1))
	return tableNum
}
