package spider

import (
	"fmt"
	"strings"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/shirou/gopsutil/process"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

func (g GlobalBackup) initializeBackup(dbw *mysqlconn.DbWorker) (backupId string, err error) {
	var servers []MysqlServer
	sqlQ := sq.Select("Server_name", "Wrapper", "Host", "Port").
		From(MysqlServer{}.TableName()) // .Where("Wrapper in ?", []string{"mysql", "SPIDER"})
	sqlStr, sqlArgs := sqlQ.MustSql()
	logger.Log.Infof("sqlStr: %s", sqlStr)
	if err := dbw.Db.Select(&servers, sqlStr, sqlArgs...); err != nil {
		return "", err
	}
	var serversBackup []MysqlServer
	for _, s := range servers {
		if s.Wrapper == cst.WrapperRemote || s.Wrapper == cst.WrapperRemoteSlave {
			if strings.HasPrefix(s.ServerName, "SPT") {
				s.PartValue = cast.ToInt(strings.TrimLeft(s.ServerName, "SPT"))
			} else {
				return "", errors.Errorf("Server_name should has prefix SPT: %+v", s)
			}
			serversBackup = append(serversBackup, s)
		} else if s.Host == g.Host && s.Wrapper == cst.WrapperSpider {
			// primary spider / tdbctl
			serversBackup = append(serversBackup, s)

		}
	}
	logger.Log.Infof("serversBackup:%+v", serversBackup)

	if g.BackupId != "" {
		backupId = g.BackupId
	} else {
		if backupId, err = dbw.GetOneValue(`select uuid()`); err != nil {
			return "", err
		}
	}

	sqlI := sq.Insert(g.GlobalBackupModel.TableName()).
		Columns("Server_name", "Wrapper", "Host", "Port", "ShardValue", "BackupId", "BackupStatus")
	for _, s := range serversBackup {
		sqlI = sqlI.Values(s.ServerName, s.Wrapper, s.Host, s.Port, s.PartValue, backupId, StatusInit)
	}
	sqlStr, sqlArgs = sqlI.MustSql()
	logger.Log.Infof("init backup tasks:%+v, %+v", sqlStr, sqlArgs)
	if _, err := sqlI.RunWith(dbw.Db).Exec(); err != nil {
		logger.Log.Warnf("fail to initializeBackup: %s", err.Error())
		if err2 := migrateBackupSchema(err, dbw.Db); err2 != nil {
			return "", errors.WithMessagef(err, "migrateBackupSchema failed:%s", err2.Error())
		} else {
			logger.Log.Infof("migrateBackupSchema sucess: continue")
			if g.retries < 1 {
				g.retries += 1
				return g.initializeBackup(dbw)
			} else {
				return "", errors.New("retry initializeBackup too much")
			}
			// return nil
		}
	}
	return backupId, nil
}

func (b GlobalBackupModel) checkBackupStatus(db *sqlx.DB) (string, error) {
	sqlBuilder := sq.Select("BackupStatus").From(b.TableName()).
		Where("BackupId=? and Host=? and Port=?", b.BackupId, b.Host, b.Port)
	var backupStatus string
	sqlStr, sqlArgs := sqlBuilder.MustSql()
	if err := db.QueryRow(sqlStr, sqlArgs...).Scan(&backupStatus); err != nil {
		// if err := sqlBuilder.RunWith(db).Scan(&backupStatus); err != nil {
		return "", err
	} else {
		return backupStatus, nil
	}
}

// queryBackupTasks 以本机 ip 来查询本实例的备份任务
func (b GlobalBackupModel) queryBackupTasks(retries int, db *sqlx.DB) (backupTasks []*GlobalBackupModel, err error) {
	sqlBuilder := sq.Select("BackupId", "Host", "Port", "BackupStatus", "ShardValue", "CreatedAt").
		From(b.TableName()).
		Where("Host = ?", b.Host).
		Where(sq.Eq{"BackupStatus": []string{StatusInit, StatusRunning}})
	if b.BackupId != "" {
		sqlBuilder = sqlBuilder.Where("BackupId = ?", b.BackupId)
	}
	sqlStr, sqlArgs, err := sqlBuilder.ToSql()
	if err != nil {
		return nil, err
	}
	logger.Log.Infof("queryBackupTasks port=%d, sqlStr:%s, sqlArgs:%v", b.Port, sqlStr, sqlArgs)

	if err = db.Select(&backupTasks, sqlStr, sqlArgs...); err != nil {
		logger.Log.Warnf("fail to queryBackupTasks: %s", err.Error())
		if err2 := migrateBackupSchema(err, db); err2 != nil {
			return nil, errors.WithMessagef(err, "migrateBackupSchema failed:%s", err2.Error())
		} else {
			logger.Log.Infof("migrateBackupSchema sucess: continue")
			if retries < 1 {
				retries += 1
				return b.queryBackupTasks(retries, db)
			} else {
				return nil, errors.New("retry queryBackupTasks too much")
			}
			// return nil, nil
		}
	} else if len(backupTasks) == 0 {
		logger.Log.Infof("no backup task for %s:%d", b.Host, b.Port)
		return nil, nil
	}
	logger.Log.Infof("check tasks to run: %+v", backupTasks)
	return backupTasks, nil
}

// handleRunningTasks 归档异常 running 状态的任务
// 1. task pid 不存在
// 2. task 运行超过 48 h
func (b GlobalBackupModel) handleRunningTasks(db *sqlx.DB) {
	var backupStatus string
	if b.TaskPid <= 0 {
		logger.Log.Warnf("no pid, backup-id info:%s", b.BackupId)
		backupStatus = fmt.Sprintf("%s: %s", StatusFailed, "no pid")
	} else if proc, err := process.NewProcess(int32(b.TaskPid)); err != nil {
		if err == process.ErrorProcessNotRunning {
			logger.Log.Warnf("%s, backup-id info:%s", err.Error(), b.BackupId)
			backupStatus = fmt.Sprintf("%s: %s", StatusFailed, err.Error())
		} else {
			logger.Log.Warn("NewProcess error", err.Error())
			// return errors.WithMessage(err, "NewProcess")
		}
	} else {
		cmdline, _ := proc.Cmdline()
		if !strings.Contains(cmdline, b.BackupId) {
			logger.Log.Warnf("cmdline: %s has no backup-id info:%s", cmdline, b.BackupId)
			backupStatus = fmt.Sprintf("%s: %s", StatusFailed, "cmdline has no backup-id")
		}
	}
	if backupStatus != "" {
		if _, err := b.updateBackupTask(backupStatus, 0, db); err != nil {
			logger.Log.Warn(err.Error())
		}
	}

	updatedAt, err := time.ParseInLocation("", b.UpdatedAt, time.Local)
	if err != nil {
		logger.Log.Warn("error time format: %s, %s", b.BackupId, b.UpdatedAt)
		// return nil
	}
	if time.Now().Sub(updatedAt).Hours() > cst.SpiderTaskMaxRunHours && backupStatus == "" {
		logger.Log.Warn("backup timeout: %s", b.BackupId)
		backupStatus := fmt.Sprintf("%s: %s", StatusFailed, "timeout")
		if _, err = b.updateBackupTask(backupStatus, 0, db); err != nil {
			logger.Log.Warn(err.Error())
		}
	}
	// return nil
}

// handleQuitTasks 归档以 quit 状态的任务
func (b GlobalBackupModel) handleQuitTasks(db *sqlx.DB) {
	var bTmp = GlobalBackupModel{BackupId: b.BackupId, Host: b.Host, Port: b.Port}
	var backupStatus string
	var pids []int32
	if proc, err := process.NewProcess(int32(b.TaskPid)); err != nil {
		if err == process.ErrorProcessNotRunning {
			backupStatus = StatusQuit + ": no process"
		} else {
			logger.Log.Warn("NewProcess error", err.Error())
			// continue
		}
	} else {
		logger.Log.Infof("kill process: %d", proc.Pid)
		// _ = syscall.Kill(-int(proc.Pid), syscall.SIGKILL)
		pids = append(pids, proc.Pid)
		childs, _ := proc.Children()
		for _, i := range childs {
			// _ = syscall.Kill(int(i.Pid), syscall.SIGKILL)
			_ = i.Kill()
			// pids = append(pids, i.Pid)
		}
		_ = proc.Kill()

		time.Sleep(1 * time.Second)
		if proc, err = process.NewProcess(int32(b.TaskPid)); err == nil {
			backupStatus = StatusQuit + ": fail"
		} else if err == process.ErrorProcessNotRunning {
			backupStatus = StatusQuit + ": success"
		}
	}
	if backupStatus != "" {
		if _, err := bTmp.updateBackupTask(backupStatus, 0, db); err != nil {
			logger.Log.Warn(err.Error())
		}
	}
}

// handleOldTask 移除太久远的任务
func (b GlobalBackupModel) handleOldTask(db *sqlx.DB) error {
	sqlB := sq.Delete("").From(b.TableName()).
		Where(fmt.Sprintf("CreatedAt < DATE_SUB(now(), INTERVAL %d DAY)", cst.SpiderRemoveOldTaskBeforeDays))
	if _, err := sqlB.RunWith(db).Exec(); err != nil {
		return err
	}
	return nil
}

func (b GlobalBackupModel) updateBackupTask(backupStatus string, taskPid int, db *sqlx.DB) (int64, error) {
	logger.Log.Infof("update task: BackupId=%s, Port=%d, BackupStatus=%s, TaskPid=%d",
		b.BackupId, b.Port, backupStatus, taskPid)

	sqlBuilder := sq.Update(b.TableName()).Where("BackupId=? and Host=? and Port=?", b.BackupId, b.Host, b.Port)
	/*
		whereMap := map[string]interface{}{
			"BackupStatus": backupStatus,
			"TaskPid":      taskPid,
		}
		sqlBuilder = sqlBuilder.SetMap(whereMap)
	*/
	sqlBuilder = sqlBuilder.Set("BackupStatus", backupStatus)
	if taskPid != 0 {
		sqlBuilder = sqlBuilder.Set("TaskPid", taskPid)
	}
	sqlStr, sqlArgs := sqlBuilder.MustSql()
	logger.Log.Infof("updateBackupTask: %+v, %+v", sqlStr, sqlArgs)
	if res, err := sqlBuilder.RunWith(db).Exec(); err != nil {
		return 0, errors.WithMessage(err, "update task failed")
	} else {
		rowsAffected, _ := res.RowsAffected()
		return rowsAffected, nil
	}
}
