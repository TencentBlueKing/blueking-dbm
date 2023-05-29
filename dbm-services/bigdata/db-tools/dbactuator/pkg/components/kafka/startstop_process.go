package kafka

import (
	"fmt"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
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
	ZookeeperIp string `json:"zookeeper_ip" ` // zookeeper ip, eg: ip1,ip2,ip3
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

	extraCmd = "ps -ef | egrep 'cmak' | grep -v grep |awk {'print \"kill -9 \" $2'}|sh"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultKafkaEnv+"/cmak-3.0.0.5/RUNNING_PID")
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

	extraCmd = "ps -ef | egrep 'cmak' | grep -v grep |awk {'print \"kill -9 \" $2'}|sh"
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

// RestartBroker TODO
/**
 *  @description:
 *  @return
 */
func (d *StartStopProcessComp) RestartBroker() (err error) {

	zookeeperIpList := strings.Split(d.Params.ZookeeperIp, ",")
	// extraCmd := fmt.Sprintf("line=`sed -n -e '/zookeeper.connect=/=' %s`", cst.DefaultKafkaEnv+"/kafka/config/server.properties")
	// if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
	//	logger.Error("%s execute failed, %v", extraCmd, err)
	//	return err
	// }
	extraCmd := fmt.Sprintf("sed -i '29c zookeeper.connect=%s:2181,%s:2181,%s:2181/' %s", zookeeperIpList[0],
		zookeeperIpList[1], zookeeperIpList[2], cst.DefaultKafkaEnv+"/kafka/config/server.properties")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	// 重启broker进程
	extraCmd = "supervisorctl restart kafka"
	logger.Info("重启broker进程, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sleep 5m")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	return nil
}
