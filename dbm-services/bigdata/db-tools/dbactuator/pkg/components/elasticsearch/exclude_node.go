package elasticsearch

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

const (
	// RetryTimes 重试次数
	RetryTimes = 200
	// WaitTime 等待时间
	WaitTime = 5 * time.Minute
)

// ExcludeEsNodeComp 是用于处理Elasticsearch节点剔除操作的组件。
type ExcludeEsNodeComp struct {
	GeneralParam    *components.GeneralParam // GeneralParam 包含一些通用的参数，如请求ID等。
	Params          *ExcludeEsNodeParams     // Params 包含执行节点剔除所需的具体参数。
	RollBackContext rollback.RollBackObjects // RollBackContext 用于在操作失败时处理回滚逻辑。
}

// ExcludeEsNodeParams 包含了执行Elasticsearch节点剔除操作所需的参数。
type ExcludeEsNodeParams struct {
	HTTPPort     int      `json:"http_port"`                   // HTTPPort 是Elasticsearch服务的HTTP端口。
	Host         string   `json:"host" validate:"required,ip"` // Host 是Elasticsearch集群的主机IP地址。
	ClusterName  string   `json:"cluster_name"`                // ClusterName 是Elasticsearch集群的名称。
	Username     string   `json:"username"`                    // Username 是用于认证的Elasticsearch用户名。
	Password     string   `json:"password"`                    // Password 是用于认证的Elasticsearch密码。
	ExcludeNodes []string `json:"exclude_nodes"`               // ExcludeNodes 是需要从集群中剔除的节点列表。
}

// Init 初始化函数
/**
 *  @description:
 *  @return
 */
func (d *ExcludeEsNodeComp) Init() (err error) {
	logger.Info("Reduce es node fake init")
	return nil
}

// ExcludeEsNode 是 ExcludeEsNodeComp 的一个方法，用于从Elasticsearch集群中剔除一个或多个节点。
//
//	@return err 返回一个error，如果操作过程中发生错误，将返回非nil的error。
func (d *ExcludeEsNodeComp) ExcludeEsNode() (err error) {
	// 使用提供的用户名和密码获取凭证。
	username, password := esutil.GetCredentials(d.Params.Username, d.Params.Password)

	// 初始化一个EsInsObject结构体实例，用于执行剔除操作。
	e := esutil.EsInsObject{
		Host:     d.Params.Host,     // Elasticsearch集群的主机地址。
		HTTPPort: d.Params.HTTPPort, // Elasticsearch集群的HTTP端口。
		UserName: username,          // 经过处理的用户名。
		Password: password,          // 经过处理的密码。
	}

	// 获取要剔除的节点列表。
	nodes := d.Params.ExcludeNodes

	// 记录开始执行剔除操作的日志。
	logger.Info("执行exclude", nodes)
	// 调用EsInsObject的DoExclude方法执行剔除操作，如果出错，记录错误日志并返回错误。
	if err := e.DoExclude(nodes); err != nil {
		logger.Error("执行exclude失败", err)
		return err
	}

	// 如果剔除操作成功，记录成功的日志。
	logger.Info("执行exclude成功")

	// 返回nil表示剔除操作成功完成。
	return nil
}

// CheckShards 检查指定节点上的shard是否已经成功搬迁。
// 如果在指定的重试次数内，shard成功搬迁，则返回nil，否则返回错误。
func (d *ExcludeEsNodeComp) CheckShards() error {
	// 从配置中获取Elasticsearch的用户名和密码。
	username, password := esutil.GetCredentials(d.Params.Username, d.Params.Password)

	// 初始化Elasticsearch实例对象，用于后续的API调用。
	e := esutil.EsInsObject{
		Host:     d.Params.Host,     // Elasticsearch集群的主机地址。
		HTTPPort: d.Params.HTTPPort, // Elasticsearch集群的HTTP端口。
		UserName: username,          // 经过处理的用户名。
		Password: password,          // 经过处理的密码。
	}

	// 获取要检查的节点列表。
	nodes := d.Params.ExcludeNodes
	// 记录开始检查节点的日志。
	logger.Info("开始检查节点是否为空")

	// 循环检查shard搬迁状态，最多重试RetryTimes次。
	for i := 0; i < RetryTimes; i++ {
		// 调用CheckEmptyOnetime方法检查节点上的shard是否已经搬迁。
		shards, ok, err := e.CheckEmptyOnetime(nodes)
		if err != nil {
			// 如果检查过程中出现错误，记录错误日志并返回错误。
			logger.Error("检查空节点失败", err)
			return err
		}

		// 如果shard已经搬迁完毕，记录日志并返回nil。
		if ok {
			logger.Info("Shard搬迁完毕")
			return nil
		}

		// 如果shard还未搬迁完毕，记录剩余shard数量的错误日志。
		errMsg := fmt.Sprintf("Shard迁移未完成, 剩余%d", shards)
		logger.Error(errMsg)

		// 等待一段时间后再次尝试，等待时间由WaitTime变量定义。
		time.Sleep(WaitTime)
	}

	// 如果经过RetryTimes次尝试后，shard仍未搬迁完毕，返回错误。
	return fmt.Errorf("经过%d次尝试后，Shard仍未完成迁移", RetryTimes)
}

// CheckConnections 检查Elasticsearch节点上的活动连接数。
// 如果没有活动连接，返回nil；如果有活动连接，返回错误。
func (d *ExcludeEsNodeComp) CheckConnections() (err error) {
	// 从结构体中获取Elasticsearch服务的主机地址和HTTP端口。
	host := d.Params.Host
	httpPort := d.Params.HTTPPort

	// 构建shell命令，使用ss工具检查与指定端口的ESTABLISHED状态的连接，
	// 并排除掉本机地址和Elasticsearch服务的主机地址。
	extraCmd := fmt.Sprintf(`ss -tn|grep ESTAB|grep -w %d|awk '{if($5 !~ "%s" && $5 !~ "127.0.0.1")  {print}}'`, httpPort,
		host)
	// 记录检查连接数的日志。
	logger.Info("检查连接数, [%s]", extraCmd)
	// 执行shell命令。
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		// 如果命令执行失败，记录错误日志并返回错误。
		logger.Error("[%s] execute failed, %v", extraCmd, err)
	}
	// 如果输出结果为空，说明没有活动连接。
	if len(strings.TrimSuffix(output, "\n")) == 0 {
		logger.Info("活动连接为空")
		err = nil
	} else {
		// 如果输出结果不为空，说明存在活动连接，记录错误日志并返回错误。
		errMsg := fmt.Sprintf("还有活动连接, %s", output)
		logger.Error(errMsg)
		err = errors.New(errMsg)
	}

	// 返回错误，如果没有活动连接则为nil，如果有则包含错误信息。
	return err
}
