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
	"dbm-services/common/go-pubpkg/logger"
)

// DecomBrokerComp TODO
type DecomBrokerComp struct {
	GeneralParam    *components.GeneralParam
	Params          *DecomBrokerParams
	RollBackContext rollback.RollBackObjects
}

// DecomBrokerParams TODO
type DecomBrokerParams struct {
	ZookeeperIp    string   `json:"zookeeper_ip" validate:"required"`    // 连接zk
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

	zkHost := d.Params.ZookeeperIp + ":2181"
	oldBrokers := d.Params.ExcludeBrokers
	newBrokers := d.Params.NewBrokers

	var newBrokerIds []string
	for _, broker := range newBrokers {
		id, err := kafkautil.GetBrokerIdByHost(broker, zkHost)
		if err != nil {
			logger.Error("cant get %s broker id, %v", broker, err)
			return err
		}
		newBrokerIds = append(newBrokerIds, id)
	}
	logger.Info("newBrokerIds: %v", newBrokerIds)

	for i, broker := range oldBrokers {
		oldBrokerId, err := kafkautil.GetBrokerIdByHost(broker, zkHost)
		logger.Info("oldBrokerId: [%s]", oldBrokerId)
		if err != nil {
			logger.Error("cant get %s broker id, %v", broker, err)
			return err
		}
		topicJson, err := kafkautil.GenReplaceReassignmentJson(oldBrokerId, newBrokerIds[i], zkHost)
		if err != nil {
			logger.Error("GenReassignmentJson failed", err)
			return err
		}
		logger.Info("topicJson, %s", topicJson)
		// /data/kafkaenv/host.json
		jsonFile := fmt.Sprintf("%s/%s.json", cst.DefaultKafkaEnv, broker)
		logger.Info("jsonfile: %s", jsonFile)
		if err = ioutil.WriteFile(jsonFile, []byte(topicJson), 0644); err != nil {
			logger.Error("write %s failed, %v", jsonFile, err)
			return err
		}
		if !strings.Contains(topicJson, "topic") {
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
func (d *DecomBrokerComp) DoDecomBrokers() (err error) {

	const SleepInterval = 300 * time.Second

	zkHost := d.Params.ZookeeperIp + ":2181"
	brokers := d.Params.ExcludeBrokers

	/*
		allIds, err := kafkautil.GetBrokerIds(zkHost)
		if err != nil {
			logger.Error("can't get broker ids", err)
			return err
		}
	*/
	var excludeIds []string
	for _, broker := range brokers {

		id, err := kafkautil.GetBrokerIdByHost(broker, zkHost)
		if err != nil {
			logger.Error("cant get %s broker id, %v", broker, err)
			return err
		}
		excludeIds = append(excludeIds, id)
	}
	logger.Info("excludeIds: %v", excludeIds)

	for _, broker := range brokers {
		brokerId, err := kafkautil.GetBrokerIdByHost(broker, zkHost)
		logger.Info("brokerId: [%s]", brokerId)
		if err != nil {
			logger.Error("cant get %s broker id, %v", broker, err)
			return err
		}
		topicJson, err := kafkautil.GenReassignmentJson(brokerId, zkHost, excludeIds)
		if err != nil {
			logger.Error("GenReassignmentJson failed", err)
			return err
		}
		logger.Info("topicJson, %s", topicJson)
		// /data/kafkaenv/host.json
		jsonFile := fmt.Sprintf("%s/%s.json", cst.DefaultKafkaEnv, broker)
		logger.Info("jsonfile: %s", jsonFile)
		if err = ioutil.WriteFile(jsonFile, []byte(topicJson), 0644); err != nil {
			logger.Error("write %s failed, %v", jsonFile, err)
			return err
		}
		if !strings.Contains(topicJson, "topic") {
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

// DoPartitionCheck TODO
func (d *DecomBrokerComp) DoPartitionCheck() (err error) {
	const MaxRetry = 5
	count := 0
	zkHost := d.Params.ZookeeperIp + ":2181"
	brokers := d.Params.ExcludeBrokers
	for {
		count++
		logger.Info("检查搬迁状态，次数[%d]", count)
		sum := 0
		for _, broker := range brokers {
			jsonFile := fmt.Sprintf("%s/%s.json", cst.DefaultKafkaEnv, broker)

			out, err := kafkautil.CheckReassignPartitions(zkHost, jsonFile)
			if err != nil {
				logger.Error("检查partition搬迁进度失败 %v", err)
				return err
			}
			sum += len(out)
		}

		if sum == 0 {
			logger.Info("数据搬迁完成")
			break
		}

		if count == MaxRetry {
			logger.Error("检查数据搬迁超时,可以选择重试")
			return fmt.Errorf("检查扩容状态超时,可以选择重试")
		}
		time.Sleep(60 * time.Second)
	}

	logger.Info("数据变迁完毕")

	return nil
}
