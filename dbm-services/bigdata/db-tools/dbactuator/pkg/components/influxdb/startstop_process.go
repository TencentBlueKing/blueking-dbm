package influxdb

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// StartStopProcessComp TODO
type StartStopProcessComp struct {
	GeneralParam    *components.GeneralParam
	Params          *ProcessParams
	RollBackContext rollback.RollBackObjects
}

// ProcessParams TODO
type ProcessParams struct {
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) Init() (err error) {
	logger.Info("start stop cluster init")
	return nil
}

// StopProcess TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) StopProcess() (err error) {

	// 停止进程
	extraCmd := "supervisorctl stop all"
	logger.Info("停止所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}

// StartProcess TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) StartProcess() (err error) {

	// 启动进程
	extraCmd := "supervisorctl start all"
	logger.Info("启动所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}

// RestartProcess TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) RestartProcess() (err error) {

	// 停止进程
	extraCmd := "supervisorctl stop all"
	logger.Info("停止所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 启动进程
	extraCmd = "supervisorctl start all"
	logger.Info("启动所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}
