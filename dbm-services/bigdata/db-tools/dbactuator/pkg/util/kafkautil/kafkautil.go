// Package kafkautil TODO
package kafkautil

import (
	"bufio"
	"encoding/json"
	"errors"
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
func GetHostByID(conn *zk.Conn, id string, root string) (string, error) {
	// 构造ZooKeeper中broker信息的路径
	var path string
	if root == "/" {
		path = fmt.Sprintf("/brokers/ids/%s", id)
	} else {
		path = fmt.Sprintf("%s/brokers/ids/%s", root, id)
	}
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
func GetBrokerIds(conn *zk.Conn, root string) ([]string, error) {
	// zk: ls /brokers/ids
	// output: [0,1,2]
	var path string
	if root == "/" {
		path = "/brokers/ids"
	} else {
		path = fmt.Sprintf("%s/brokers/ids", root)
	}
	ids, _, err := conn.Children(path)
	if err != nil {
		logger.Error("Get broker ids failed, %s", err)
		return ids, err
	}

	logger.Info("Broker ids: %v", ids)
	return ids, nil
}

// GetBrokerIDByHost 根据host返回brokerid, brokerhost -> 0
func GetBrokerIDByHost(conn *zk.Conn, host string, root string) (string, error) {
	logger.Info("Getting broker id of host ...")

	// Retrieve all broker IDs from ZooKeeper.
	ids, err := GetBrokerIds(conn, root)
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
		kfHost, err := GetHostByID(conn, kfid, root)
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
func GenReassignmentJSON(conn *zk.Conn, zkHost string, root string, xBrokerIds []string) error {
	idsArr, _ := GetBrokerIds(conn, root)
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
	// 127.0.0.1:2181/xxxx
	zk := zkHost + root
	extraCmd := fmt.Sprintf("%s --topics-to-move-json-file %s/topic.json --generate --zookeeper %s --broker-list %s >%s",
		cst.DefaultReassignPartitionsBin, cst.DefaultKafkaEnv, zk, tempIds, planJSONFile)

	logger.Info("extraCmd, %s", extraCmd)
	output, _ := osutil.ExecShellCommandJ(false, extraCmd)
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
		return errors.New(s)
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
func GenReplaceReassignmentJSON(conn *zk.Conn, zkHost string, root string, oldBrokerIds, newBrokerIds []string) error {
	// all brokers id
	idsArr, _ := GetBrokerIds(conn, root)
	ids := strings.Join(idsArr[:], ",")
	planJSONFile := cst.PlanJSONFile
	zk := zkHost + root
	extraCmd := fmt.Sprintf("%s --topics-to-move-json-file %s/topic.json --generate --zookeeper %s --broker-list %s >%s",
		cst.DefaultReassignPartitionsBin, cst.DefaultKafkaEnv, zk, ids, planJSONFile)

	logger.Info("extraCmd, %s", extraCmd)
	output, _ := osutil.ExecShellCommandJ(false, extraCmd)
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
		return errors.New(s)
	}
	// 生成rollback.json
	rollbackFile := cst.RollbackFile
	// sed -n '2p' plan.json  >rollback.json
	extraCmd = fmt.Sprintf("sed -n '2p' %s  > %s", planJSONFile, rollbackFile)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("sed plan.json failed, %s", err)
		return err
	}

	// 读取 rollback.json 并解析
	data, err := os.ReadFile(rollbackFile)
	if err != nil {
		logger.Error("读取 rollback.json 失败: %s", err)
		return err
	}
	var plan ReassignmentPlan
	err = json.Unmarshal(data, &plan)
	if err != nil {
		logger.Error("JSON 解析失败: %s", err)
		return err
	}
	oldBrokers, _ := stringsToInts(oldBrokerIds)
	newBrokers, _ := stringsToInts(newBrokerIds)
	ReplaceBrokerIds(&plan, oldBrokers, newBrokers)
	// 写入 plan.json
	outData, err := json.MarshalIndent(plan, "", "  ")
	if err != nil {
		logger.Error("JSON 序列化失败: %s", err)
		return err
	}

	err = os.WriteFile(cst.PlanJSONFile, outData, 0644)
	if err != nil {
		logger.Error("写入 plan.json 失败: %s", err)
		return err
	}
	logger.Info("Generate plan.json done")

	return nil
}

// GenReplaceReassignmentJSONBak TODO
func GenReplaceReassignmentJSONBak(oldBrokerID string, newBrokerID string, zk string) (output string, err error) {
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
	output, _ := osutil.ExecShellCommandJ(false, extraCmd)
	logger.Info("output %s", output)
	logger.Info("Doing patitions reassignment, default speed rate is 30MB/s")
	logger.Info("Changing the rate, please rerun [%s] with other rate", extraCmd)
	return nil
}

// CheckReassignPartitions TODO
func CheckReassignPartitions(zk string, jsonFile string) (output string, err error) {
	extraCmd := fmt.Sprintf(`%s --zookeeper %s --reassignment-json-file %s --verify|grep -Ev 'Status|successfully'|tail`,
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
		--broker-list %s --generate | grep -E -A1 ^Proposed|grep -E -v ^Proposed`,
		cst.DefaultReassignPartitionsBin,
		zk, topicFile, idStrs)
	logger.Info("cmd: [%s]", extraCmd)
	output, err := osutil.ExecShellCommandJ(false, extraCmd)
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

// GetZookeeperConnect 从指定的Kafka配置文件中读取zookeeper.connect的值
func GetZookeeperConnect(filePath string) (string, string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return "", "", err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		// 跳过空行和注释行
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "zookeeper.connect=") {
			// 去掉前缀，获取值
			zkHost, zkPath := parseZkAndPath(strings.TrimPrefix(line, "zookeeper.connect="))
			return zkHost, zkPath, nil
		}
	}

	if err := scanner.Err(); err != nil {
		return "", "", err
	}

	return "", "", fmt.Errorf("zookeeper.connect not found in file")
}

// Partition 表示JSON中的一个分区结构
type Partition struct {
	Topic     string   `json:"topic"`
	Partition int      `json:"partition"`
	Replicas  []int    `json:"replicas"`
	LogDirs   []string `json:"log_dirs"`
}

// ReassignmentPlan 表示整个JSON结构
type ReassignmentPlan struct {
	Version    int         `json:"version"`
	Partitions []Partition `json:"partitions"`
}

// ReplaceBrokerIds 替换replicas中的brokerId
func ReplaceBrokerIds(plan *ReassignmentPlan, oldBrokerIds, newBrokerIds []int) {
	if len(oldBrokerIds) != len(newBrokerIds) {
		logger.Error("oldBrokerIds and newBrokerIds length mismatch")
		return
	}
	replaceMap := make(map[int]int)
	for i := range oldBrokerIds {
		replaceMap[oldBrokerIds[i]] = newBrokerIds[i]
	}

	for i, p := range plan.Partitions {
		for j, brokerId := range p.Replicas {
			if newId, ok := replaceMap[brokerId]; ok {
				plan.Partitions[i].Replicas[j] = newId
			}
		}
	}
}

func stringsToInts(strs []string) ([]int, error) {
	ints := make([]int, len(strs))
	for i, s := range strs {
		n, err := strconv.Atoi(s)
		if err != nil {
			return nil, err
		}
		ints[i] = n
	}
	return ints, nil
}

// parseZkAndPath 输入格式：多个zk地址和path部分混合的字符串
// 返回第一个zk地址 + path部分（如果没有path，自动加上"/"）
func parseZkAndPath(input string) (string, string) {
	slashIndex := strings.Index(input, "/")

	var zkStr, pathStr string
	if slashIndex == -1 {
		// 不带斜杠，全部是ZK地址
		zkStr = input
		pathStr = ""
	} else {
		// 带斜杠，拆分
		zkStr = input[:slashIndex]
		pathStr = input[slashIndex:]
	}

	zkAddrs := strings.Split(zkStr, ",")
	if len(zkAddrs) == 0 {
		return "", ""
	}
	firstZk := zkAddrs[0]

	if pathStr == "" {
		return firstZk, "/"
	}
	return firstZk, pathStr
}

// GetBootstrapServers parses a kafka server.properties file and returns a bootstrap-server
// connection string like "host1:9092,host2:9092".
// It prefers advertised.listeners, and falls back to listeners if advertised.listeners is absent.
// Lines beginning with '#' (comments) and blank lines are ignored.
func GetBootstrapServers(kafkaConfigFile string) (string, error) {
	f, err := os.Open(kafkaConfigFile)
	if err != nil {
		return "", fmt.Errorf("open kafka config file %s: %w", kafkaConfigFile, err)
	}
	defer f.Close()

	var advertised string
	var fallbackListeners string

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		// skip comments and empty lines
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		// We only consider lines that start exactly with the key name (no preceding spaces after TrimSpace)
		if strings.HasPrefix(line, "advertised.listeners=") {
			advertised = strings.TrimSpace(strings.TrimPrefix(line, "advertised.listeners="))
			// found preferred key, we can stop scanning
			break
		}
		if fallbackListeners == "" && strings.HasPrefix(line, "listeners=") {
			fallbackListeners = strings.TrimSpace(strings.TrimPrefix(line, "listeners="))
			// do not break, maybe advertised.listeners appears later and should override
		}
	}
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("read kafka config file %s: %w", kafkaConfigFile, err)
	}

	listenersRaw := advertised
	if listenersRaw == "" {
		listenersRaw = fallbackListeners
	}
	if listenersRaw == "" {
		return "", fmt.Errorf("no advertised.listeners or listeners found in %s", kafkaConfigFile)
	}

	// listenersRaw may be comma separated entries like:
	//   SASL_PLAINTEXT://localhost:9092
	//   PLAINTEXT://host1:9092,SSL://host2:9093
	// We need to extract the host:port part(s)
	parts := strings.Split(listenersRaw, ",")
	var addrParts []string
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		// remove protocol prefix if present (protocol://host:port)
		if idx := strings.Index(p, "://"); idx >= 0 {
			p = p[idx+3:]
		}
		// trim any possible surrounding quotes/spaces
		p = strings.Trim(p, "\"' ")
		if p != "" {
			addrParts = append(addrParts, p)
		}
	}

	if len(addrParts) == 0 {
		return "", fmt.Errorf("no host:port found in listeners value: %s", listenersRaw)
	}

	// join multiple addresses by comma as expected by --bootstrap-server
	return strings.Join(addrParts, ","), nil
}

// GetClientProperties reads a JAAS file (e.g. kafka_server_scram_jaas.conf),
// extracts username and password and writes a Kafka client properties file
// suitable for passing to Kafka CLI tools via --command-config.
//
// Example:
//
//	jaasFile := "/data/kafkaenv/kafka/config/kafka_server_scram_jaas.conf"
//	clientProps := "/data/kafkaenv/kafka/client.properties"
//	if err := GetClientProperties(jaasFile, clientProps); err != nil { ... }
func GetClientProperties(jaasFilePath, clientPropsPath string) error {
	content, err := os.ReadFile(jaasFilePath)
	if err != nil {
		return fmt.Errorf("read jaas file %s: %w", jaasFilePath, err)
	}

	// Extract username and password using regex
	userRe := regexp.MustCompile(`username\s*=\s*"([^"]+)"`)
	passRe := regexp.MustCompile(`password\s*=\s*"([^"]+)"`)

	userMatch := userRe.FindSubmatch(content)
	passMatch := passRe.FindSubmatch(content)

	if userMatch == nil {
		return fmt.Errorf("username not found in jaas file %s", jaasFilePath)
	}
	if passMatch == nil {
		return fmt.Errorf("password not found in jaas file %s", jaasFilePath)
	}

	username := string(userMatch[1])
	password := string(passMatch[1])

	// Build client.properties content
	// Ensure the sasl.jaas.config line ends with a semicolon as required.
	props := fmt.Sprintf(
		`sasl.mechanism=SCRAM-SHA-512
security.protocol=SASL_PLAINTEXT
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username="%s" password="%s";
`, username, password)

	if err := os.WriteFile(clientPropsPath, []byte(props), 0644); err != nil {
		return fmt.Errorf("write client properties to %s: %w", clientPropsPath, err)
	}
	return nil
}

// GetKafkaVersion runs "<binPath> --version" via ExecShellCommandJ and returns the
// first non-empty line that doesn't look like Jolokia/java bind exception noise.
// It filters out lines containing "Jolokia", "Could not start Jolokia agent" and
// "java.net.BindException" (case-insensitive).
func GetKafkaVersion(binPath string) (string, error) {
	cmd := binPath + " --version"
	logger.Info("Getting Kafka version via command: [%s]", cmd)
	out, err := osutil.ExecShellCommandJ(false, cmd)
	// Parse and filter lines
	for _, raw := range strings.Split(out, "\n") {
		line := strings.TrimSpace(raw)
		if line == "" {
			continue
		}
		lower := strings.ToLower(line)
		if strings.Contains(lower, "jolokia") ||
			strings.Contains(lower, "could not start jolokia") ||
			strings.Contains(lower, "java.net.bindexception") {
			continue
		}
		// first remaining non-noise line is considered the version
		return line, nil
	}

	// If we get here, no acceptable version line found
	if err != nil {
		return "", fmt.Errorf("exec %s --version failed: %v; output: %s", binPath, err, out)
	}
	return "", fmt.Errorf("no version line found in output: %s", out)
}

// CompareVersion TODO
// CompareResult: -1 a<b, 0 a==b, 1 a>b
func CompareVersion(a, b string) int {
	// split only on '.' and '_' (keep '-' so pre-release like "1.0.0-alpha" becomes "0-alpha")
	split := func(s string) []string {
		s = strings.TrimSpace(s)
		if s == "" {
			return []string{}
		}
		// normalize consecutive separators
		parts := strings.FieldsFunc(s, func(r rune) bool {
			return r == '.' || r == '_'
		})
		return parts
	}

	parseSeg := func(seg string) (hasNum bool, num int64, suf string) {
		// match leading digits (if any) and keep the rest as suffix (can include '-' etc.)
		re := regexp.MustCompile(`^(\d+)(.*)$`)
		if seg == "" {
			return true, 0, "" // treat empty as numeric zero
		}
		if m := re.FindStringSubmatch(seg); m != nil {
			n, _ := strconv.ParseInt(m[1], 10, 64)
			return true, n, m[2] // m[2] may be "" or like "-alpha" or "rc1" or ".bkbase" etc.
		}
		return false, 0, seg // no leading number, treat whole segment as suffix string
	}

	pa := split(a)
	pb := split(b)
	n := len(pa)
	if len(pb) > n {
		n = len(pb)
	}

	for i := 0; i < n; i++ {
		var sa, sb string
		if i < len(pa) {
			sa = pa[i]
		} else {
			sa = "" // missing -> treated as zero
		}
		if i < len(pb) {
			sb = pb[i]
		} else {
			sb = ""
		}

		ha, na, sufa := parseSeg(sa)
		hb, nb, sufb := parseSeg(sb)

		// both numeric-leading
		if ha && hb {
			if na < nb {
				return -1
			}
			if na > nb {
				return 1
			}
			// same leading number -> consider suffixes
			// rule: "" (no suffix) > non-empty suffix (release > pre-release)
			if sufa == "" && sufb == "" {
				continue
			}
			if sufa == "" && sufb != "" {
				return 1
			}
			if sufa != "" && sufb == "" {
				return -1
			}
			// both non-empty suffix: compare lexicographically
			if sufa < sufb {
				return -1
			}
			if sufa > sufb {
				return 1
			}
			continue
		}

		// one numeric-leading and the other not
		if ha && !hb {
			// decide rule: numeric-leading (e.g. "1") vs non-numeric (e.g. "beta")
			// 我们采用：数字段 > 非数字段 if numeric value != 0.
			// If numeric == 0 and other is empty, consider equal above.
			// This is heuristic; 若需其它策略可修改。
			if na != 0 {
				return 1
			}
			// if na == 0, compare suffix (sufa is entire seg if no leading digits)
			if "" < sufb {
				// fallback lexicographic
				if sufa < sufb {
					return -1
				}
				if sufa > sufb {
					return 1
				}
			}
			continue
		}
		if !ha && hb {
			if nb != 0 {
				return -1
			}
			if sa < sb {
				return -1
			}
			if sa > sb {
				return 1
			}
			continue
		}

		// both non-numeric-leading: plain string compare
		if sa < sb {
			return -1
		}
		if sa > sb {
			return 1
		}
		// equal, move to next
	}

	return 0
}

// KraftBrokerIDs parses the output of "kafka-cluster.sh list-endpoints" (or similar)
// and returns a slice of broker ID strings in the order they appear.
//
// Expected input format (first line is a header):
// ID         HOST          PORT       RACK STATE      ENDPOINT_TYPE
// The function is forgiving: it skips empty lines and the header line.
func KraftBrokerIDs(listOutput string) ([]string, error) {
	var ids []string
	scanner := bufio.NewScanner(strings.NewReader(listOutput))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		// skip header or non-data lines where first field is "ID"
		if fields[0] == "ID" {
			continue
		}
		// take first field as ID string (no integer conversion)
		if fields[0] != "" {
			ids = append(ids, fields[0])
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("scan broker list output: %w", err)
	}
	if len(ids) == 0 {
		return nil, fmt.Errorf("no broker ids found")
	}
	return ids, nil
}

// KraftBrokerIDByIP searches the listOutput for a line with HOST matching the given ip
// and returns the corresponding broker ID as a string.
// If the IP is not found, an error is returned.
func KraftBrokerIDByIP(listOutput, ip string) (string, error) {
	scanner := bufio.NewScanner(strings.NewReader(listOutput))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		// skip header
		if fields[0] == "ID" {
			continue
		}
		host := fields[1]
		if host == ip {
			// return the ID field as string (no integer conversion)
			return fields[0], nil
		}
	}
	if err := scanner.Err(); err != nil {
		return "", fmt.Errorf("scan broker list output: %w", err)
	}
	return "", fmt.Errorf("ip %s not found in broker list", ip)
}

// GetBrokerPartitionCounts 通过执行 kafka-topics.sh --describe --zookeeper <endpoint>
// 并直接解析其原始输出（不借助 sed/tr/uniq 等外部工具），
// 返回 map[brokerID]partitionCount（brokerID 为 string）。
// 依赖：存在可执行的 bin/kafka-topics.sh 并且 ExecShellCommandJ 可用。
func GetBrokerPartitionCounts(endpoint string) (map[string]int, error) {
	if strings.TrimSpace(endpoint) == "" {
		return nil, fmt.Errorf("endpoint is empty")
	}

	cmd := fmt.Sprintf("%s --describe %s", cst.DefaultTopicBin, endpoint)
	out, err := osutil.ExecShellCommandJ(false, cmd)
	if err != nil {
		return nil, err
	}

	// regexp 捕获 "Replicas: <数字,数字,...>"
	re := regexp.MustCompile(`Replicas:\s*([0-9,]+)`)
	counts := make(map[string]int)

	lines := strings.Split(out, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		m := re.FindStringSubmatch(line)
		if len(m) < 2 {
			// 未匹配到 Replicas 字段，跳过
			continue
		}
		// 例如 "1002,1001"
		replicasCSV := m[1]
		ids := strings.Split(replicasCSV, ",")
		for _, id := range ids {
			id = strings.TrimSpace(id)
			if id == "" {
				continue
			}
			// 每出现一次代表该 broker 存储了该分区的一个副本
			counts[id]++
		}
	}

	return counts, nil
}
