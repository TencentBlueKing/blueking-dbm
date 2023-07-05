package backupexe

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

//// GetTargetName produce the target name of the backup file
//func GetTargetName(cfg *config.Public) (string, error) {
//	currentTime := time.Now().Format("20060102_150405")
//	/*
//		output, err := exec.Command("hostname").CombinedOutput()
//		if err != nil {
//			logger.Log.Warn("failed to get hostname")
//			return "", err
//		}
//		common.HostName = strings.Replace(string(output), "\n", "", -1)
//	*/
//	targetName := fmt.Sprintf("%s_%s_%s_%d_%s_%s",
//		cfg.BkBizId, cfg.ClusterId, cfg.MysqlHost, cfg.MysqlPort, currentTime, cfg.BackupType)
//	logger.Log.Info("targetName: ", targetName)
//	return targetName, nil
//}

// GrantBackup backup grant information
func GrantBackup(cfg *config.Public) error {
	db, err := mysqlconn.InitConn(cfg)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()

	rows, err := db.Query("select user, host from mysql.user where user not in ('ADMIN','yw','dba_bak_all_sel')")
	if err != nil {
		logger.Log.Error("can't send query to Mysql server %v\n", err)
		return err
	}

	var user string
	var host string

	filepath := cfg.BackupDir + "/" + cfg.TargetName() + ".priv"
	// logger.Log.Info(filepath)
	file, err := os.OpenFile(filepath, os.O_RDWR|os.O_CREATE, 0666)
	if err != nil {
		logger.Log.Error("failed to create priv file")
		return err
	}
	defer func() {
		_ = file.Close()
	}()

	writer := bufio.NewWriter(file)

	version, verErr := mysqlconn.GetMysqlVersion(db)
	verStr, _ := util.VersionParser(version)
	if verErr != nil {
		return verErr
	}
	logger.Log.Info("mysql version :", version)
	for rows.Next() {
		err := rows.Scan(&user, &host)
		if err != nil {
			logger.Log.Error("scan backup user row failed: ", err)
			return err
		}

		var grantInfo string
		if strings.Compare(verStr, "005007000") >= 0 { // mysql.version >=5.7
			sqlString := strings.Join([]string{"show create user `", user, "`@`", host, "`"}, "")
			gRows, err := db.Query(sqlString)
			if err != nil {
				logger.Log.Warn("failed to get grants about `", user, "`@`", host, "` err:", err)
				continue
			}

			for gRows.Next() {
				err := gRows.Scan(&grantInfo)
				if err != nil {
					logger.Log.Error("scan show create user row failed: ", err)
					return err
				}

				_, err = writer.WriteString(grantInfo + ";\n")
				if err != nil {
					logger.Log.Error("write user grants failed: ", err)
					return err
				}
			}
		}

		sqlString := strings.Join([]string{"show grants for `", user, "`@`", host, "`"}, "")
		gRows, err := db.Query(sqlString)
		if err != nil {
			logger.Log.Warn("failed to get grants about `", user, "`@`", host, "` err:", err)
			continue
		}
		for gRows.Next() {
			err := gRows.Scan(&grantInfo)
			if err != nil {
				logger.Log.Error("scan show grants row failed: ", err)
				return err
			}

			_, err = writer.WriteString(grantInfo + ";\n")
			if err != nil {
				logger.Log.Error("write show grants failed: ", err)
				return err
			}
		}

	}

	_, err = writer.WriteString("FLUSH PRIVILEGES;")
	if err != nil {
		logger.Log.Error("write flush privileges failed: ", err)
		return err
	}

	err = writer.Flush()
	if err != nil {
		logger.Log.Error("flush file failed: ", err)
		return err
	}

	if strings.Compare(verStr, "005007000") >= 0 { // mysql.version >=5.7
		cmdStr := fmt.Sprintf(`sed -i 's/CREATE USER IF NOT EXISTS /CREATE USER /g' %s`, filepath)
		err := exec.Command("/bin/bash", "-c", cmdStr).Run()
		if err != nil {
			logger.Log.Error(fmt.Sprintf("run %s failed: ", cmdStr), err)
			return err
		}

		cmdStr = fmt.Sprintf(`sed -i 's/^\s*CREATE USER /CREATE USER IF NOT EXISTS /g' %s`, filepath)
		err = exec.Command("/bin/bash", "-c", cmdStr).Run()
		if err != nil {
			logger.Log.Error(fmt.Sprintf("run %s failed: ", cmdStr), err)
			return err
		}
	}

	return nil
}
