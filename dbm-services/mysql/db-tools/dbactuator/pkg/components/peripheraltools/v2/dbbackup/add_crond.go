package dbbackup

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"fmt"
	"path"
	"path/filepath"
	"strings"
	"time"
)

func (c *NewDbBackupComp) AddCrontab() error {
	if c.Params.ClusterType == cst.TendbCluster {
		return c.addCrontabSpider()
	} else {
		return c.addCrontabLegacy()
	}
}

func (c *NewDbBackupComp) addCrontabLegacy() (err error) {
	crondManager := ma.NewManager("http://127.0.0.1:9999")
	var jobItem ma.JobDefine
	logFile := path.Join(cst.DbbackupGoInstallPath, "logs/main.log")
	jobItem = ma.JobDefine{
		Name:     "dbbackup-schedule",
		Command:  filepath.Join(cst.DbbackupGoInstallPath, "dbbackup_main.sh"),
		WorkDir:  cst.DbbackupGoInstallPath,
		Args:     []string{">", logFile, "2>&1"},
		Schedule: c.Params.Options.CrontabTime,
		Creator:  c.Params.ExecUser,
		Enable:   true,
	}
	logger.Info("adding job_item to crond: %+v", jobItem)
	if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
		return err
	}
	return nil
}

func (c *NewDbBackupComp) addCrontabSpider() (err error) {
	crondManager := ma.NewManager("http://127.0.0.1:9999")
	var jobItem ma.JobDefine
	if c.Params.Role == cst.BackupRoleSpiderMaster {
		dbbackupConfFile := fmt.Sprintf("dbbackup.%d.ini", c.Params.Ports[0])
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-schedule",
			Command:  filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"),
			WorkDir:  cst.DbbackupGoInstallPath,
			Args:     []string{"spiderbackup", "schedule", "--config", dbbackupConfFile},
			Schedule: c.Params.Options.CrontabTime, //c.getInsHostCrontabTime(),
			Creator:  c.Params.ExecUser,
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
			return err
		}
	}
	if !(c.Params.Role == cst.BackupRoleSpiderMnt || c.Params.Role == cst.BackupRoleSpiderSlave) { // MASTER,SLAVE,REPEATER
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-check",
			Command:  filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"),
			WorkDir:  cst.DbbackupGoInstallPath,
			Args:     []string{"spiderbackup", "check", "--run"},
			Schedule: "*/1 * * * *",
			Creator:  c.Params.ExecUser,
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
			return err
		}
	}
	return nil
}

func (c *NewDbBackupComp) addCrontabOld() (err error) {
	var newCrontab []string
	err = osutil.RemoveSystemCrontab("dbbackup")
	if err != nil {
		return fmt.Errorf(`删除原备份crontab任务失败("dbbackup") get an error:%w`, err)
	}
	entryShell := path.Join(cst.DbbackupGoInstallPath, "dbbackup_main.sh")
	logfile := path.Join(cst.DbbackupGoInstallPath, "dbbackup.log")
	newCrontab = append(
		newCrontab,
		fmt.Sprintf(
			"#dbbackup/dbbackup_main.sh: backup database every day, distribute at %s by %s",
			time.Now().Format(cst.TIMELAYOUT), c.Params.ExecUser,
		),
	)
	newCrontab = append(
		newCrontab,
		fmt.Sprintf(
			"%s %s 1>>%s 2>&1\n",
			c.Params.Options.CrontabTime, entryShell, logfile,
		),
	)
	crontabStr := strings.Join(newCrontab, "\n")
	return osutil.AddCrontab(crontabStr)
}
