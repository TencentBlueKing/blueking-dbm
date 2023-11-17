// Package kafkautil TODO
package kafkautil

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"regexp"
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

// GetHostByID TODO
func GetHostByID(conn *zk.Conn, id string) (string, error) {
	data, _, err := conn.Get(fmt.Sprintf("/brokers/ids/%s", id))
	if err != nil {
		logger.Error("get /brokers/ids/%s failed: %s", id, err)
		return "", err
	}
	result := make(map[string]interface{})
	if err = json.Unmarshal(data, &result); err != nil {
		logger.Error("Parse json failed, %s", err)
		return "", err
	}

	ep := result["endpoints"].([]interface{})[0].(string)
	// brokerhost:9092
	m1 := regexp.MustCompile(`.*://`)
	hostPort := m1.ReplaceAllString(ep, "")
	// brokerhost
	brokerHost := strings.Split(hostPort, ":")[0]
	logger.Info("brokerHost:[%s]", brokerHost)
	return brokerHost, nil
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

// GetBrokerIDByHost  brokerhost -> 0
func GetBrokerIDByHost(conn *zk.Conn, host string) (string, error) {
	var brokerID string
	logger.Info("Getting broker id of host ...")
	ids, _ := GetBrokerIds(conn)
	for _, kfid := range ids {
		kfHost, err := GetHostByID(conn, kfid)
		if err != nil {
			logger.Error("Cant get host by id, %s", err)
			return "", err
		}
		if kfHost == host {
			logger.Info("host:[%s] id is [%s]", kfHost, kfid)
			brokerID = kfid
			break
		}
	}
	return brokerID, nil
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

	planJSONFile := fmt.Sprintf("%s/plan.json", cst.DefaultKafkaEnv)
	extraCmd := fmt.Sprintf("%s --topics-to-move-json-file %s/topic.json --generate --zookeeper %s --broker-list %s >%s",
		cst.DefaultReassignPartitionsBin, cst.DefaultKafkaEnv, zk, tempIds, planJSONFile)

	logger.Info("extraCmd, %s", extraCmd)
	output, _ := osutil.ExecShellCommand(false, extraCmd)
	logger.Info("output: %s", output)
	/*
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("Gen plan json failed, %s, %s", output, err)
			return err
		}
	*/
	b, err := ioutil.ReadFile(planJSONFile)
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

	// Delete Current part
	extraCmd = fmt.Sprintf("sed -i '1,4d'  %s", planJSONFile)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("sed plan.json failed, %s", err)
		return err
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
	/*
		if err != nil {
			logger.Error("获取kafka topic列表失败 %v", err)
			return topicList, err
		}
	*/
	topicList = strings.Split(strings.TrimSuffix(output, "\n"), "\n")
	return topicList, nil
}

// WriteTopicJSON TODO
func WriteTopicJSON(zk string) error {
	topics, err := GetTopics(zk)
	if err != nil {
		logger.Error("Get topics list failed, %s", err)
		return err
	}
	logger.Info("Topics list %v", topics)
	var tps []TP
	for _, t := range topics {
		tps = append(tps, TP{Topic: t})
	}
	tpJSON := &TPs{
		Topics:  tps,
		Version: 1,
	}
	b, err := json.Marshal(tpJSON)
	if err != nil {
		logger.Info("Pase topic json failed, %s", err)
		return err
	}
	logger.Info("topic.json: %s", string(b))

	// write to /data/kafkaenv/topic.json
	topicJSONFile := fmt.Sprintf("%s/topic.json", cst.DefaultKafkaEnv)
	if err := ioutil.WriteFile(topicJSONFile, b, 0644); err != nil {
		logger.Error("write %s failed, %s", topicJSONFile, err)
		return err
	}

	return nil
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
	if err := ioutil.WriteFile(topicFile, []byte(topicJSON), 0644); err != nil {
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
	if err := ioutil.WriteFile(planJSONFile, []byte(output), 0644); err != nil {
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
