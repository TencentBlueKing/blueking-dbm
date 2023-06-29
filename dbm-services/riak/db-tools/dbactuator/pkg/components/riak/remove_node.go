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
)

// RemoveNodeComp TODO
type RemoveNodeComp struct {
	Params               *RemoveNodeParam `json:"extend"`
	RemoveNodeRunTimeCtx `json:"-"`
}

// RemoveNodeParam TODO
type RemoveNodeParam struct {
	OperateNodes *[]string `json:"operate_nodes"  validate:"required"`
}

// RemoveNodeRunTimeCtx 运行时上下文
type RemoveNodeRunTimeCtx struct {
	LocalIp     string
	NodesStatus map[string]string
}

// PreCheck 预检查
func (i *RemoveNodeComp) PreCheck() error {
	// 检查本节点的状态，是否正常启动
	_, err := osutil.ExecShellCommand(false, cst.ClusterStatusCmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cst.ClusterStatusCmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cst.ClusterStatusCmd, err.Error())
		return err
	}
	// 获取所有节点的状态
	cmd := fmt.Sprintf(`%s | grep riak | cut -d'@' -f2 | 
	awk '{print $1" "$4}' | sed 's/|//g'`, cst.ClusterStatusCmd)
	res, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute shell [%s] error: %s", cmd, err.Error())
		err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
		return err
	}
	logger.Info("riak node status:\n%s", res)
	lines := strings.Split(strings.TrimSuffix(strings.TrimPrefix(res, "\n"), "\n"), "\n")
	i.NodesStatus = make(map[string]string)
	for _, l := range lines {
		node := strings.Split(l, " ")
		ip := strings.Trim(node[0], " ")
		status := strings.Trim(node[1], " ")
		i.NodesStatus[ip] = status
		// 集群中存在不在运行中的riak节点
		if strings.Contains(status, "down") {
			logger.Warn("riak node %s status: %s", ip, status)
		}
	}
	logger.Info("riak cluster status check success")
	return nil
}

// MarkInvalidNodeDown 标志集群中故障的节点为down，保障集群ring正常
func (i *RemoveNodeComp) MarkInvalidNodeDown() error {
	for k, v := range i.NodesStatus {
		if v == "down!" {
			// 标志故障的节点为down
			cmd := fmt.Sprintf("riak-admin down riak@%s", k)
			_, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				logger.Error("execute shell [%s] error: %s", cmd, err.Error())
				return fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
			}
			logger.Info("execute shell [%s] success", cmd)
		}
	}
	return nil
}

// RemoveNode 集群剔除节点
func (i *RemoveNodeComp) RemoveNode() error {
	for _, ip := range *i.Params.OperateNodes {
		// 剔除节点
		cmd := fmt.Sprintf("riak-admin cluster leave riak@%s", ip)
		// 待剔除的节点，是否在集群中
		status := i.NodesStatus[ip]
		if status == "" {
			logger.Error("'riak@%s' is not a member of the cluster", ip)
			return fmt.Errorf("'riak@%s' is not a member of the cluster", ip)
		}
		// 待剔除的节点没有运行，强制剔除，不搬迁节点上的数据
		if strings.Contains(status, "down") {
			cmd = fmt.Sprintf("riak-admin cluster force-remove riak@%s", ip)
		}
		_, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			logger.Error("execute shell [%s] error: %s", cmd, err.Error())
			err = fmt.Errorf("execute shell [%s] error: %s", cmd, err.Error())
			return err
		}
	}
	logger.Info("remove node success")
	return nil
}
