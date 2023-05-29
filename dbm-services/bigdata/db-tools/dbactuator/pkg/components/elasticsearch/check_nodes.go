package elasticsearch

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/common/go-pubpkg/logger"
	"time"
)

// CheckEsNodeComp TODO
type CheckEsNodeComp struct {
	GeneralParam    *components.GeneralParam
	Params          *CheckEsNodeParams
	RollBackContext rollback.RollBackObjects
}

// CheckEsNodeParams TODO
type CheckEsNodeParams struct {
	HttpPort    int           `json:"http_port" ` // http端口
	Host        string        `json:"host" validate:"required,ip" `
	ClusterName string        `json:"cluster_name"` // 集群名
	Username    string        `json:"username"`
	Password    string        `json:"password"`
	Nodes       []esutil.Node `json:"nodes"` //
}

// Nodes TODO
type Nodes struct {
	Ip          string `json:"Ip" validate:"required"`
	InstanceNum int    `json:"instance_num"  validate:"required"`
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *CheckEsNodeComp) Init() (err error) {
	logger.Info("Reduce es node fake init")
	return nil
}

// CheckEsNodes TODO
/**
 *  @description: 剔除节点
 *  @return
 */
func (d *CheckEsNodeComp) CheckEsNodes() (err error) {
	const MaxRetry = 5
	count := 0
	// 先等待60s
	time.Sleep(60 * time.Second)

	e := esutil.EsInsObject{
		Host:     d.Params.Host,
		HttpPort: d.Params.HttpPort,
		UserName: d.Params.Username,
		Password: d.Params.Password,
	}

	nodes := d.Params.Nodes

	logger.Info("开始检查扩容的状态")
	for {
		count++
		logger.Info("开始第[%d]次检查", count)
		ok, err := e.CheckNodes(nodes)
		if ok {
			logger.Info("所有节点启动成功, %v", err)
			break
		}
		if count == MaxRetry {
			logger.Error("检查扩容状态超时, %v", err)
			return err
		}
		time.Sleep(60 * time.Second)

	}
	logger.Info("检查扩容状态完毕")

	return nil
}
