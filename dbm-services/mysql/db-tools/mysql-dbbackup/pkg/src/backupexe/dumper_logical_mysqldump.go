package backupexe

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// LogicalDumperMysqldump logical dumper using mysqldump tool
type LogicalDumperMysqldump struct {
	cnf          *config.BackupConfig
	dbbackupHome string
	backupInfo   dbareport.IndexContent // for mysqldump backup
}

// initConfig initializes the configuration for the logical dumper[mysqldump]
func (l *LogicalDumperMysqldump) initConfig(mysqlVerStr string) error {
	if l.cnf == nil {
		return errors.New("logical dumper[mysqldump] params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}

	return nil
}

// Execute excute dumping backup with logical backup tool[mysqldump]
func (l *LogicalDumperMysqldump) Execute(enableTimeOut bool) (err error) {
	var binPath string
	if l.cnf.LogicalBackupMysqldump.BinPath != "" {
		binPath = l.cnf.LogicalBackupMysqldump.BinPath
	} else {
		binPath = filepath.Join(l.dbbackupHome, "/bin/mysqldump")
		if !cmutil.FileExists(binPath) {
			binPath, err = exec.LookPath("mysqldump")
			if err != nil {
				return err
			}
		}
	}
	logger.Log.Info("user mysqldump path:", binPath)

	errCreatDir := os.Mkdir(filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName()), 0755)
	if errCreatDir != nil {
		logger.Log.Error("failed to create mysqldump dir, err:", errCreatDir)
		return errCreatDir
	}

	args := []string{
		"-h", l.cnf.Public.MysqlHost,
		"-P", strconv.Itoa(l.cnf.Public.MysqlPort),
		"-u" + l.cnf.Public.MysqlUser,
		"-p" + l.cnf.Public.MysqlPasswd,
		"--single-transaction", "--master-data=2",
		"-r", filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName(), l.cnf.Public.TargetName()+".sql"),
		// --max-allowed-packet=1G
	}
	/*
		if l.cnf.Public.MysqlRole == cst.RoleSlave {
			args = append(args, []string{
				"--dump-slave=2",
			}...)
		}
	*/
	if l.cnf.LogicalBackupMysqldump.ExtraOpt != "" {
		args = append(args, []string{
			fmt.Sprintf(`%s`, l.cnf.LogicalBackupMysqldump.ExtraOpt),
		}...)
	}

	var cmd *exec.Cmd
	if enableTimeOut {
		timeDiffUnix, err := GetMaxRunningTime(l.cnf.Public.BackupTimeOut)
		if err != nil {
			return err
		}
		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUnix))*time.Second)
		defer cancel()

		cmd = exec.CommandContext(ctx,
			"sh", "-c",
			fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	} else {
		cmd = exec.Command("sh", "-c",
			fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	}

	logger.Log.Info("logical dump command with mysqldump: ", cmd.String())

	outFile, err := os.Create(
		filepath.Join(
			l.dbbackupHome,
			"logs",
			fmt.Sprintf("mysqldump_%d.log", int(time.Now().Weekday()))))
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	cmd.Stderr = outFile

	mysqldumpBeginTime := time.Now().Format("2006-01-02 15:04:05")
	l.backupInfo.BackupBeginTime, err = time.ParseInLocation(cst.MydumperTimeLayout, mysqldumpBeginTime, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupBeginTime(mysqldump) %s", mysqldumpBeginTime)
	}
	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run logical backup(with mysqldump) failed: ", err)
		return err
	}
	mysqldumpEndTime := time.Now().Format("2006-01-02 15:04:05")
	l.backupInfo.BackupEndTime, err = time.ParseInLocation(cst.MydumperTimeLayout, mysqldumpEndTime, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupEndTime(mysqldump) %s", mysqldumpEndTime)
	}

	return nil
}

// PrepareBackupMetaInfo prepare the backup result of Logical Backup for mysqldump backup
// 备份完成后，解析 metadata 文件
func (l *LogicalDumperMysqldump) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
	var metaInfo = dbareport.IndexContent{BinlogInfo: dbareport.BinlogStatusInfo{}}
	metaFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), cnf.Public.TargetName()+".sql")
	metadata, err := parseMysqldumpMetadata(metaFileName)
	if err != nil {
		return nil, errors.WithMessage(err, "parse mysqldump metadata")
	}
	metaInfo.BackupBeginTime = l.backupInfo.BackupBeginTime
	metaInfo.BackupEndTime = l.backupInfo.BackupEndTime
	metaInfo.BackupConsistentTime = metaInfo.BackupBeginTime
	metaInfo.BinlogInfo.ShowMasterStatus = &dbareport.StatusInfo{
		BinlogFile: metadata.MasterStatus["File"],
		BinlogPos:  metadata.MasterStatus["Position"],
		MasterHost: cnf.Public.MysqlHost, // use backup_host as local binlog file_pos host
		MasterPort: cast.ToInt(cnf.Public.MysqlPort),
	}
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave {
		metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{
			BinlogFile: metadata.SlaveStatus["File"],
			BinlogPos:  metadata.SlaveStatus["Position"],
			//Gtid:       metadata.SlaveStatus["Executed_Gtid_Set"],
			//MasterHost: metadata.SlaveStatus["Master_Host"],
			//MasterPort: cast.ToInt(metadata.SlaveStatus["Master_Port"]),
		}
	}
	return &metaInfo, nil
}
