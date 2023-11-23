package kafka

import (
	"fmt"
	"io/ioutil"
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
		if err = ioutil.WriteFile(jsonFile, []byte(topicJSON), 0644); err != nil {
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

// DoDecomBrokers TODO
/**
 *  @description:
 *  @return
 */
func (d *DecomBrokerComp) DoDecomBrokers() error {

	zkHost := d.Params.ZookeeperIP + ":2181"
	brokers := d.Params.ExcludeBrokers

	// connect to zk
	conn, _, err := zk.Connect([]string{zkHost}, 10*time.Second) // *10)
	if err != nil {
		logger.Error("Connect zk failed, %s", err)
		return err
	}
	defer conn.Close()

	/*
		allIds, err := kafkautil.GetBrokerIds(zkHost)
		if err != nil {
			logger.Error("can't get broker ids", err)
			return err
		}
	*/
	var excludeIds []string
	for _, broker := range brokers {

		id, err := kafkautil.GetBrokerIDByHost(conn, broker)
		if err != nil {
			logger.Error("cant get %s broker id, %s", broker, err)
			return err
		}
		excludeIds = append(excludeIds, id)
	}
	logger.Info("excludeIds: %v", excludeIds)
	// Get topics
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
	if err := ioutil.WriteFile(topicJSONFile, b, 0644); err != nil {
		logger.Error("write %s failed, %s", topicJSONFile, err)
		return err
	}

	logger.Info("Creating plan.json file")
	err = kafkautil.GenReassignmentJSON(conn, zkHost, excludeIds)
	if err != nil {
		logger.Error("Create plan.json failed %s", err)
		return err
	}

	logger.Info("Execute the plan")
	planJSONFile := fmt.Sprintf("%s/plan.json", cst.DefaultKafkaEnv)
	err = kafkautil.DoReassignPartitions(zkHost, planJSONFile)
	if err != nil {
		logger.Error("Execute partitions reassignment failed %s", err)
		return err
	}
	logger.Info("Execute partitions reassignment end")
	return nil
}

// DoPartitionCheck TODO
func (d *DecomBrokerComp) DoPartitionCheck() (err error) {
	const MaxRetry = 5
	count := 0
	zkHost := d.Params.ZookeeperIP + ":2181"
	jsonFile := fmt.Sprintf("%s/plan.json", cst.DefaultKafkaEnv)
	topicJSONFile := fmt.Sprintf("%s/topic.json", cst.DefaultKafkaEnv)

	for {
		count++
		logger.Info("检查搬迁状态，次数[%d]", count)

		if !osutil.FileExist(topicJSONFile) {
			logger.Info("[%s] no exist, no need to check progress.")
			break
		}

		out, err := kafkautil.CheckReassignPartitions(zkHost, jsonFile)
		if err != nil {
			logger.Error("检查partition搬迁进度失败 %v", err)
			return err
		}
		logger.Info("当前进度: [%s]", out)
		if len(out) == 0 {
			logger.Info("数据搬迁完成")
			break
		}

		if count == MaxRetry {
			logger.Error("检查数据搬迁超时,可以选择重试")
			return fmt.Errorf("检查扩容状态超时,可以选择重试")
		}
		time.Sleep(60 * time.Second)
	}

	logger.Info("分区已搬空, 若有新增topic, 请检查分区分布")
	logger.Info("清理计划文件")
	extraCmd := fmt.Sprintf("rm -f %s %s", jsonFile, topicJSONFile)
	logger.Info("cmd: [%s]", extraCmd)
	osutil.ExecShellCommandBd(false, extraCmd)

	return nil
}
