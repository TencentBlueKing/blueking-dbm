package backupexe

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// GetTargetName produce the target name of the backup file
func GetTargetName(connCnf *parsecnf.CnfShared) (string, error) {
	currentTime := time.Now().Format("20060102_150405")
	/*
		output, err := exec.Command("hostname").CombinedOutput()
		if err != nil {
			logger.Log.Warn("failed to get hostname")
			return "", err
		}
		common.HostName = strings.Replace(string(output), "\n", "", -1)
	*/
	targetName := strings.Join([]string{connCnf.BkBizId, connCnf.ClusterId, connCnf.MysqlHost,
		connCnf.MysqlPort, currentTime, connCnf.BackupType}, "_")
	logger.Log.Info("targetName: ", targetName)
	return targetName, nil
}

// GrantBackup backup grant information
func GrantBackup(connCnf *parsecnf.CnfShared) error {
	DB, err := mysqlconn.InitConn(connCnf)
	if err != nil {
		return err
	}
	defer DB.Close()

	rows, err := DB.Query("select user, host from mysql.user where user not in ('ADMIN','yw','dba_bak_all_sel')")
	if err != nil {
		logger.Log.Error("can't send query to Mysql server %v\n", err)
		return err
	}

	var user string
	var host string

	filepath := connCnf.BackupDir + "/" + common.TargetName + ".priv"
	// logger.Log.Info(filepath)
	file, err := os.OpenFile(filepath, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		logger.Log.Error("failed to create priv file")
		return err
	}
	defer file.Close()
	writer := bufio.NewWriter(file)

	version, verErr := mysqlconn.GetMysqlVersion(DB)
	if verErr != nil {
		return verErr
	}
	logger.Log.Info("mysql version :", version)
	for rows.Next() {
		rows.Scan(&user, &host)
		var grantInfo string
		if strings.Compare(util.VersionParser(version), "005007000") >= 0 { // mysql.version >=5.7
			sqlString := strings.Join([]string{"show create user `", user, "`@`", host, "`"}, "")
			gRows, gErr := DB.Query(sqlString)
			if gErr != nil {
				logger.Log.Warn("failed to get grants about `", user, "`@`", host, "` err:", gErr)
				continue
				// return gErr
			}
			for gRows.Next() {
				gRows.Scan(&grantInfo)
				writer.WriteString(grantInfo + ";\n")
			}
		}
		sqlString := strings.Join([]string{"show grants for `", user, "`@`", host, "`"}, "")
		gRows, gErr := DB.Query(sqlString)
		if gErr != nil {
			logger.Log.Warn("failed to get grants about `", user, "`@`", host, "` err:", gErr)
			continue
			// return gErr
		}
		for gRows.Next() {
			gRows.Scan(&grantInfo)
			writer.WriteString(grantInfo + ";\n")
		}

	}
	writer.WriteString("FLUSH PRIVILEGES;")
	writer.Flush()

	if strings.Compare(util.VersionParser(version), "005007000") >= 0 { // mysql.version >=5.7
		cmdstr := fmt.Sprintf(`sed -i 's/CREATE USER IF NOT EXISTS /CREATE USER /g' %s`, filepath)
		err := exec.Command("/bin/bash", "-c", cmdstr).Run()
		if err != nil {
			logger.Log.Error("cmd.Run() failed with err :", err)
			return err
		}
		cmdstr1 := fmt.Sprintf(`sed -i 's/^\s*CREATE USER /CREATE USER IF NOT EXISTS /g' %s`, filepath)
		err1 := exec.Command("/bin/bash", "-c", cmdstr1).Run()
		if err1 != nil {
			logger.Log.Error("cmd.Run()2 failed with err :", err)
			return err1
		}
	}

	return nil
}
