package kafka

import (
	"fmt"
	"os"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/kafkautil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/go-zookeeper/zk"
)

// DecomBrokerComp TODO
type DecomBrokerComp struct {
	GeneralParam    *components.GeneralParam
	Params          *DecomBrokerParams
	RollBackContext rollback.RollBackObjects
}

// DecomBrokerParams TODO
type DecomBrokerParams struct {
	ZookeeperIP    string   `json:"zookeeper_ip" validate:"required"`    // 连接zk
	Username       string   `json:"username"`                            // 管理用户
	Password       string   `json:"password"`                            // 管理密码
	ExcludeBrokers []string `json:"exclude_brokers" validate:"required"` // 要缩容的broker
	NewBrokers     []string `json:"new_brokers" `                        // 要扩容的broker
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *DecomBrokerComp) Init() (err error) {
	logger.Info("Clean data fake init")
	return nil
}

// DoReplaceBrokers TODO
func (d *DecomBrokerComp) DoReplaceBrokers() (err error) {

	const SleepInterval = 300 * time.Second

	zkHost := d.Params.ZookeeperIP + ":2181"
	oldBrokers := d.Params.ExcludeBrokers
	newBrokers := d.Params.NewBrokers

	conn, _, err := zk.Connect([]string{zkHost}, 10*time.Second) // *10)
	if err != nil {
		logger.Error("Connect zk failed, %s", err)
		return err
	}
	defer conn.Close()

	var newBrokerIds []string
	for _, broker := range newBrokers {
		id, err := kafkautil.GetBrokerIDByHost(conn, broker)
		if err != nil {
			logger.Error("cant get %s broker id, %v", broker, err)
			return err
		}
		newBrokerIds = append(newBrokerIds, id)
	}
	logger.Info("newBrokerIds: %v", newBrokerIds)

	for i, broker := range oldBrokers {
		oldBrokerID, err := kafkautil.GetBrokerIDByHost(conn, broker)
		logger.Info("oldBrokerId: [%s]", oldBrokerID)
		if err != nil {
			logger.Error("cant get %s broker id, %v", broker, err)
			return err
		}
		topicJSON, err := kafkautil.GenReplaceReassignmentJSON(oldBrokerID, newBrokerIds[i], zkHost)
		if err != nil {
			logger.Error("GenReassignmentJson failed", err)
			return err
		}
		logger.Info("topicJson, %s", topicJSON)
		// /data/kafkaenv/host.json
		jsonFile := fmt.Sprintf("%s/%s.json", cst.DefaultKafkaEnv, broker)
		logger.Info("jsonfile: %s", jsonFile)
		if err = os.WriteFile(jsonFile, []byte(topicJSON), 0644); err != nil {
			logger.Error("write %s failed, %v", jsonFile, err)
			return err
		}
		if !strings.Contains(topicJSON, "topic") {
			logger.Info("无需搬迁数据")
			continue
		}
		// do
		if err = kafkautil.DoReassignPartitions(zkHost, jsonFile); err != nil {
			logger.Error("DoReassignPartitions failed, %v", err)
			return err
		}
		for {

			out, err := kafkautil.CheckReassignPartitions(zkHost, jsonFile)
			if err != nil {
				logger.Error("CheckReassignPartitions failed %v", err)
				return err
			}

			if len(out) == 0 {
				logger.Info("数据搬迁完毕")
				break
			}

			time.Sleep(SleepInterval)
		}
		logger.Info("broker [%s] 搬迁 finished", broker)

	}

	return nil
}

// DoDecomBrokers 进行 Kafka broker 的缩容
func (d *DecomBrokerComp) DoDecomBrokers() (err error) {
	var id string
	// 连接到 Zookeeper
	zkHost := d.Params.ZookeeperIP + ":2181"
	conn, _, err := zk.Connect([]string{zkHost}, 10*time.Second) // *10)
	if err != nil {
		logger.Error("Connect zk failed, %s", err)
		return err
	}
	defer conn.Close()
	// 获取要缩容的 broker 的 ID
	var excludeIds []string
	for _, broker := range d.Params.ExcludeBrokers {
		id, err = kafkautil.GetBrokerIDByHost(conn, broker)
		if err != nil {
			logger.Error("cant get %s broker id, %s", broker, err)
			continue
		}
		excludeIds = append(excludeIds, id)
	}
	// 假如缩容的host已经不在kafka集群,例如机器故障已经关机了,这种情况不生成执行计划
	if len(excludeIds) == 0 {
		logger.Info("缩容的broker不在集群里面.")
		return nil
	}
	logger.Info("excludeIds: %v", excludeIds)
	// 获取主题并写入 JSON 文件
	b, err := kafkautil.WriteTopicJSON(zkHost)
	if err != nil {
		return err
	}
	if len(string(b)) == 0 {
		logger.Info("No need to do reassignment.")
		return nil
	}
	logger.Info("Creating topic.json file")
	topicJSONFile := fmt.Sprintf("%s/topic.json", cst.DefaultKafkaEnv)
	if err = os.WriteFile(topicJSONFile, b, 0644); err != nil {
		logger.Error("write %s failed, %s", topicJSONFile, err)
		return err
	}
	// 生成分区副本重分配的计划并写入 JSON 文件
	logger.Info("Creating plan.json file")
	err = kafkautil.GenReassignmentJSON(conn, zkHost, excludeIds)
	if err != nil {
		logger.Error("Create plan.json failed %s", err)
		return err
	}

	// 执行分区副本重分配
	logger.Info("Execute the plan")
	planJSONFile := cst.PlanJSONFile
	err = kafkautil.DoReassignPartitions(zkHost, planJSONFile)
	if err != nil {
		logger.Error("Execute partitions reassignment failed %s", err)
		return err
	}
	logger.Info("Execute partitions reassignment end")
	return nil
}

// DoPartitionCheck 检查Kafka分区搬迁的状态。
// 这个过程会重复检查搬迁状态，直到所有分区都成功搬迁或达到最大重试次数。
func (d *DecomBrokerComp) DoPartitionCheck() (err error) {
	// 定义最大重试次数为288次
	const MaxRetry = 288
	count := 0                                                         // 初始化计数器
	zkHost := d.Params.ZookeeperIP + ":2181"                           // 构建Zookeeper的连接字符串
	jsonFile := cst.PlanJSONFile                                       // 搬迁计划文件
	topicJSONFile := fmt.Sprintf("%s/topic.json", cst.DefaultKafkaEnv) // Kafka主题配置文件

	// 循环检查搬迁状态
	for {
		count++ // 增加重试计数
		logger.Info("检查搬迁状态，次数[%d]", count)

		// 如果topic.json文件不存在，表示没有需要检查的搬迁进度
		if !osutil.FileExist(topicJSONFile) {
			logger.Info("[%s] no exist, no need to check progress.", topicJSONFile)
			break // 退出循环
		}

		// 调用kafkautil.CheckReassignPartitions来检查搬迁进度
		out, err := kafkautil.CheckReassignPartitions(zkHost, jsonFile)
		if err != nil {
			// 如果检查失败，记录错误并返回
			logger.Error("检查partition搬迁进度失败 %v", err)
			return err
		}
		// 记录当前搬迁进度
		logger.Info("当前进度: [%s]", out)
		// 如果输出为空，表示搬迁完成
		if len(out) == 0 {
			logger.Info("数据搬迁完成")
			break // 退出循环
		}

		// 如果达到最大重试次数，记录错误并返回超时错误
		if count == MaxRetry {
			logger.Error("检查数据搬迁超时,可以选择重试")
			return fmt.Errorf("检查扩容状态超时,可以选择重试")
		}
		// 等待5分钟后再次检查
		time.Sleep(300 * time.Second)
	}

	// 搬迁完成后的日志信息
	logger.Info("分区已搬空, 若有新增topic, 请检查分区分布")
	logger.Info("清理计划文件")
	// 构建清理计划文件的命令
	extraCmd := fmt.Sprintf("rm -f %s %s %s", jsonFile, topicJSONFile, cst.RollbackFile)
	logger.Info("cmd: [%s]", extraCmd)
	// 执行清理命令
	osutil.ExecShellCommandBd(false, extraCmd)

	// 函数成功完成，返回nil
	return nil
}

// DoEmptyCheck 检查broker数据目录为空
func (d *DecomBrokerComp) DoEmptyCheck() (err error) {
	// 从配置文件中读取数据目录
	dataDirs, err := kafkautil.ReadDataDirs(cst.KafkaConfigFile)
	if err != nil {
		logger.Error("Error reading data directories from config file: %v", err)
		return err
	}
	// 检查Broker是否为空
	empty, err := kafkautil.IsBrokerEmpty(dataDirs)
	if err != nil {
		logger.Error("Error checking if the broker is empty: %v", err)
		return err
	}
	if !empty {
		errMsg := fmt.Errorf("The broker is not empty.")
		return errMsg
	}
	return nil
}
