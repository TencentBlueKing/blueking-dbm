// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"strings"
	"time"
)

// UninstallComp TODO
type UninstallComp struct {
	Params              *UninstallParam `json:"extend"`
	UninstallRunTimeCtx `json:"-"`
}

// UninstallParam TODO
type UninstallParam struct {
	Stopped *bool `json:"stopped"  validate:"required"`
}

// UninstallRunTimeCtx 运行时上下文
type UninstallRunTimeCtx struct {
}

// PreCheck 下架预检查
func (i *UninstallComp) PreCheck() error {
	var cnt int
	var res string
	var err error
	// 每10秒检查一次状态，集群剔除节点后，节点可能没有马上自动关闭，等待10分钟
	// 集群下架前，需要禁用集群，节点已关闭，检查一次即可
	max := 1
	if *i.Params.Stopped == false {
		max = 60
		logger.Info("check riak status every 10s")
	}

	for cnt = 1; cnt <= max; cnt++ {
		res, err = osutil.ExecShellCommand(false, cst.ClusterStatusCmd)
		if err != nil {
			if strings.Contains(err.Error(), "Node did not respond to ping!") {
				logger.Info(err.Error())
				break
			} else {
				logger.Error("execute shell [%s] error: %s", cst.ClusterStatusCmd, err.Error())
				err = fmt.Errorf("execute shell [%s] error: %s", cst.ClusterStatusCmd, err.Error())
				return err
			}
		}
		logger.Info("%d check, riak still running", cnt)
		time.Sleep(10 * time.Second)
	}
	// 本来应该自动关闭的实例一直未关闭，检查失败
	if cnt == max+1 {
		logger.Error("riak still running. execute shell [%s], output:%s", cst.ClusterStatusCmd, res)
		err = fmt.Errorf("riak still running. execute shell [%s], output:%s", cst.ClusterStatusCmd, res)
		return err
	}
	// 检查是否有riak进程
	cmd := `ps -ef | grep riak | grep -v 'grep' | grep -v 'epmd -daemon' | grep -v dbactuator`
	res, err = osutil.ExecShellCommand(false, cmd)
	if err == nil {
		logger.Error("riak still running. execute shell [%s], output:%s", cmd, res)
		err = fmt.Errorf("riak still running. execute shell [%s], output:%s", cmd, res)
		return err
	}
	logger.Info("uninstall riak node precheck complete")
	return nil
}

// Uninstall 下架
func (i *UninstallComp) Uninstall() error {
	// 关闭守护进程
	killDaemon := `ps -ef | grep 'epmd -daemon' | grep riak | grep -v grep | awk '{print "kill -9 "$2";"}' | sh`
	vtime := time.Now().Local().Format(cst.TimeLayoutDir)
	// 清理riak数据以及日志文件
	fileBak := fmt.Sprintf("mv %s/riak %s/riak.bak.%s", cst.DefaultDataRootPath, cst.DefaultDataRootPath, vtime)
	fileBak2 := fmt.Sprintf("mv %s/riak %s/riak.bak.%s", cst.AlterNativeDataRootPath, cst.AlterNativeDataRootPath, vtime)
	fileBak3 := fmt.Sprintf("mv %s %s.bak.%s", cst.MonitorPath, cst.MonitorPath, vtime)
	cmds := []string{killDaemon, fileBak, fileBak2, fileBak3}

	for _, cmd := range cmds {
		res, err := osutil.ExecShellCommand(false, cmd)
		if err != nil && !strings.Contains(err.Error(), "No such file or directory") {
			// 存在则清理，不存在，清理失败可忽略报错
			logger.Info("execute shell [%s] error: %s", cmd, err.Error())
		} else if err == nil {
			logger.Info("execute shell [%s] output: %s", cmd, res)
		}
	}
	logger.Info("uninstall riak node complete")
	return nil
}
