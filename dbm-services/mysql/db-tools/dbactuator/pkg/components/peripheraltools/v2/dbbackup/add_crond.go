package dbbackup

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"slices"

	"dbm-services/common/go-pubpkg/logger"
	reversemysqlapi "dbm-services/common/reverseapi/apis/mysql"
	reversemysqldef "dbm-services/common/reverseapi/define/mysql"
	"dbm-services/common/reverseapi/pkg/core"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"

	"gopkg.in/ini.v1"
)

func addCrontabLegacy(port int, schedule string) (err error) {
	logger.Info("add dbbackup crond for tendb legacy")
	tl, err := tools.NewToolSetWithPick(tools.ToolDbbackupGo)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	scheduleCmd := fmt.Sprintf("%s reschedule -c %s "+
		"&& chown -R mysql:mysql %s",
		tl.MustGet(tools.ToolDbbackupGo),
		filepath.Join(cst.DbbackupGoInstallPath, fmt.Sprintf("dbbackup.%d.ini", port)),
		cst.DbbackupGoInstallPath,
	)
	logger.Info("crond register cmd: %s", scheduleCmd)
	str, err := osutil.ExecShellCommand(false, scheduleCmd)
	if err != nil {
		logger.Error(
			"failed to register dbbackup-schedule to crond: %s(%s)", str, err.Error(),
		)
		return err
	}
	return nil
}

func addCrontabSpider(role string, port int, schedule string) (err error) {
	logger.Info("add dbbackup crond for spider, role: %s, port: %d", role, port)
	tl, err := tools.NewToolSetWithPick(tools.ToolDbbackupGo)
	if err != nil {
		logger.Error(err.Error())
		return err
	}
	scheduleCmd := fmt.Sprintf("%s reschedule -c %s --cluster-type tendbcluster "+
		"&& chown -R mysql:mysql %s",
		tl.MustGet(tools.ToolDbbackupGo),
		filepath.Join(cst.DbbackupGoInstallPath, fmt.Sprintf("dbbackup.%d.ini", port)),
		cst.DbbackupGoInstallPath,
	)
	logger.Info("crond register cmd: %s", scheduleCmd)
	str, err := osutil.ExecShellCommand(false, scheduleCmd)
	if err != nil {
		logger.Error(
			"failed to register spiderbackup tasks to crond: %s(%s)", str, err.Error(),
		)
		return err
	}
	return nil
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

	apiCore, err := core.NewCore(int64(cfg.Public.BkCloudId), core.DefaultRetryOpts...)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	data, err := reversemysqlapi.DBBackupConfig(apiCore, port)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	var backupCfgs []reversemysqldef.DBBackupConfig
	err = json.Unmarshal(data, &backupCfgs)
	if err != nil {
		logger.Error(err.Error())
		return err
	}

	if len(backupCfgs) == 0 || slices.IndexFunc(backupCfgs, func(e reversemysqldef.DBBackupConfig) bool {
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

	logger.Info("cluster type: %s", backupCfg.ClusterType)

	if backupCfg.ClusterType == cst.TendbCluster {
		err = addCrontabSpider(backupCfg.Role, port, opt.CrontabTime)
		if err != nil {
			return err
		}
		return nil

	} else {
		err = addCrontabLegacy(port, opt.CrontabTime)
		if err != nil {
			return err
		}
		return nil
	}
}
