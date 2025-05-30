package dbbackup

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/reverseapi"
	"dbm-services/common/reverseapi/define/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"encoding/json"
	"fmt"
	"path"
	"path/filepath"
	"slices"
	"strings"

	"gopkg.in/ini.v1"
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
	return addCrontabLegacy(crondManager, c.Params.Options.CrontabTime)
}

func addCrontabLegacy(cm *ma.Manager, schedule string) (err error) {
	logger.Info("legacy")
	var jobItem ma.JobDefine
	logFile := path.Join(cst.DbbackupGoInstallPath, "logs/main.log")
	jobItem = ma.JobDefine{
		Name:     "dbbackup-schedule",
		Command:  filepath.Join(cst.DbbackupGoInstallPath, "dbbackup_main.sh"),
		WorkDir:  cst.DbbackupGoInstallPath,
		Args:     []string{">", logFile, "2>&1"},
		Schedule: schedule,
		Creator:  "system",
		Enable:   true,
	}
	logger.Info("adding job_item to crond: %+v", jobItem)
	if _, err = cm.CreateOrReplace(jobItem, true); err != nil {
		return err
	}
	return nil
}

func addCrontabSpider(cm *ma.Manager, role string, port int, schedule string) (err error) {
	logger.Info("add dbbackup crond for spider, role: %s, port: %d", role, port)
	var jobItem ma.JobDefine
	if strings.ToLower(role) == strings.ToLower(cst.BackupRoleSpiderMaster) {
		logger.Info("add schedule")
		dbbackupConfFile := fmt.Sprintf("dbbackup.%d.ini", port)
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-schedule",
			Command:  filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"),
			WorkDir:  cst.DbbackupGoInstallPath,
			Args:     []string{"spiderbackup", "schedule", "--config", dbbackupConfFile},
			Schedule: schedule,
			Creator:  "system",
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		id, err := cm.CreateOrReplace(jobItem, true)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		logger.Info("adding job_item to crond: id: %s", id)
	}
	if !(strings.ToLower(role) == strings.ToLower(cst.BackupRoleSpiderMnt) ||
		strings.ToLower(role) == strings.ToLower(cst.BackupRoleSpiderSlave)) { // MASTER,SLAVE,REPEATER
		logger.Info("add check")
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-check",
			Command:  filepath.Join(cst.DbbackupGoInstallPath, "dbbackup"),
			WorkDir:  cst.DbbackupGoInstallPath,
			Args:     []string{"spiderbackup", "check", "--run"},
			Schedule: "*/1 * * * *",
			Creator:  "system",
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		id, err := cm.CreateOrReplace(jobItem, true)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		logger.Info("adding job_item to crond: id: %s", id)
	}
	return nil
}

func (c *NewDbBackupComp) addCrontabSpider() (err error) {
	crondManager := ma.NewManager("http://127.0.0.1:9999")
	return addCrontabSpider(crondManager, c.Params.Role, c.Params.Ports[0], c.Params.Options.CrontabTime)
}

func AddCrond(ports []int) (err error) {
	for _, port := range ports {
		err = addOneCrond(port)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}
	return nil
}

func addOneCrond(port int) (err error) {
	cfgFp := filepath.Join(cst.DbbackupGoInstallPath, fmt.Sprintf("dbbackup.%d.ini", port))
	cfgIni, err := ini.Load(cfgFp)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	var cfg config.BackupConfig
	err = cfgIni.MapTo(&cfg)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	rvApi, err := reverseapi.NewReverseApi(int64(cfg.Public.BkCloudId))
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	data, err := rvApi.MySQL.DBBackupConfig(port)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	var backupCfgs []mysql.DBBackupConfig
	err = json.Unmarshal(data, &backupCfgs)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	if len(backupCfgs) == 0 || slices.IndexFunc(backupCfgs, func(e mysql.DBBackupConfig) bool {
		return e.Port == port
	}) < 0 {
		err = fmt.Errorf("backup config does not contain backup port:%d", port)
		logger.Error(err.Error())
		return err
	}

	backupCfg := backupCfgs[0]

	var opt BackupOptions
	err = json.Unmarshal(backupCfg.Options, &opt)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	cm := ma.NewManager("http://127.0.0.1:9999")
	logger.Info("cluster type: %s", backupCfg.ClusterType)

	if backupCfg.ClusterType == cst.TendbCluster {
		err = addCrontabSpider(cm, backupCfg.Role, port, opt.CrontabTime)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil

	} else {
		err = addCrontabLegacy(cm, opt.CrontabTime)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
		return nil
	}
}
