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
	if c.Params.UntarOnly {
		logger.Info("untar_only=true do not need AddCrontab")
		return nil
	}
	if c.Params.ClusterType == cst.TendbCluster {
		return c.addCrontabSpider()
	} else {
		return c.addCrontabLegacy()
	}
}

func (c *NewDbBackupComp) addCrontabLegacy() (err error) {
	crondManager := ma.NewManager("http://127.0.0.1:9999")
	var jobItem ma.JobDefine
	logFile := path.Join(c.installPath, "logs/main.log")
	jobItem = ma.JobDefine{
		Name:     "dbbackup-schedule",
		Command:  filepath.Join(c.installPath, "dbbackup_main.sh"),
		WorkDir:  c.installPath,
		Args:     []string{">", logFile, "2>&1"},
		Schedule: c.getInsHostCrontabTime(),
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
			Command:  filepath.Join(c.installPath, "dbbackup"),
			WorkDir:  c.installPath,
			Args:     []string{"spiderbackup", "schedule", "--config", dbbackupConfFile},
			Schedule: c.getInsHostCrontabTime(),
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
			Command:  filepath.Join(c.installPath, "dbbackup"),
			WorkDir:  c.installPath,
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
	entryShell := path.Join(c.installPath, "dbbackup_main.sh")
	logfile := path.Join(c.installPath, "dbbackup.log")
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
			c.getInsHostCrontabTime(), entryShell, logfile,
		),
	)
	crontabStr := strings.Join(newCrontab, "\n")
	return osutil.AddCrontab(crontabStr)
}

func (c *NewDbBackupComp) getInsHostCrontabTime() string {
	cronTime := ""
	for _, opt := range c.Params.Options {
		if opt.CrontabTime > cronTime {
			cronTime = opt.CrontabTime
		}
	}
	return cronTime
}
