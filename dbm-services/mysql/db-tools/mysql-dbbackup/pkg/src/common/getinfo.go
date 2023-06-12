package common

import (
	"os/exec"
	"strconv"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// GetDatadir Get the datadir of mysql server
func GetDatadir(port string) (string, error) {
	cmdStr := "ps -ef|grep mysqld|grep " + port + "|grep datadir|grep -o '\\-\\-datadir=\\S*'"
	res, err := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
	if err != nil {
		logger.Log.Error("cant get mysql datadir")
		return "", err
	}
	datadir := strings.Replace(string(res), "\n", "", -1)
	words := strings.Split(datadir, "=")
	return words[1], err
}

// GetTableNum get table number of mysql server
func GetTableNum(port string) int {
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
