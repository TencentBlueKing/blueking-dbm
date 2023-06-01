package elasticsearch

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
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
	Node string `json:"node"`
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) Init() (err error) {
	logger.Info("Destory cluster fake init")
	return nil
}

// StopProcess TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) StopProcess() (err error) {

	// 停止进程
	node := d.Params.Node
	processId, err := esutil.GetNumByNode(node)
	if err != nil {
		return err
	}
	extraCmd := fmt.Sprintf("supervisorctl stop %s", processId)
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
	node := d.Params.Node
	processId, err := esutil.GetNumByNode(node)
	if err != nil {
		return err
	}
	extraCmd := fmt.Sprintf("supervisorctl start %s", processId)
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
	node := d.Params.Node
	processId, err := esutil.GetNumByNode(node)
	if err != nil {
		return err
	}
	extraCmd := fmt.Sprintf("supervisorctl stop %s", processId)
	logger.Info("停止所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 启动进程
	extraCmd = fmt.Sprintf("supervisorctl start %s", processId)
	logger.Info("启动所有进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}
