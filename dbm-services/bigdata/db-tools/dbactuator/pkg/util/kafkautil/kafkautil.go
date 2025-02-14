// Package kafkautil TODO
package kafkautil

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/go-zookeeper/zk"
)

// TP define topic
type TP struct {
	Topic string `json:"topic"`
}

// TPs topic.json struct
type TPs struct {
	Topics  []TP `json:"topics"`
	Version int  `json:"version"`
}

// GetHostByID ZooKeeper中获取特定ID的broker信息
func GetHostByID(conn *zk.Conn, id string) (string, error) {
	// 构造ZooKeeper中broker信息的路径
	path := fmt.Sprintf("/brokers/ids/%s", id)

	// 从ZooKeeper获取broker信息
	data, _, err := conn.Get(path)
	if err != nil {
		logger.Error("get %s failed: %s", path, err)
		return "", err // 返回错误信息
	}

	// 解析JSON数据
	var result map[string]interface{}
	if err = json.Unmarshal(data, &result); err != nil {
		logger.Error("Parse json failed, %s", err)
		return "", err // JSON解析失败，返回错误
	}

	// 确保endpoints字段存在且为非空数组
	endpoints, ok := result["endpoints"].([]interface{})
	if !ok || len(endpoints) == 0 {
		return "", fmt.Errorf("endpoints not found or empty in broker %s data", id)
	}

	// 假设第一个endpoint是我们需要的host信息
	ep, ok := endpoints[0].(string)
	if !ok {
		return "", fmt.Errorf("endpoint format is invalid for broker %s", id)
	}

	// 使用正则表达式去除协议部分（如"http://"或"kafka://"）
	m1 := regexp.MustCompile(`.*://`)
	hostPort := m1.ReplaceAllString(ep, "")

	// 分割字符串以获取host部分
	hostParts := strings.Split(hostPort, ":")
	if len(hostParts) == 0 {
		return "", fmt.Errorf("invalid hostport format for broker %s", id)
	}
	brokerHost := hostParts[0] // 取出host部分

	logger.Info("brokerHost:[%s]", brokerHost)
	return brokerHost, nil // 返回broker的host
}

// GetBrokerIds TODO
func GetBrokerIds(conn *zk.Conn) ([]string, error) {
	// zk: ls /brokers/ids
	// output: [0,1,2]
	ids, _, err := conn.Children("/brokers/ids")
	if err != nil {
		logger.Error("Get broker ids failed, %s", err)
		return ids, err
	}

	logger.Info("Broker ids: %v", ids)
	return ids, nil
}

// GetBrokerIDByHost 根据host返回brokerid, brokerhost -> 0
func GetBrokerIDByHost(conn *zk.Conn, host string) (string, error) {
	logger.Info("Getting broker id of host ...")

	// Retrieve all broker IDs from ZooKeeper.
	ids, err := GetBrokerIds(conn)
	if err != nil {
		logger.Error("Can't get broker ids, %s", err)
		return "", err // Return the error if we can't get the broker IDs.
	}

	// Check if the list of broker IDs is empty.
	if len(ids) == 0 {
		return "", fmt.Errorf("no broker ids found")
	}

	// Iterate over the broker IDs to find a matching host.
	for _, kfid := range ids {
		kfHost, err := GetHostByID(conn, kfid)
		if err != nil {
			// Log the error and continue checking the next ID.
			logger.Error("Can't get host by id, %s", err)
			continue
		}
		// Check if the retrieved host matches the given host.
		if kfHost == host {
			logger.Info("host:[%s] id is [%s]", kfHost, kfid)
			return kfid, nil
		}
	}

	// If we reach this point, it means no matching host was found
	return "", fmt.Errorf("broker id for host %s not found", host)
}

// PickRandom TODO
func PickRandom(arr []string) string {
	rand.Seed(time.Now().Unix())
	return arr[rand.Intn(len(arr))]
}

// GenReassignmentJSON TODO
func GenReassignmentJSON(conn *zk.Conn, zk string, xBrokerIds []string) error {
	idsArr, _ := GetBrokerIds(conn)
	logger.Info("idsArr %v", idsArr)
	tempArr := make([]string, len(idsArr))
	copy(tempArr, idsArr)
	// 剔除缩容的ids
	for _, id := range xBrokerIds {
		tempArr = findAndDelete(tempArr, id)
	}
	logger.Info("tempArr %v", tempArr)
	logger.Info("idsArr %v", idsArr)

	// 获取brokerid, eg: 1,2,3
	tempIds := strings.Join(tempArr[:], ",")

	planJSONFile := cst.PlanJSONFile
	extraCmd := fmt.Sprintf("%s --topics-to-move-json-file %s/topic.json --generate --zookeeper %s --broker-list %s >%s",
		cst.DefaultReassignPartitionsBin, cst.DefaultKafkaEnv, zk, tempIds, planJSONFile)

	logger.Info("extraCmd, %s", extraCmd)
	output, _ := osutil.ExecShellCommand(false, extraCmd)
	logger.Info("output: %s", output)
	b, err := os.ReadFile(planJSONFile)
	if err != nil {
		logger.Error("Cant read plan.json, %s", err)
		return err
	}
	// plan.json content
	s := string(b)
	failedKeyWord := "Partitions reassignment failed"
	if strings.Contains(s, failedKeyWord) {
		logger.Error(s)
		return fmt.Errorf(s)
	}

	// 生成rollback.json
	rollbackFile := cst.RollbackFile
	// sed -n '2p' plan.json  >rollback.json
	extraCmd = fmt.Sprintf("sed -n '2p' %s  > %s", planJSONFile, rollbackFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("sed plan.json failed, %s", err)
		return err
	}

	// Delete Current part
	extraCmd = fmt.Sprintf("sed -i '1,4d'  %s", planJSONFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("sed plan.json failed, %s", err)
		return err
	}
	// 判断缩容的host是否还有partiton,对应已经提前均衡的情况，执行也不应该跑执行计划
	jsonFile, err := os.Open(rollbackFile)
	if err != nil {
		logger.Error("Error opening JSON file[%s]: %s", rollbackFile, err)
		return err
	}
	defer jsonFile.Close()
	byteValue, err := io.ReadAll(jsonFile)
	if err != nil {
		logger.Error("Error reading JSON file: %s", err)
		return err
	}
	var config KafkaConfig
	if err = json.Unmarshal(byteValue, &config); err != nil {
		logger.Error("Error unmarshalling JSON: %s", err)
		return err
	}
	if notPresent := CheckReplicas(config, xBrokerIds); notPresent {
		logger.Info("缩容的broker没有topic.将rollback.json做为执行计划")
		_ = RollbackPlan()
	}
	logger.Info("Generate plan.json done")
	return nil
}

// GenReplaceReassignmentJSON TODO
func GenReplaceReassignmentJSON(oldBrokerID string, newBrokerID string, zk string) (output string, err error) {
	extraCmd := fmt.Sprintf(`
	json="{\n"
	json="$json  \"partitions\": [\n"

	for topicPartitionReplicas in $(%s --zookeeper %s --describe | awk '{ print $2"#"$4"#"$6"#"$8 }'); do
	  IFS=$'#' read -a array <<< "$topicPartitionReplicas"
	  topic="${array[0]}"     # e.g. "zerg.hydra"
	  partition="${array[1]}" # e.g. "4"
	  leaders="${array[2]}"
	  replicas="${array[3]}"  # e.g. "0,8"  (= comma-separated list of broker IDs)
	  if [[ $replicas =~ %s ]];then 
	  	new_replicas=${replicas/%s/%s}
	  	if [ -z "$new_replicas" ]; then
			echo "ERROR: Cannot find any replacement broker.  Maybe you have only a single broker in your cluster?"
			exit 60
	  	fi
	  	json="$json    {\"topic\": \"${topic}\", \"partition\": ${partition}, \"replicas\": [${new_replicas}] },\n"
	  fi
	done

	# Remove tailing comma, if any.
	json=${json%%",\n"}
	json="${json}\n"

	# "Footer" of JSON file
	json="$json  ],\n"
	json="$json  \"version\": 1\n"
	json="${json}}\n"

	# Print JSON to STDOUT
	echo -e $json
	`, cst.DefaultTopicBin, zk, oldBrokerID, oldBrokerID, newBrokerID)
	logger.Info("extraCmd, %s", extraCmd)
	if output, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("gen json failed, %s, %s", output, err.Error())
		return "", err
	}
	logger.Info("output %s", output)

	return output, nil
}

// DoReassignPartitions TODO
func DoReassignPartitions(zk string, jsonFile string) error {

	// default limit 30MB/s
	speedLimit := 30000000
	extraCmd := fmt.Sprintf(`%s --zookeeper %s --reassignment-json-file %s --throttle %d --execute `,
		cst.DefaultReassignPartitionsBin,
		zk, jsonFile, speedLimit)
	logger.Info("extraCmd: %s", extraCmd)
	output, _ := osutil.ExecShellCommand(false, extraCmd)
	logger.Info("output %s", output)
	logger.Info("Doing patitions reassignment, default speed rate is 30MB/s")
	logger.Info("Changing the rate, please rerun [%s] with other rate", extraCmd)
	return nil
}

// CheckReassignPartitions TODO
func CheckReassignPartitions(zk string, jsonFile string) (output string, err error) {
	extraCmd := fmt.Sprintf(`%s --zookeeper %s --reassignment-json-file %s --verify|egrep -v 'Status|successfully'`,
		cst.DefaultReassignPartitionsBin,
		zk, jsonFile)
	logger.Info("cmd: [%s]", extraCmd)
	// 这里不判断status状态
	output, _, _ = osutil.ExecShellCommandBd(false, extraCmd)
	logger.Info("output %s", output)
	return strings.TrimSuffix(output, "\n"), nil
}

// GetTopics return topic list
func GetTopics(zk string) (topicList []string, err error) {
	extraCmd := fmt.Sprintf(`%s --zookeeper %s --list`, cst.DefaultTopicBin, zk)
	logger.Info("cmd: [%s]", extraCmd)
	output, _, _ := osutil.ExecShellCommandBd(false, extraCmd)
	logger.Info("output %s", output)
	// empty output, return empty list
	if output == "" {
		return topicList, nil
	}
	topicList = strings.Split(strings.TrimSuffix(output, "\n"), "\n")
	return topicList, nil
}

// WriteTopicJSON TODO
func WriteTopicJSON(zk string) (b []byte, err error) {
	topics, err := GetTopics(zk)
	if err != nil {
		logger.Error("Get topics list failed, %s", err)
		return b, err
	}

	logger.Info("topics: [%d]", len(topics))
	// if no topic, nothing
	if len(topics) == 0 {
		logger.Info("No topics found.")
		b = []byte("")
	} else {
		logger.Info("Topics list %v", topics)
		var tps []TP
		for _, t := range topics {
			tps = append(tps, TP{Topic: t})
		}
		tpJSON := &TPs{
			Topics:  tps,
			Version: 1,
		}
		b, err = json.Marshal(tpJSON)
		if err != nil {
			logger.Info("Pase topic json failed, %s", err)
			return b, err
		}
		logger.Info("topic.json: %s", string(b))
	}

	return b, nil
}

// GenerateReassginFile TODO
func GenerateReassginFile(zk, topic, idStrs, host string) error {
	topicJSON := fmt.Sprintf(`
	{
		"version": 1,
		"topics": [
			{ "topic": "%s"}
		]
	}`, topic)
	topicFile := "/tmp/topic.json"
	if err := os.WriteFile(topicFile, []byte(topicJSON), 0644); err != nil {
		logger.Error("write %s failed, %v", topicFile, err)
		return err
	}
	extraCmd := fmt.Sprintf(
		`%s  --zookeeper %s  --topics-to-move-json-file %s \
		--broker-list %s --generate | egrep -A1 ^Proposed|egrep -v ^Proposed`,
		cst.DefaultReassignPartitionsBin,
		zk, topicFile, idStrs)
	logger.Info("cmd: [%s]", extraCmd)
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("生成迁移计划失败, %v", err)
		return err
	}
	logger.Info("迁移计划json: [%s]", output)
	// /data/kafkaenv/{host}/topic1.json
	jsonDir := fmt.Sprintf("%s/%s", cst.DefaultKafkaEnv, host)
	// mkdir
	extraCmd = fmt.Sprintf("mkdir -p %s", jsonDir)
	logger.Info("cmd: [%s]", extraCmd)
	_, err = osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("创建目录失败, %v", err)
		return err
	}

	planJSONFile := fmt.Sprintf("%s/%s.json", jsonDir, topic)
	if err := os.WriteFile(planJSONFile, []byte(output), 0644); err != nil {
		logger.Error("write %s failed, %v", planJSONFile, err)
		return err
	}
	return nil
}

func findAndDelete(s []string, item string) []string {
	index := 0
	for _, i := range s {
		if i != item {
			s[index] = i
			index++
		}
	}
	return s[:index]
}

// ExporterParam exporter参数写入环境变量
func ExporterParam(noSecurity int, username, password, version string) error {
	// noSecurity, 1:无鉴权, 0:有鉴权
	param := ""
	authParam := fmt.Sprintf(
		`export SASL_USERNAME="%s"
	export SASL_PASSWORD="%s"
	export SASL_MECHANISM=scram-sha512
	export SASL_ENABLED=true`,
		username, password)
	if version == "0.10.2" {
		param = param + "export KAFKA_VERSION=0.10.2.1"
		if noSecurity == 0 {
			param = param + "\n" + authParam
		}
	} else {
		if noSecurity == 0 {
			param = param + authParam
		}
	}
	logger.Info("Exporter parameter is %s", param)

	// Write to env
	extraCmd := fmt.Sprintf(`echo '%s'  > /etc/profile.d/kafka.sh`, param)
	logger.Info("cmd: [%s]", extraCmd)
	_, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("写入/etc/profile.d/kafka.sh失败 %s", err)
		return err
	}
	// make env worked
	extraCmd = "source /etc/profile"
	logger.Info("cmd :[%s]", extraCmd)
	_, _ = osutil.ExecShellCommand(false, extraCmd)

	return nil
}

// KafkaConfig matches the JSON structure for easy unmarshalling.
type KafkaConfig struct {
	Version    int `json:"version"`
	Partitions []struct {
		Replicas []int `json:"replicas"`
	} `json:"partitions"`
}

// CheckReplicas checks if the given numbers are not present in any replicas list.
func CheckReplicas(config KafkaConfig, numbersToCheck []string) bool {
	// Create a map to store the presence of numbers in replicas
	replicaMap := make(map[int]bool)

	// Populate the map with numbers from replicas
	for _, partition := range config.Partitions {
		for _, replica := range partition.Replicas {
			replicaMap[replica] = true
		}
	}

	// Check if any of the numbers to check are in the map
	for _, str := range numbersToCheck {
		num, _ := strconv.Atoi(str)
		if replicaMap[num] {
			return false
		}
	}

	return true
}

// RollbackPlan 将rollback.json重命名为plan.json
func RollbackPlan() error {
	// 获取当前时间戳
	currentTime := time.Now().Unix()

	// 构建新的文件名，附加时间戳
	newPlanFileName := fmt.Sprintf("%s.%d", cst.PlanJSONFile, currentTime)

	// 重命名 plan.json 为 plan.json.当前时间戳
	if err := os.Rename(cst.PlanJSONFile, newPlanFileName); err != nil {
		return fmt.Errorf("failed to rename plan.json to %s: %v", newPlanFileName, err)
	}

	// 重命名 rollback.json 为 plan.json
	if err := os.Rename(cst.RollbackFile, cst.PlanJSONFile); err != nil {
		return fmt.Errorf("failed to rename rollback.json to plan.json: %v", err)
	}

	return nil
}

// IsBrokerEmpty TODO
func IsBrokerEmpty(dataDirs []string) (bool, error) {
	// 定义Broker为空时应该包含的文件名
	emptyBrokerFiles := map[string]struct{}{
		"meta.properties":                  {},
		"recovery-point-offset-checkpoint": {},
		"log-start-offset-checkpoint":      {},
		"replication-offset-checkpoint":    {},
		"cleaner-offset-checkpoint":        {},
	}

	// 遍历所有数据目录
	for _, dataDir := range dataDirs {
		// 读取目录中的文件和子目录
		files, err := os.ReadDir(dataDir)
		if err != nil {
			return false, fmt.Errorf("failed to read data directory '%s': %v", dataDir, err)
		}

		// 检查目录中的文件是否只是Broker为空时应该包含的文件
		for _, file := range files {
			if file.IsDir() {
				// 如果存在子目录，则Broker不为空
				return false, nil
			}
			// 如果文件不在预期的文件列表中，则Broker不为空
			if _, ok := emptyBrokerFiles[file.Name()]; !ok {
				return false, nil
			}
		}
	}

	// 如果所有检查都通过，则Broker为空
	return true, nil
}

// ReadDataDirs 从Kafka配置文件中读取数据目录。
func ReadDataDirs(configFilePath string) ([]string, error) {
	file, err := os.Open(configFilePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open config file: %v", err)
	}
	defer file.Close()

	var dataDirs []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "log.dirs=") {
			dataDirs = strings.Split(strings.TrimPrefix(line, "log.dirs="), ",")
			break
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("failed to read config file: %v", err)
	}

	return dataDirs, nil
}

// KfVersionMap 转换成cmak能识别的版本
func KfVersionMap(version string) string {
	switch version {
	case "2.4.0":
		return "2.4.0"
	case "0.10.2":
		return "0.10.2.1"
	default:
		return "2.4.0"
	}
}
