package victoriametrics

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
)

// CleanDataComp 是一个结构体，用于清理数据和相关进程。
type CleanDataComp struct {
	GeneralParam    *components.GeneralParam // GeneralParam 是通用参数，可能包含了一些全局设置或配置。
	Params          *CleanDataParams         // Params 是清理数据的参数，目前看起来是空的，可能在后续的开发中会添加具体的参数。
	RollBackContext rollback.RollBackObjects // RollBackContext 是回滚上下文，用于在操作失败时进行回滚。
}

// CleanDataParams 是一个空的结构体，可能在后续的开发中会添加具体的参数。
type CleanDataParams struct{}

// Init 是 CleanDataComp 的初始化函数，目前只是打印一条日志，没有实际操作。
func (d *CleanDataComp) Init() (err error) {
	logger.Info("Clean data fake init")
	return nil
}

// CleanData 是清理数据和相关进程的函数，它执行了以下操作：
// 1. 清除crontab
// 2. 强杀进程
// 3. 删除软链
// 4. 清理profile
// 5. 删除vmenv
// 6. 删除数据目录
// 7. 删除日志目录
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
		extraCmd := fmt.Sprintf("crontab -u %s -r", cst.DefaultExecUser)
		logger.Info("清除crontab, [%s]", extraCmd)
		if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("[%s] execute failed, %v", extraCmd, err)
			return err
		}
	}

	// 强杀进程
	extraCmd :=
		`ps -ef | egrep 'supervisord|node_exporter|telegraf|vminsert|vmstorage|vmselect'| ` +
			`grep -v grep |awk {'print "kill -9 " $2'}|sh`
	logger.Info("强杀进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除软链
	extraCmd = `rm -f /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord /usr/bin/java`
	logger.Info("删除软链, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 清理profile
	extraCmd = `rm -f /etc/profile.d/vm.sh`
	logger.Info("清理profile, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
	}

	// 删除vmenv
	extraCmd = `rm -rf /data/vmenv*`
	logger.Info("删除vmenv, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除数据目录
	extraCmd = `rm -rf /data*/vmd*`
	logger.Info("删除数据目录, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 删除日志目录
	extraCmd = `rm -rf /data*/vm*`
	logger.Info("删除日志目录, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}
