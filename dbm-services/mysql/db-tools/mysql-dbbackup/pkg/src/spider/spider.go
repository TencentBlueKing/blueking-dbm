// Package spider TODO
package spider

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// ScheduleBackup TODO
func ScheduleBackup(cnf *config.Public) error {
	spiderInst := mysqlconn.InsObject{
		Host: cnf.MysqlHost,
		Port: cnf.MysqlPort,
		User: cnf.MysqlUser,
		Pwd:  cnf.MysqlPasswd,
	}
	isPrimary, err := mysqlconn.IsPrimarySpider(spiderInst)
	if err != nil {
		logger.Log.Warn(err.Error())
		return err
	} else if isPrimary {
		logger.Log.Infof("current host spider and tdbctl is primary")
		dbw, err := spiderInst.Conn()
		if err != nil {
			return err
		}
		defer dbw.Close()
		// cnf.BackupId 可能是用户传进来的 backup-id
		var b = GlobalBackupModel{Host: spiderInst.Host, Port: spiderInst.Port, BackupId: cnf.BackupId}
		tdbctlInstObj := mysqlconn.GetTdbctlInst(spiderInst)
		var globalBackup = GlobalBackup{
			GlobalBackupModel: &b,
			instObj:           &spiderInst,
			tdbctlInstObj:     &tdbctlInstObj, // 用于在中控查询 slave backup_status 信息
			localLog:          logger.Log.WithField("Port", cnf.MysqlPort),
		}
		var backupId string
		var servers []MysqlServer
		if backupId, servers, err = globalBackup.prepareBackup(mysqlconn.GetTdbctlInst(spiderInst)); err != nil {
			return errors.WithMessagef(err, "prepareBackup")
		}
		if err = globalBackup.initializeBackup(servers, dbw); err != nil {
			return errors.WithMessage(err, "initializeBackup")
		}
		if viper.GetBool("schedule.wait") {
			ch := make(chan error, 1)
			go func() {
				err := globalBackup.waitBackupDone(backupId)
				ch <- err
			}()
			select {
			case res := <-ch:
				return res
			case <-time.After(cst.SpiderScheduleWaitTimeout):
				errStr := fmt.Sprintf("wait done timeout: backupId=%s", backupId)
				logger.Log.Errorf(errStr)
				return errors.New(errStr)
			}
		}
	} else {
		logger.Log.Infof("current host spider and tdbctl is not primary")
		return nil
	}
	return nil
}

// QueryBackup query backup status
func QueryBackup(cnf *config.Public, backupStatus []string) error {
	spiderInst := mysqlconn.InsObject{
		Host: cnf.MysqlHost,
		Port: cnf.MysqlPort,
		User: cnf.MysqlUser,
		Pwd:  cnf.MysqlPasswd,
	}
	isPrimary, err := mysqlconn.IsPrimarySpider(spiderInst)
	if err != nil {
		logger.Log.Warn(err.Error())
		return err
	} else if isPrimary {
		logger.Log.Infof("current host spider and tdbctl is primary")
		dbw, err := spiderInst.Conn()
		if err != nil {
			return err
		}
		defer dbw.Close()
		var b = GlobalBackupModel{Host: spiderInst.Host, Port: spiderInst.Port, BackupId: cnf.BackupId}
		tdbctlInstObj := mysqlconn.GetTdbctlInst(spiderInst)
		var globalBackup = GlobalBackup{
			GlobalBackupModel: &b,
			instObj:           &spiderInst,
			tdbctlInstObj:     &tdbctlInstObj, // 用于在中控查询 slave backup_status 信息
			localLog:          logger.Log.WithField("Port", cnf.MysqlPort),
		}
		tasks, err := globalBackup.queryBackupStatusById(cnf.BackupId, backupStatus)
		if err != nil {
			return err
		}
		sort.Sort(sort.Reverse(GlobalBackupList(tasks)))
		printBackup(tasks, viper.GetString("query.format"))
	}
	return nil
}

// InstBackupTask 记录某个 instance 的所有备份任务信息
type InstBackupTask struct {
	tasks             []*GlobalBackupModel
	backupTaskInit    map[string]int // BackupId:Port
	backupTaskRunning map[string]int // BackupId:Port
	taskInit          []*GlobalBackupModel
	taskRunning       []*GlobalBackupModel
	// earliestBackupID  string
	earliestBackupTask *GlobalBackupModel
	instObj            mysqlconn.InsObject

	cnfFile    string
	cnfObj     config.Public
	shardValue int
}

// RunBackupTasks 运行备份主逻辑
func RunBackupTasks(cnfList []*config.Public) error {
	allInstBackupTasks := make(map[int]InstBackupTask) // port: tasks
	var allBackupsInit []*GlobalBackupModel
	var allBackupsRunning []*GlobalBackupModel
	var errList []error
	for _, cnf := range cnfList {
		logger.Log.Infof("filterBackupTasks: cnfFile:%s", cnf.GetCnfFileName())
		var instTask = InstBackupTask{cnfFile: cnf.GetCnfFileName()}

		if err := instTask.filterBackupTasks(cnf); err != nil {
			errList = append(errList, errors.WithMessage(err, strconv.Itoa(cnf.MysqlPort)))
			continue
		} else {
			allInstBackupTasks[instTask.instObj.Port] = instTask
			allBackupsInit = append(allBackupsInit, instTask.taskInit...)
			allBackupsRunning = append(allBackupsRunning, instTask.taskRunning...)
		}
	}

	if len(allBackupsRunning) > 0 {
		logger.Log.Infof("quit because host has backup running")
		return nil
	}
	// 从本机多个实例里，找出 CreateAt 最早的 backup_id
	if len(allBackupsInit) > 0 {
		sort.Sort(GlobalBackupList(allBackupsInit)) // 取最早的 BackupId
		logger.Log.Infof("all init backupTasks(sorted): %+v", allBackupsInit)
		var backupIdEarliest = allBackupsInit[0].BackupId
		// 一个 backupId 可能在本机上有多个task(对应不同port)
		// 遍历所有port，拿到相同的 backupId，本轮备份只做一个 backupId
		var backupIdTasks []InstBackupTask

		for instPort, instTask := range allInstBackupTasks {
			if port, ok := instTask.backupTaskInit[backupIdEarliest]; ok {
				if port == instPort { // 有可能在 25000 里查到 26000 实例的备份任务，这里要排查
					// 在 instTask.tasks 找到 backupIdEarliest 这个 id 的任务
					for _, t := range instTask.tasks {
						if t.BackupId == backupIdEarliest {
							instTask.earliestBackupTask = t
							continue
						}
					}
					backupIdTasks = append(backupIdTasks, instTask)
				} else {
					logger.Log.Warnf("instance:%s:%d has backup task %s,%d",
						instTask.instObj.Host, instTask.instObj.Port, backupIdEarliest, port)
				}
			}
		}
		if viper.GetBool("check.run") {
			logger.Log.Infof("check and run tasks: %+v", backupIdTasks)
			if err := runBackup(backupIdTasks); err != nil {
				return err
			}
		} else {
			var tasks []*GlobalBackupModel
			for i, t := range backupIdTasks {
				tasks[i] = t.earliestBackupTask
			}
			printBackup(tasks, "")
		}
	} else {
		logger.Log.Info("no backup tasks for this host")
	}
	if len(errList) > 0 {
		return errors.Errorf("%v", errList)
	}
	return nil
}

func printBackup(tasks []*GlobalBackupModel, format string) {
	if format == "json" {
		jsonBytes, _ := json.Marshal(tasks)
		fmt.Println(string(jsonBytes))
		return
	}
	table := tablewriter.NewWriter(os.Stdout)
	table.SetAutoWrapText(false)
	table.SetAutoFormatHeaders(false)
	table.SetAutoMergeCellsByColumnIndex([]int{0})
	table.SetRowLine(true)
	table.SetHeader([]string{"BackupId", "ServerName", "BackupStatus", "Host", "Port", "ShardValue", "CreatedAt"})
	for _, t := range tasks {
		if t != nil {
			table.Append([]string{
				t.BackupId,
				t.ServerName,
				t.BackupStatus,
				t.Host,
				cast.ToString(t.Port),
				cast.ToString(t.ShardValue),
				t.CreatedAt})
		}
	}
	table.SetFooter([]string{"Rows", cast.ToString(table.NumLines()), "", "", "", "", ""})
	table.Render()
}
func runBackup(tasks []InstBackupTask) error {
	var errList []error
	for _, t := range tasks {
		_ = GlobalBackupModel{
			Host:     t.instObj.Host,
			Port:     t.instObj.Port,
			BackupId: t.earliestBackupTask.BackupId,
			// ShardValue: t.shardValue,
		}
		var globalBackup = GlobalBackup{
			GlobalBackupModel: t.earliestBackupTask,
			localLog:          logger.Log.WithField("Port", t.instObj.Port),
		}
		logger.Log.Infof("runBackup[%s], %s:%d", globalBackup.BackupId, t.instObj.Host, t.instObj.Port)
		if err := globalBackup.runBackup(t); err != nil {
			globalBackup.localLog.Errorf("dbbackup failed: %v, error:%s", t.earliestBackupTask, err.Error())
			errList = append(errList, err)
			continue
		}
	}
	if len(errList) > 0 {
		return errors.Errorf("%+v", errList)
	}
	return nil
}

// runBackup schedule backup to run
// 仅备份 1 个实例 task.cnfFile
func (g GlobalBackup) runBackup(task InstBackupTask) error {
	g.localLog.Infof("runBackup for %s:%d, cnfFile=%s, backupId=%s",
		task.instObj.Host, task.instObj.Port, task.cnfFile, g.BackupId)
	dbw, err := task.instObj.Conn()
	if err != nil {
		return err
	}
	defer dbw.Close()
	g.localLog.Infof("runBackup BackupId:%s", g.BackupId)

	// 先检查备份任务在 db 的状态，可能已经发生变化
	if backupStatusInDB, err := g.checkBackupStatus(dbw.Db); err != nil {
		return errors.WithMessage(err, "checkBackupStatus")
	} else {
		if !isBackupStatusInit(backupStatusInDB) {
			g.localLog.Infof("backupStatus changed, in db:%s ", backupStatusInDB)
		}
		if backupStatusInDB == StatusSuccess {
			return nil
		} else if !isBackupStatusInit(backupStatusInDB) {
			return errors.Errorf("backupStatus changed, got %s", backupStatusInDB)
		}
	}
	// 先预提交: update BackupStatus=running, TaskPid=-1, 确保能 update 成功
	if rowsAffected, err := g.updateBackupTask(StatusRunning, -1, dbw.Db); err != nil {
		return err
	} else if rowsAffected != 1 {
		return errors.Errorf("pre-update BackupStatus=running: expect rows=1 but got %d", rowsAffected)
	}

	var execCmd *exec.Cmd
	if task.instObj.Port >= 25000 && task.instObj.Port < 26000 || g.Wrapper == cst.WrapperSpider {
		execCmd = buildBackupCmdForSpiderMaster(g.BackupId)
	} else {
		execCmd = buildBackupCmdForRemote(g.BackupId, task.cnfFile, task.shardValue)
	}
	g.localLog.Infof("backup cmd: %s", strings.Join(execCmd.Args, " "))

	var stderr bytes.Buffer
	var cmdPid = -1
	execCmd.Stderr = &stderr
	if err = execCmd.Start(); err != nil {
		if _, err2 := g.updateBackupTask(StatusFailed, cmdPid, dbw.Db); err2 != nil {
			g.localLog.Warn(err, "update error:%s", stderr.String(), err2.Error())
		}
		return errors.Wrapf(err, "backup start error:%s", stderr.String())
	} else {
		cmdPid = execCmd.Process.Pid
		if _, err2 := g.updateBackupTask(StatusRunning, cmdPid, dbw.Db); err2 != nil {
			return err2
		}
	}

	err = execCmd.Wait()
	// 这里可能运行很久，所以重新获取 db 连接
	dbw.Close()
	dbw, err2 := task.instObj.Conn()
	if err2 != nil {
		return errors.WithMessage(err2, "reconnect to update")
	}
	if err != nil {
		if _, err2 := g.updateBackupTask(StatusFailed, cmdPid, dbw.Db); err2 != nil {
			g.localLog.Warn(err, "update error:%s", stderr.String(), err2.Error())
		}
		return errors.Wrapf(err, "backup run error:%s", stderr.String())
	} else {
		cmdPid = execCmd.Process.Pid
		if _, err2 := g.updateBackupTask(StatusSuccess, cmdPid, dbw.Db); err2 != nil {
			// 实际备份已经成功
			g.localLog.Warn(err, "update error:%s", stderr.String(), err2.Error())
		}
	}
	_ = g.handleOldTask(dbw.Db)
	return nil
}

// buildBackupCmdForSpiderMaster backup all dbbackup.*.ini for spider node
func buildBackupCmdForSpiderMaster(backupId string) *exec.Cmd {
	executable, _ := os.Executable()
	cmdPath := filepath.Dir(executable)
	dbbackupCmd := filepath.Join(cmdPath, "dbbackup_main.sh") // dbbackup_main.sh?
	execArgs := []string{"-k", backupId}                      // "-p", "25000,26000",
	execCmd := exec.Command(dbbackupCmd, execArgs...)
	execCmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	return execCmd
}

// buildBackupCmdForRemote backup one remote instance
func buildBackupCmdForRemote(backupId string, cnfFilename string, shardValue int) *exec.Cmd {
	executable, _ := os.Executable()
	execArgs := []string{
		"dumpbackup",
		"--config", cnfFilename,
		"--backup-id", backupId,
		"--shard-value", cast.ToString(shardValue),
	}
	execCmd := exec.Command(executable, execArgs...)
	return execCmd
}

// archiveAbnormalTasks TODO
// archiveTasks 以 实例 的维度归档异常任务，正常不返回error，避免影响正常备份任务
func archiveAbnormalTasks(backupTasks []*GlobalBackupModel, db *sqlx.DB) error {
	// var runningTask []*GlobalBackupModel
	// var toQuitTask []*GlobalBackupModel
	for _, t := range backupTasks {
		if t.BackupStatus == StatusRunning {
			// 归档 running-task
			// runningTask = append(runningTask, t)
			var bTmp = GlobalBackupModel{BackupId: t.BackupId, Host: t.Host, Port: t.Port}
			bTmp.handleRunningTasks(db)
		} else if t.BackupStatus == StatusQuit {
			// 归档 quit-task
			// toQuitTask = append(toQuitTask, t)
			var bTmp = GlobalBackupModel{BackupId: t.BackupId, Host: t.Host, Port: t.Port}
			bTmp.handleQuitTasks(db)
		}
	}
	return nil
}

// filterBackupTasks 获取需要备份的 task 列表
func (instTask *InstBackupTask) filterBackupTasks(cnf *config.Public) (err error) {
	instObj := mysqlconn.InsObject{
		Host: cnf.MysqlHost,
		Port: cnf.MysqlPort,
		User: cnf.MysqlUser,
		Pwd:  cnf.MysqlPasswd,
	}
	dbw, err := instObj.Conn()
	if err != nil {
		return err
	}
	defer dbw.Close()

	instTask.instObj = instObj
	instTask.backupTaskInit = make(map[string]int)
	instTask.backupTaskRunning = make(map[string]int)
	instTask.shardValue = cnf.ShardValue // 配置文件里面不一定有配置上 ShardValue

	b := GlobalBackupModel{Host: instObj.Host, Port: instObj.Port}
	if strings.HasPrefix(cnf.MysqlRole, "spider_") {
		// 如果当前节点是 spider node，查询备份的时候为了避免跨分片查询所有后端，这里优化下指定 wrapper=SPIDER
		// 在 queryBackupTasks 会作为条件
		b.Wrapper = cst.WrapperSpider
	}
	instTask.tasks, err = b.queryBackupTasks(0, dbw.Db)
	if err != nil {
		return err
	}
	if err = archiveAbnormalTasks(instTask.tasks, dbw.Db); err != nil {
		return err
	}

	for _, t := range instTask.tasks {
		if instTask.shardValue < 0 { // 从 global_backup 中获取 ShardValue 信息，理论上这 2 个应该是相同的
			instTask.shardValue = instTask.tasks[0].ShardValue // 这里一定会有实例，不会panic
		}
		if isBackupStatusInit(t.BackupStatus) {
			instTask.taskInit = append(instTask.taskInit, t)
			if p, ok := instTask.backupTaskInit[t.BackupId]; ok {
				return errors.Errorf("backup_id %s has to ports [%d,%d] in this instance", t.BackupId, p, t.Port)
			}
			instTask.backupTaskInit[t.BackupId] = t.Port
		} else if t.BackupStatus == StatusRunning {
			instTask.taskRunning = append(instTask.taskRunning, t)
			instTask.backupTaskRunning[t.BackupId] = t.Port
		} else {
			continue
		}
	}
	if len(instTask.backupTaskRunning) > 0 {
		logger.Log.Infof("host has backupTask running: %+v", instTask.backupTaskRunning)
	}
	return nil
}

// getBackupStatusByWrapper wrapper = mysql|mysql_slave
func (g GlobalBackup) getBackupStatusByWrapper(backupId string, wrapper string) ([]*GlobalBackupModel, error) {
	tdbctlDbw, err := g.tdbctlInstObj.Conn()
	if err != nil {
		logger.Log.Warnf("getBackupStatusByWrapper connect tdbctl error:%s", err.Error())
		return nil, err
	}
	defer tdbctlDbw.Close()
	var tasks []*GlobalBackupModel
	slaveSQL := fmt.Sprintf("select BackupId,ServerName,Wrapper,Host,Port,ShardValue,BackupStatus,CreatedAt "+
		"from %s  where Wrapper='%s'", g.GlobalBackupModel.TableName(), wrapper)
	if backupId != "" {
		slaveSQL += fmt.Sprintf(" and BackupId='%s'", backupId)
	}
	logger.Log.Warnf("TdbctlQueryByRoleWithMerge sql:%s", slaveSQL)

	if err := TdbctlQueryByRoleWithMerge(&tasks, wrapper, slaveSQL, tdbctlDbw.Db); err != nil {
		logger.Log.Warnf("TdbctlQueryByRoleWithMerge error:%s", err.Error())
		return nil, err
	}
	logger.Log.Warnf("TdbctlQueryByRoleWithMerge slave tasks:%+v", tasks)
	return tasks, nil
}

// getBackupStatusMaster 获取 SPIDER, mysql(remote master)的备份状态
// 通过是否是 StatusReplicated 来区分，即不返回 replicated 状态的任务
func (g GlobalBackup) getBackupStatusMaster(backupId string) ([]*GlobalBackupModel, error) {
	spiderDbw, err := g.instObj.Conn()
	if err != nil {
		logger.Log.Warnf("getBackupStatusMaster connect spider error:%s", err.Error())
		return nil, err
	}
	defer spiderDbw.Close()
	sqlBuilder := sq.Select("*").
		From(g.GlobalBackupModel.TableName()).Where("BackupStatus != ?", StatusReplicated)
	if backupId != "" {
		sqlBuilder = sqlBuilder.Where("BackupId = ?", backupId)
	}
	sqlStr, sqlArgs := sqlBuilder.MustSql()
	var tasks []*GlobalBackupModel
	if err = spiderDbw.Db.Select(&tasks, sqlStr, sqlArgs...); err != nil {
		logger.Log.Warnf("getBackupStatusMaster error:%s", err.Error())
		return nil, err
	}
	return tasks, nil
}

func (g GlobalBackup) queryBackupStatusById(backupId string, backupStatus []string) ([]*GlobalBackupModel, error) {
	tasks, err := g.getBackupStatusMaster(backupId)
	slaveTasks, err1 := g.getBackupStatusByWrapper(backupId, cst.WrapperRemoteSlave)
	if err == nil && err1 == nil {
		tasks = append(tasks, slaveTasks...)
	} else if err != nil || err1 != nil {
		return nil, err
	}
	if len(backupStatus) > 0 {
		tasksFiltered := make([]*GlobalBackupModel, len(tasks))
		for _, t := range tasks {
			backupStatusTrimmed := strings.SplitN(t.BackupStatus, ":", 2)[0]
			if cmutil.StringsHas(backupStatus, backupStatusTrimmed) {
				tasksFiltered = append(tasksFiltered, t)
			}
		}
		return tasksFiltered, nil
	} else {
		return tasks, nil
	}
}

// waitBackupDone wait a backupId to done
// need to check remote master and remote slave
func (g GlobalBackup) waitBackupDone(backupId string) error {
	for true {
		time.Sleep(60 * time.Second)
		var statusTasks = map[string]int{
			StatusInit:       0,
			StatusRunning:    0,
			StatusFailed:     0,
			StatusSuccess:    0,
			StatusUnknown:    0,
			StatusReplicated: 0,
		}

		tasks, err := g.getBackupStatusMaster(backupId)
		slaveTasks, err1 := g.getBackupStatusByWrapper(backupId, cst.WrapperRemoteSlave)
		if err == nil && err1 == nil {
			tasks = append(tasks, slaveTasks...)
		} else if err != nil || err1 != nil {
			if g.retries > 120 {
				return errors.Errorf("backup progress [%s] waitBackupDone failed", backupId)
			} else {
				logger.Log.Warnf("get backup status for wait_done failed: err=%v, err1=%v", err, err1)
				g.retries += 1
				continue
			}
		}
		logger.Log.Warnf("all backupTasks for backupId=%s:%+v", backupId, tasks)

		for _, t := range tasks {
			if t.BackupStatus == StatusSuccess || t.BackupStatus == StatusRunning ||
				t.BackupStatus == StatusInit || t.BackupStatus == StatusReplicated {
				statusTasks[t.BackupStatus] += 1
			} else if strings.HasPrefix(t.BackupStatus, StatusFailed) || strings.HasPrefix(t.BackupStatus, StatusQuit) {
				statusTasks[StatusFailed] += 1
			} else {
				statusTasks[StatusUnknown] += 1
			}
		}
		if statusTasks[StatusInit]+statusTasks[StatusRunning]+statusTasks[StatusReplicated] == 0 {
			finishInfo := fmt.Sprintf("backup progress [%s] finish with: %v", backupId, statusTasks)
			if statusTasks[StatusSuccess] != len(tasks) {
				logger.Log.Warn(finishInfo)
				return errors.New(finishInfo)
			} else {
				logger.Log.Info(finishInfo)
				return nil
			}
		} else {
			nowTime := time.Now()
			if nowTime.Minute()%10 == 0 { // 每 10 分钟打印一次日志
				logger.Log.Infof("backup progress [%s] status: %v", backupId, statusTasks)
			}
		}
	}
	return nil
}
