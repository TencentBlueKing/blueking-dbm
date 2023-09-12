package elasticsearch

import (
	"errors"
	"fmt"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ExcludeEsNodeComp TODO
type ExcludeEsNodeComp struct {
	GeneralParam    *components.GeneralParam
	Params          *ExcludeEsNodeParams
	RollBackContext rollback.RollBackObjects
}

// ExcludeEsNodeParams TODO
type ExcludeEsNodeParams struct {
	HTTPPort     int      `json:"http_port"` // http端口
	Host         string   `json:"host" validate:"required,ip"`
	ClusterName  string   `json:"cluster_name"` // 集群名
	Username     string   `json:"username"`
	Password     string   `json:"password"`
	ExcludeNodes []string `json:"exclude_nodes"` //
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *ExcludeEsNodeComp) Init() (err error) {
	logger.Info("Reduce es node fake init")
	return nil
}

// ExcludeEsNode TODO
/**
 *  @description: 剔除节点
 *  @return
 */
func (d *ExcludeEsNodeComp) ExcludeEsNode() (err error) {
	e := esutil.EsInsObject{
		Host:     d.Params.Host,
		HttpPort: d.Params.HTTPPort,
		UserName: d.Params.Username,
		Password: d.Params.Password,
	}

	nodes := d.Params.ExcludeNodes

	logger.Info("执行exclude", nodes)
	if err := e.DoExclude(nodes); err != nil {
		logger.Error("执行exclude失败", err)
		return err
	}

	/* 放在后面做
	logger.Info("检查节点是否为空")
	if err := e.CheckEmpty(nodes); err != nil {
		logger.Error("检查空节点失败", err)
		return err
	}
	*/

	logger.Info("执行exclud成功")

	return nil
}

// CheckShards TODO
func (d *ExcludeEsNodeComp) CheckShards() (err error) {
	e := esutil.EsInsObject{
		Host:     d.Params.Host,
		HttpPort: d.Params.HTTPPort,
		UserName: d.Params.Username,
		Password: d.Params.Password,
	}

	nodes := d.Params.ExcludeNodes
	logger.Info("检查节点是否为空")
	shards, ok, err := e.CheckEmptyOnetime(nodes)
	if err != nil {
		logger.Error("检查空节点失败", err)
		return err
	}

	if ok {
		logger.Info("Shard搬迁完毕")
		err = nil
	} else {
		errMsg := fmt.Sprintf("Shard变迁未完成, 剩余%d", shards)
		logger.Error(errMsg)
		err = errors.New(errMsg)
	}

	return err
}

// CheckConnections TODO
func (d *ExcludeEsNodeComp) CheckConnections() (err error) {

	host := d.Params.Host
	httpPort := d.Params.HTTPPort

	extraCmd := fmt.Sprintf(`ss -tn|grep ESTAB|grep -w %d|awk '{if($5 !~ "%s" && $5 !~ "127.0.0.1")  {print}}'`, httpPort,
		host)
	logger.Info("检查连接数, [%s]", extraCmd)
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
	}
	if len(strings.TrimSuffix(output, "\n")) == 0 {
		logger.Info("活动连接为空")
		err = nil
	} else {
		errMsg := fmt.Sprintf("还有活动连接, %s", output)
		logger.Error(errMsg)
		err = errors.New(errMsg)
	}

	return err
}
