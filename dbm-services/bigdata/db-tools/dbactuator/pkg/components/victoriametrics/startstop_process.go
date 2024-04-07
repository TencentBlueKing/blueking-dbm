package victoriametrics

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// StartStopProcessComp 是一个结构体，用于管理进程的启动、停止和重启。
type StartStopProcessComp struct {
	GeneralParam    *components.GeneralParam // GeneralParam 是通用参数，可能包含了一些全局设置或配置。
	Params          *StartStopParams         // Params 是清理数据的参数，目前看起来是空的，可能在后续的开发中会添加具体的参数。
	RollBackContext rollback.RollBackObjects // RollBackContext 是回滚上下文，用于在操作失败时进行回滚。
}

// StartStopParams 是一个空的结构体，可能在后续的开发中会添加具体的参数。
type StartStopParams struct{}

// Init 是 StartStopProcessComp 的初始化函数，目前只是打印一条日志，没有实际操作。
func (d *StartStopProcessComp) Init() (err error) {
	logger.Info("Fake init")
	return nil
}

// StopProcess 是停止所有进程的函数，它通过执行 "supervisorctl stop all" 命令来实现。
func (d *StartStopProcessComp) StopProcess() (err error) {
	extraCmd := cst.StopCommand
	logger.Info("停止所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

// StartProcess 是启动所有进程的函数，它通过执行 "supervisorctl start all" 命令来实现。
func (d *StartStopProcessComp) StartProcess() (err error) {
	extraCmd := cst.StartCommand
	logger.Info("启动所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

// RestartProcess 是重启所有进程的函数，它先停止所有进程，然后再启动所有进程。
func (d *StartStopProcessComp) RestartProcess() (err error) {
	extraCmd := cst.StopCommand
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = cst.StartCommand
	logger.Info("启动所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}
