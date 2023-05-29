package kafka

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// CleanDataComp TODO
type CleanDataComp struct {
	GeneralParam    *components.GeneralParam
	Params          *CleanDataParams
	RollBackContext rollback.RollBackObjects
}

// CleanDataParams TODO
type CleanDataParams struct{}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *CleanDataComp) Init() (err error) {
	logger.Info("Clean data fake init")
	return nil
}

// CleanData TODO
/**
 *  @description:
 *  @return
 */
func (d *CleanDataComp) CleanData() (err error) {
	// 清除crontab
	logger.Info("获取crontab")
	out, err := osutil.ListCrontb(cst.DefaultExecUser)
	if err != nil {
		logger.Error("获取crontab失败", err)
		return err
	}
	logger.Debug("crontab: ", out)
	if len(out) > 0 {
		extraCmd := "crontab -u mysql -r"
		logger.Info("清除crontab, [%s]", extraCmd)
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("[%s] execute failed, %v", extraCmd, err)
			return err
		}
	}

	// 强杀进程
	extraCmd := `ps -ef | egrep 'supervisord|burrow|telegraf|java'|grep -v grep |awk {'print "kill -9 " $2'}|sh`
	logger.Info("强杀进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java`
	logger.Info("删除软链, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除kafkaenv
	extraCmd = `rm -rf /data/kafkaenv*`
	logger.Info("删除kafkaenv, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除数据目录
	extraCmd = `rm -rf /data*/kafkadata*`
	logger.Info("删除kafkadata, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除日志目录
	extraCmd = `rm -rf /data*/kafkalog*`
	logger.Info("删除kafkalog, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除日志目录
	extraCmd = `rm -rf /data*/zklog*`
	logger.Info("删除kafkalog, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}
