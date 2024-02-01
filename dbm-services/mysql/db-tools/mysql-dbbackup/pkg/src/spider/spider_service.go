package spider

import (
	"context"
	"fmt"
	"strings"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/shirou/gopsutil/process"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// prepareBackup 获取backupId 和 需要备份的 servers
// servers 从 tdbctl master 获取，因为它的是全的， spider节点的 mysql.servers 没有 remote slave 信息
func (g GlobalBackup) prepareBackup(tdbctlInst mysqlconn.InsObject) (string, []MysqlServer, error) {
	dbw, err := tdbctlInst.Conn()
	if err != nil {
		return "", nil, err
	}
	defer dbw.Close()

	var serversTmp []MysqlServer
	sqlQ := sq.Select("Server_name", "Wrapper", "Host", "Port").
		From(MysqlServer{}.TableName()) // .Where("Wrapper in ?", []string{"mysql", "SPIDER"})
	sqlStr, sqlArgs := sqlQ.MustSql()
	logger.Log.Infof("sqlStr: %s", sqlStr)
	if err := dbw.Db.Select(&serversTmp, sqlStr, sqlArgs...); err != nil {
		return "", nil, err
	}
	var backupId string
	var backupServers []MysqlServer
	for _, s := range serversTmp {
		if s.Wrapper == cst.WrapperRemote || s.Wrapper == cst.WrapperRemoteSlave {
			if strings.HasPrefix(s.ServerName, "SPT_SLAVE") {
				s.PartValue = cast.ToInt(strings.TrimPrefix(s.ServerName, "SPT_SLAVE"))
			} else if strings.HasPrefix(s.ServerName, "SPT") {
				s.PartValue = cast.ToInt(strings.TrimPrefix(s.ServerName, "SPT"))
			} else {
				return "", nil, errors.Errorf("Server_name should has prefix SPT/SPT_SLAVE: %+v", s)
			}
			backupServers = append(backupServers, s)
		} else if s.Host == g.Host && s.Wrapper == cst.WrapperSpider {
			// primary spider / tdbctl
			s.PartValue = cst.SpiderNodeShardValue
			backupServers = append(backupServers, s)
		}
	}
	logger.Log.Infof("backupServers:%+v", backupServers)
	if g.BackupId != "" {
		backupId = g.BackupId
	} else {
		if backupId, err = dbareport.GenerateUUid(); err != nil {
			return "", nil, err
		}
		g.BackupId = backupId
	}
	return backupId, backupServers, nil
}

func (g GlobalBackup) initializeBackup(backupServers []MysqlServer, dbw *mysqlconn.DbWorker) error {
	createdAt := time.Now().Format(time.DateTime)
	sqlI := sq.Insert(g.GlobalBackupModel.TableName()).
		Columns("ServerName", "Wrapper", "Host", "Port", "ShardValue", "BackupId", "BackupStatus", "CreatedAt")
	for _, s := range backupServers {
		if strings.HasPrefix(s.ServerName, "SPT_SLAVE") {
			sqlI = sqlI.Values(s.ServerName, s.Wrapper, s.Host, s.Port, s.PartValue, g.BackupId,
				StatusReplicated, createdAt)
		} else {
			sqlI = sqlI.Values(s.ServerName, s.Wrapper, s.Host, s.Port, s.PartValue, g.BackupId, StatusInit, createdAt)
		}
	}
	sqlStr, sqlArgs := sqlI.MustSql()
	logger.Log.Infof("init backup tasks:%+v, %+v", sqlStr, sqlArgs)
	if _, err := sqlI.RunWith(dbw.Db).Exec(); err != nil {
		logger.Log.Warnf("fail to initializeBackup: %s", err.Error())
		if err2 := migrateBackupSchema(err, dbw.Db); err2 != nil {
			return errors.WithMessagef(err, "migrateBackupSchema failed:%s", err2.Error())
		} else {
			logger.Log.Infof("migrateBackupSchema sucess: continue")
			if g.retries < 1 {
				g.retries += 1
				return g.initializeBackup(backupServers, dbw)
			} else {
				return errors.New("retry initializeBackup too much")
			}
			// return nil
		}
	}
	return nil
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

// queryBackupTasks 以本机 ip:port 来查询本实例的备份任务
func (b GlobalBackupModel) queryBackupTasks(retries int, db *sqlx.DB) (backupTasks []*GlobalBackupModel, err error) {
	sqlBuilder := sq.Select("BackupId", "ServerName", "Host", "Port", "BackupStatus", "ShardValue", "CreatedAt").
		From(b.TableName()).
		Where("Host = ? and Port = ?", b.Host, b.Port).
		Where(sq.Eq{"BackupStatus": []string{StatusInit, StatusReplicated, StatusRunning}}) // isBackupStatusInit
	if b.BackupId != "" {
		sqlBuilder = sqlBuilder.Where("BackupId = ?", b.BackupId)
	}
	if b.Wrapper == cst.WrapperSpider { // 可以避免在 spider node 上备份时，跨分片查询
		sqlBuilder = sqlBuilder.Where("ShardValue = ?", cst.SpiderNodeShardValue)
		b.Wrapper = "" // 避免后续可能干扰后续查询条件
	}
	sqlStr, sqlArgs, err := sqlBuilder.ToSql()
	if err != nil {
		return nil, err
	}
	logger.Log.Infof("queryBackupTasks port=%d, sqlStr:%s, sqlArgs:%v", b.Port, sqlStr, sqlArgs)

	if err = db.Select(&backupTasks, sqlStr, sqlArgs...); err != nil {
		logger.Log.Warnf("fail to queryBackupTasks: %s, retries %d", err.Error(), retries)
		if err2 := migrateBackupSchema(err, db); err2 != nil {
			return nil, errors.WithMessagef(err, "migrateBackupSchema failed:%s", err2.Error())
		} else {
			logger.Log.Infof("migrateBackupSchema sucess: continue")
			if retries < 1 {
				retries += 1
				return b.queryBackupTasks(retries, db)
			} else {
				return nil, errors.Wrap(err, "retry queryBackupTasks too much")
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
	ctx := context.Background()
	conn, err := db.DB.Conn(context.Background())
	// 关闭 binlog 避免 slave 报错
	if _, err = conn.ExecContext(ctx, "set session sql_log_bin=0"); err != nil {
		return err
	}

	sqlStr := fmt.Sprintf("DELETE FROM %s WHERE CreatedAt < DATE_SUB(now(), INTERVAL %d DAY)",
		b.TableName(), cst.SpiderRemoveOldTaskBeforeDays) // where host ?
	_, _ = conn.ExecContext(ctx, sqlStr)
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
