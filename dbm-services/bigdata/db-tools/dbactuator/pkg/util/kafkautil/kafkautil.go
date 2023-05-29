// Package kafkautil TODO
package kafkautil

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io/ioutil"
	"math/rand"
	"strings"
	"time"
)

// GetBrokerIds TODO
func GetBrokerIds(zk string) (ids []string, err error) {
	var output string
	extraCmd := fmt.Sprintf(`
	export BROKERIDS=$(%s %s <<< 'ls /brokers/ids' | tail -1)
	export BROKERIDS=${BROKERIDS//[!0-9 ]/}
	echo $BROKERIDS
	`, cst.DefaultZookeeperShell, zk)
	logger.Info("extraCmd: %s", extraCmd)
	if output, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("Get zk ids failed, %s, %s", output, err.Error())
		return nil, err
	}
	logger.Info("output, %s", output)
	trimRes := strings.TrimSuffix(output, "\n")
	ids = strings.Fields(trimRes)
	return ids, nil
}

// GetBrokerIdByHost TODO
func GetBrokerIdByHost(host string, zk string) (id string, err error) {
	brokerIds, err := GetBrokerIds(zk)
	logger.Info("brokerIds, %v", brokerIds)
	if err != nil {
		logger.Error("Get broker id failed, %v", err)
		return "", err
	}

	for _, kfid := range brokerIds {
		var output string
		extraCmd := fmt.Sprintf(`
		DETAIL=$(%s %s <<< "get /brokers/ids/%s")
		[[ $DETAIL =~ PLAINTEXT:\/\/(.*?)\"\] ]]
		BROKERS=${BASH_REMATCH[1]}
		echo $BROKERS
		`, cst.DefaultZookeeperShell, zk, kfid)
		logger.Info("extraCmd: %s", extraCmd)
		if output, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("Get zk ids failed, %s, %s", output, err.Error())
			return "", err
		}
		logger.Info("output", output)
		kfHost := strings.Split(strings.TrimSuffix(output, "\n"), ":")[0]
		if kfHost == host {
			id = kfid
			break
		}
	}

	return id, nil
}

// PickRandom TODO
func PickRandom(arr []string) string {
	rand.Seed(time.Now().Unix())
	return arr[rand.Intn(len(arr))]
}

// GenReassignmentJson TODO
func GenReassignmentJson(brokerId string, zk string, xBrokerIds []string) (output string, err error) {
	idsArr, _ := GetBrokerIds(zk)
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
	allIds := strings.Join(idsArr[:], ",")
	tempIds := strings.Join(tempArr[:], ",")

	extraCmd := fmt.Sprintf(`
	function random_broker {
			IFS=$',' read -a brokers <<< %s
			selectedexpression=${brokers[ $RANDOM %% ${#brokers[@]} ]}
			echo $selectedexpression
	}
	function array_contains {
			local array="$1[@]"
			local seeking=$2
			local in=1
			for element in "${!array}"; do
			  if [[ $element == $seeking ]]; then
					in=0
					break
			  fi
			done
			return $in
	}

	function other_broker {
			local brokers_string=$1
			local all_brokers_string=%s
			if [ ${#brokers_string} -ge ${#all_brokers_string} ]; then
			  local no_other_broker_available=""
			  echo $no_other_broker_available
			else
			  IFS=$',' read -a brokers <<< "$brokers_string"
			  local new_broker=$(random_broker)
			  while array_contains brokers $new_broker; do
					new_broker=$(random_broker)
			  done
			  echo $new_broker
			fi
	}

	function all_but_broker {
			local brokers_string=$1
			local broker=$2
			IFS=$',' read -a brokers <<< "$brokers_string"
			local new_brokers=""
			for curr_broker in "${brokers[@]}"; do
			  if [ "$curr_broker" != "$broker" ]; then
					new_brokers="$new_brokers,$curr_broker"
			  fi
			done
			# Remove leading comma, if any.
			new_brokers=${new_brokers#","}
			echo $new_brokers
	  }

	function replace_broker {
			local brokers_string=$1
			local broker=$2
			local remaining_brokers=$(all_but_broker $brokers_string $broker)
			local replacement_broker=$(other_broker $brokers_string)
			new_brokers="$remaining_brokers,$replacement_broker"
			# Remove leading comma, if any.
			new_brokers=${new_brokers#","}
			# Remove trailing comma, if any.
			new_brokers=${new_brokers%%","}
			echo $new_brokers
	  }

	json="{\n"
	json="$json  \"partitions\": [\n"

	# Actual partition reassignments
	for topicPartitionReplicas in $(%s --zookeeper %s --describe | grep -w "Leader: %s" | awk '{ print $2"#"$4"#"$6"#"$8 }'); do
	 #echo "topicPartitionReplicas: $topicPartitionReplicas"
	  # Note: We use '#' as field separator in awk (see above) and here
	  # because it is not a valid character for a Kafka topic name.
	  IFS=$'#' read -a array <<< "$topicPartitionReplicas"
	  topic="${array[0]}"     # e.g. "zerg.hydra"
	  partition="${array[1]}" # e.g. "4"
	  leaders="${array[2]}"
	  replicas="${array[3]}"  # e.g. "0,8"  (= comma-separated list of broker IDs)
	  if [ $leaders == $replicas ];then 
	  	new_replicas=$(replace_broker $replicas %s)
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
	`, tempIds, allIds, cst.DefaultTopicBin, zk, brokerId, brokerId)
	logger.Info("extraCmd, %s", extraCmd)
	if output, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("gen json failed, %s, %s", output, err.Error())
		return "", err
	}
	logger.Info("output %s", output)

	return output, nil
}

// GenReplaceReassignmentJson TODO
func GenReplaceReassignmentJson(oldBrokerId string, newBrokerId string, zk string) (output string, err error) {
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
	`, cst.DefaultTopicBin, zk, oldBrokerId, oldBrokerId, newBrokerId)
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

	extraCmd := fmt.Sprintf(`%s --zookeeper %s --reassignment-json-file %s --execute`, cst.DefaultReassignPartitionsBin,
		zk, jsonFile)
	logger.Info("extraCmd: %s", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("exec reassignparttions failed, [%s], [%s]", output, err.Error())
		return err
	}
	return nil
}

// CheckReassignPartitions TODO
func CheckReassignPartitions(zk string, jsonFile string) (output string, err error) {
	extraCmd := fmt.Sprintf(`%s --zookeeper %s --reassignment-json-file %s --verify|egrep -v 'Status|successfully'`,
		cst.DefaultReassignPartitionsBin,
		zk, jsonFile)
	logger.Info("cmd: [%s]", extraCmd)
	// 这里不判断status状态
	output, _ = osutil.ExecShellCommand(false, extraCmd)
	logger.Info("output %s", output)
	return strings.TrimSuffix(output, "\n"), nil
}

// GetTopics TODO
func GetTopics(zk string) (topicList []string, err error) {
	extraCmd := fmt.Sprintf(`%s --zookeeper %s --list`, cst.DefaultTopicBin, zk)
	logger.Info("cmd: [%s]", extraCmd)
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("获取kafka topic列表失败 %v", err)
		return topicList, err
	}
	topicList = strings.Split(strings.TrimSuffix(output, "\n"), "\n")
	return topicList, nil
}

// GenerateReassginFile TODO
func GenerateReassginFile(zk, topic, idStrs, host string) error {
	topicJson := fmt.Sprintf(`
	{
		"version": 1,
		"topics": [
			{ "topic": "%s"}
		]
	}`, topic)
	topicFile := "/tmp/topic.json"
	if err := ioutil.WriteFile(topicFile, []byte(topicJson), 0644); err != nil {
		logger.Error("write %s failed, %v", topicFile, err)
		return err
	}
	extraCmd := fmt.Sprintf(
		`%s  --zookeeper %s  --topics-to-move-json-file %s --broker-list %s --generate | egrep -A1 ^Proposed|egrep -v ^Proposed`,
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

	planJsonFile := fmt.Sprintf("%s/%s.json", jsonDir, topic)
	if err := ioutil.WriteFile(planJsonFile, []byte(output), 0644); err != nil {
		logger.Error("write %s failed, %v", planJsonFile, err)
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
