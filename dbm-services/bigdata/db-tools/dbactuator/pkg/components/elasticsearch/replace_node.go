package elasticsearch

import (
	"fmt"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ReplaceEsNodeComp 是一个组件，负责替换 Elasticsearch 集群中的主节点。
type ReplaceEsNodeComp struct {
	GeneralParam    *components.GeneralParam // 可能在不同方法中使用的通用参数。
	Params          *ReplaceEsNodeParams     // 替换主节点所需的特定参数。
	RollBackContext rollback.RollBackObjects // 如果需要，用于回滚更改的上下文或状态。
}

// ReplaceEsNodeParams 包含替换 Elasticsearch 集群中主节点的特定参数。
type ReplaceEsNodeParams struct {
	Masters []string `json:"masters"` // 新主节点的 IP 或主机名列表。
}

// Init 是用于初始化 ReplaceEsNodeComp 组件的方法。
// 目前，它只记录一个信息性消息，并不执行任何初始化逻辑。
func (r *ReplaceEsNodeComp) Init() (err error) {
	logger.Info("Reduce es node fake init") // 记录一个消息，表明 init 方法已被调用。
	return nil                              // 返回 nil，因为没有实际的初始化逻辑。
}

// ReplaceMasterNode 更新 Elasticsearch 集群的主节点配置。
func (r *ReplaceEsNodeComp) ReplaceMasterNode() (err error) {
	// 从 Params 中提取主节点 IP。
	masters := r.Params.Masters
	// 将主节点 IP 连接成逗号分隔的字符串。
	ipStr := strings.Join(masters[:], ",")
	// 将主节点 IP 转换成 Elasticsearch 所需的主节点字符串格式。
	masterStr := esutil.ToMasterStr(masters)
	// 为 Elasticsearch 配置格式化种子主机。
	seedHosts := fmt.Sprintf("[%s]", ipStr)
	// 为 Elasticsearch 配置格式化初始主节点。
	initMaster := fmt.Sprintf("[%s]", masterStr)
	// 定义 Elasticsearch 目录的环境变量。
	esenv := cst.DefaulEsEnv
	// 创建 Elasticsearch YAML 配置路径的通配符模式。
	yamlPaths := fmt.Sprintf(`%s/es_*/config/elasticsearch.yml`, esenv)

	// 构造 sed 命令以更新 Elasticsearch 配置文件。
	extraCmd := fmt.Sprintf(
		`sed -i -e '/seed_hosts/s/\[.*\]/%s/' `+
			`-e '/initial_master_nodes/s/\[.*\]/%s/' `+
			`-e '/zen.ping.unicast.hosts/s/\[.*\]/%s/' %s`,
		seedHosts, initMaster, seedHosts, yamlPaths)
	// 记录将要执行的命令。
	logger.Info("更新master, [%s]", extraCmd)

	// 使用 shell 执行 sed 命令，以处理通配符扩展和空白字符。
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		// 如果出现错误，记录错误并返回错误。
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	// 如果命令执行成功，返回 nil，表示没有发生错误。
	return nil
}
