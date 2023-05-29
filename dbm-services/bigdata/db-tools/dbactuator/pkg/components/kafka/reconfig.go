package kafka

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
)

// ReconfigComp TODO
type ReconfigComp struct {
	GeneralParam    *components.GeneralParam
	Params          *ReconfigParams
	RollBackContext rollback.RollBackObjects
}

// ReconfigParams TODO
type ReconfigParams struct {
	Host string `json:"host" `
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (r *ReconfigComp) Init() (err error) {
	logger.Info("reconfig init")
	return nil
}

// ReconfigAdd TODO
/**
 *  @description:
 *  @return
 */
func (r *ReconfigComp) ReconfigAdd() (err error) {
	// 增加zookeeper
	extraCmd := fmt.Sprintf(`%s/zk/bin/zkCli.sh reconfig -file %s`, cst.DefaultKafkaEnv, cst.DefaultZookeeperDynamicConf)
	osutil.ExecShellCommand(false, extraCmd)

	extraCmd = fmt.Sprintf("sleep 5m")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}

// ReconfigRemove TODO
/**
 *  @description:
 *  @return
 */
func (r *ReconfigComp) ReconfigRemove() (err error) {
	// 减少zookeeper
	extraCmd := fmt.Sprintf(`%s/zk/bin/zkCli.sh reconfig -remove %s`, cst.DefaultKafkaEnv, r.Params.Host)
	osutil.ExecShellCommand(false, extraCmd)

	extraCmd = fmt.Sprintf("sleep 5m")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}
