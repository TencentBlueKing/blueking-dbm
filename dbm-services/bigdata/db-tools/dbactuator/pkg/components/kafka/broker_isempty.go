package kafka

import (
	"fmt"
	"os"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/kafkautil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/go-zookeeper/zk"
)

// BrokerIsEmptyComp 检查broker是否可以安全移除
type BrokerIsEmptyComp struct {
	GeneralParam    *components.GeneralParam
	Params          *BrokerIsEmptyParams
	RollBackContext rollback.RollBackObjects
	CheckResult     *CheckResult // 检查结果
}

// BrokerIsEmptyParams 检查broker是否为空的参数
type BrokerIsEmptyParams struct {
	Host string `json:"host" validate:"required"` // 要检查的broker主机IP
}

// CheckResult 检查结果
type CheckResult struct {
	IsEmpty        bool              `json:"is_empty"`        // 数据目录是否为空
	PartitionCount int               `json:"partition_count"` // 分区数量
	SafeToRemove   bool              `json:"safe_to_remove"`  // 是否可以安全移除
	Reason         string            `json:"reason"`          // 原因说明
	Details        map[string]string `json:"details"`         // 详细信息
}

// Init 初始化
func (c *BrokerIsEmptyComp) Init() (err error) {
	logger.Info("BrokerIsEmptyComp Init")
	return nil
}

// BrokerIsEmpty 执行检查
func (c *BrokerIsEmptyComp) BrokerIsEmpty() (err error) {
	// 先等待60s
	time.Sleep(100 * time.Second)

	result := &CheckResult{
		Details: make(map[string]string),
	}

	// 1. 获取Kafka版本，判断是ZK模式还是KRaft模式
	version, verErr := kafkautil.GetKafkaVersion(cst.DefaultTopicBin)
	if verErr != nil {
		logger.Warn("Failed to get Kafka version: %v, assuming ZK mode", verErr)
		version = "2.4.0" // 默认使用较低版本，走ZK模式
	}
	logger.Info("Detected Kafka version: %s", version)
	result.Details["kafka_version"] = version

	useBootstrapAPI := false
	if kafkautil.CompareVersion(version, cst.Kafka400) >= 0 {
		useBootstrapAPI = true
	}

	// 2. 获取broker ID
	brokerID := ""
	if useBootstrapAPI {
		// KRaft模式：通过kafka-cluster.sh获取
		bootstrapServer, err := kafkautil.GetBootstrapServers(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get bootstrap servers: %w", err)
		}
		// 如果有鉴权配置，先生成client.properties
		if _, err := os.Stat(cst.KafkaJaasFilePath); err == nil {
			if err := kafkautil.GetClientProperties(cst.KafkaJaasFilePath, cst.KafkaClientProperties); err != nil {
				return fmt.Errorf("failed to get client properties: %w", err)
			}
		}
		clusterCmd := fmt.Sprintf("%s list-endpoints --bootstrap-server %s --config %s",
			cst.KafkaClusterBin, bootstrapServer, cst.KafkaClientProperties)
		logger.Info("Executing cluster list-endpoints command: %s", clusterCmd)
		out, err := c.execCommand(clusterCmd)
		if err != nil {
			return fmt.Errorf("failed to exec list-endpoints: %w; output: %s", err, out)
		}
		brokerID, err = kafkautil.KraftBrokerIDByIP(out, c.Params.Host)
		if err != nil {
			return fmt.Errorf("failed to get broker ID for IP %s: %w", c.Params.Host, err)
		}
	} else {
		// ZK模式：通过ZK获取
		zkHost, zkPath, err := kafkautil.GetZookeeperConnect(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get zookeeper connection: %w", err)
		}
		conn, _, err := zk.Connect([]string{zkHost}, 10*time.Second)
		if err != nil {
			return fmt.Errorf("failed to connect to zookeeper: %w", err)
		}
		defer conn.Close()
		brokerID, err = kafkautil.GetBrokerIDByHost(conn, c.Params.Host, zkPath)
		if err != nil {
			return fmt.Errorf("failed to get broker ID for IP %s: %w", c.Params.Host, err)
		}
	}
	result.Details["broker_id"] = brokerID
	result.Details["broker_ip"] = c.Params.Host

	// 3. 检查数据目录是否为空
	dataDirs, err := kafkautil.ReadDataDirs(cst.KafkaConfigFile)
	if err != nil {
		return fmt.Errorf("failed to read data directories: %w", err)
	}
	isEmpty, err := kafkautil.IsBrokerEmpty(dataDirs)
	if err != nil {
		return fmt.Errorf("failed to check if broker is empty: %w", err)
	}
	result.IsEmpty = isEmpty
	result.Details["data_dirs"] = fmt.Sprintf("%v", dataDirs)

	// 4. 获取分区数量
	var partitionCounts map[string]int
	if useBootstrapAPI {
		// KRaft模式：使用bootstrap-server
		bootstrapServer, err := kafkautil.GetBootstrapServers(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get bootstrap servers: %w", err)
		}
		endpoint := fmt.Sprintf("--bootstrap-server %s --command-config %s", bootstrapServer, cst.KafkaClientProperties)
		partitionCounts, err = kafkautil.GetBrokerPartitionCounts(endpoint)
		if err != nil {
			return fmt.Errorf("failed to get broker partition counts: %w", err)
		}
	} else {
		// ZK模式：使用zookeeper
		zkHost, zkPath, err := kafkautil.GetZookeeperConnect(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get zookeeper connection: %w", err)
		}
		endpoint := fmt.Sprintf("--zookeeper %s", zkHost+zkPath)
		partitionCounts, err = kafkautil.GetBrokerPartitionCounts(endpoint)
		if err != nil {
			return fmt.Errorf("failed to get broker partition counts: %w", err)
		}
	}

	partitionCount := partitionCounts[brokerID]
	result.PartitionCount = partitionCount

	// 5. 判断是否可以安全移除
	if isEmpty && partitionCount == 0 {
		result.SafeToRemove = true
		result.Reason = "Broker数据目录为空且没有分配任何分区，可以安全移除"
		err = nil
	} else if !isEmpty && partitionCount == 0 {
		result.SafeToRemove = true
		result.Reason = "Broker没有分配任何分区，但数据目录非空（可能存在元数据文件），请确认"
		err = fmt.Errorf("%s", result.Reason)
	} else if isEmpty && partitionCount > 0 {
		result.SafeToRemove = false
		result.Reason = fmt.Sprintf("Broker数据目录为空，但仍分配了%d个分区，请先执行分区迁移", partitionCount)
		err = fmt.Errorf("%s", result.Reason)
	} else {
		result.SafeToRemove = false
		result.Reason = fmt.Sprintf("Broker有%d个分区且数据目录非空，请先执行分区迁移", partitionCount)
		err = fmt.Errorf("%s", result.Reason)
	}

	logger.Info("Check result: SafeToRemove=%v, Reason=%s", result.SafeToRemove, result.Reason)
	c.CheckResult = result
	return err
}

// execCommand 执行shell命令
func (c *BrokerIsEmptyComp) execCommand(cmd string) (string, error) {
	return osutil.ExecShellCommandJ(false, cmd)
}
