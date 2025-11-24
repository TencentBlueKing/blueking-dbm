package kafka

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
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

// TopicReassignComp represents a component for handling Kafka topic reassignment operations
type TopicReassignComp struct {
	GeneralParam    *components.GeneralParam
	Params          *TopicReassignParams
	RollBackContext rollback.RollBackObjects
}

// TopicReassignParams contains parameters needed for topic reassignment
type TopicReassignParams struct {
	Brokers        []string `json:"brokers"`         // List of broker IPs
	ThrottleRate   int64    `json:"throttle_rate"`   // Throttle rate for reassignment
	Topics         []string `json:"topics"`          // List of topic patterns to filter
	ExcludeBrokers []string `json:"exclude_brokers"` // 同时兼容
	NewBrokers     []string `json:"new_brokers"`     // 替换单据
}

// TopicJSON represents the structure for topic reassignment JSON
type TopicJSON struct {
	Topics  []Topic `json:"topics"`
	Version int     `json:"version"`
}

// Topic represents a single topic in the reassignment JSON
type Topic struct {
	Topic string `json:"topic"`
}

// Init initializes the TopicReassignComp
func (t *TopicReassignComp) Init() error {
	logger.Info("Initializing topic reassignment component")
	jaas := cst.KafkaJaasFilePath
	clientProps := cst.KafkaClientProperties

	if _, err := os.Stat(clientProps); err == nil {
		// 已存在，直接返回
		return nil
	} else if !os.IsNotExist(err) {
		// 发生其它错误（例如权限问题），返回错误以便上层处理
		return fmt.Errorf("stat %s: %w", clientProps, err)
	}

	// 文件不存在，创建之
	if err := kafkautil.GetClientProperties(jaas, clientProps); err != nil {
		logger.Error("Failed to create client properties: %v", err)
		return fmt.Errorf("create client properties: %w", err)
	}
	return nil
}

// GenerateReassignmentPlans generates reassignment plans for all topics
func (t *TopicReassignComp) GenerateReassignmentPlans() error {
	// 删除上次生成的文件
	cleanFiles()
	// 写入 ThrottleRate 到文件
	throttleFile := cst.ThrottleFile
	if err := os.WriteFile(throttleFile, fmt.Appendf(nil, "%d", t.Params.ThrottleRate), 0644); err != nil {
		return fmt.Errorf("failed to write throttle rate file: %w", err)
	}

	// Determine whether topic and reassignment binaries support --zookeeper or need --bootstrap-server
	topicBinHasZk, _ := supportsZookeeper(cst.DefaultTopicBin)
	reassignBinHasZk, _ := supportsZookeeper(cst.DefaultReassignPartitionsBin)
	topicFlag := cst.KafkaZKFlag
	if !topicBinHasZk {
		topicFlag = cst.KafkaBootstrapFlag
	}
	reassignFlag := cst.KafkaZKFlag
	if !reassignBinHasZk {
		reassignFlag = cst.KafkaBootstrapFlag
	}

	var bootstrapStr string
	var zkHost, zkPath, zkStr string
	var conn *zk.Conn
	var err error
	if topicFlag == cst.KafkaBootstrapFlag || reassignFlag == cst.KafkaBootstrapFlag {
		bootstrapStr, err = kafkautil.GetBootstrapServers(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get bootstrap servers: %w", err)
		}
		logger.Info("bootstrap servers: %s", bootstrapStr)
	}
	useBootstrapAPI := false
	version, verErr := kafkautil.GetKafkaVersion(cst.DefaultTopicBin)
	logger.Info("Detected Kafka version: %s", version)
	if verErr == nil {
		if kafkautil.CompareVersion(version, cst.Kafka400) >= 0 {
			useBootstrapAPI = true
		}
	}

	// 3) 只在需要 ZK API 时才获取 zkHost/zkPath 和 建立连接
	if !useBootstrapAPI {
		zkHost, zkPath, err = kafkautil.GetZookeeperConnect(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get zookeeper connection string: %w", err)
		}
		conn, _, err = zk.Connect([]string{zkHost}, 10*time.Second)
		if err != nil {
			return fmt.Errorf("connect zk failed: %w", err)
		}
		defer conn.Close()
		zkStr = zkHost + zkPath
		logger.Info("zk: %s", zkStr)
	}

	// Get list of topics (use correct endpoint)
	topicEndpoint := zkStr
	if topicFlag == cst.KafkaBootstrapFlag {
		logger.Info(bootstrapStr)
		topicEndpoint = bootstrapStr + fmt.Sprintf(" --command-config %s ", cst.KafkaClientProperties)
	}
	logger.Info(topicEndpoint)
	cmd := fmt.Sprintf("%s --list %s %s", cst.DefaultTopicBin, topicFlag, topicEndpoint)
	logger.Info("Executing command to get topic list: %s", cmd)
	output, err := osutil.ExecShellCommandJ(false, cmd)
	if err != nil {
		return fmt.Errorf("failed to get topic list: %w", err)
	}

	topics := strings.Split(strings.TrimSpace(output), "\n")
	// Filter topics based on patterns if provided
	filterTopics := filterTopics(topics, t.Params.Topics)
	logger.Info("filterTopics: %v", filterTopics)
	// Write filtered topics to list file
	if err := os.WriteFile(cst.TopicListFilePath, []byte(strings.Join(filterTopics, "\n")), 0644); err != nil {
		return fmt.Errorf("failed to write topic list file: %w", err)
	}

	// 获取各 broker 当前的分区数
	var partitionCount map[string]int
	endPoint := topicFlag + " " + topicEndpoint
	if partitionCount, err = kafkautil.GetBrokerPartitionCounts(endPoint); err != nil {
		return fmt.Errorf("failed to get broker partition counts: %w", err)
	}
	logger.Info("Broker partition counts: %v", partitionCount)

	excludeCount := len(t.Params.ExcludeBrokers)
	newCount := len(t.Params.NewBrokers)

	replaceMode := false
	shrinkMode := false
	if excludeCount > 0 && newCount > 0 {
		replaceMode = true
	} else if excludeCount > 0 && newCount == 0 {
		shrinkMode = true
	}

	var brokerListStr string
	var excludeIDs, newIDs []int
	var clusterOutput string
	if useBootstrapAPI {
		// 使用 kafka-cluster.sh list-endpoints 获取 broker 列表
		// 请确保 cst.KafkaClusterBin 存在并指向 kafka-cluster.sh 路径
		clusterCmd := fmt.Sprintf("%s list-endpoints --bootstrap-server %s --config %s",
			cst.KafkaClusterBin, bootstrapStr, cst.KafkaClientProperties)
		logger.Info("Executing cluster list-endpoints command: %s", clusterCmd)
		var out string
		out, err = osutil.ExecShellCommandJ(false, clusterCmd)
		if err != nil {
			return fmt.Errorf("failed to exec list-endpoints: %w; output: %s", err, out)
		}
		clusterOutput = out
	}
	if replaceMode {
		if useBootstrapAPI {
			var allBrokerIDs []string
			allBrokerIDs, err = kafkautil.KraftBrokerIDs(clusterOutput)
			if err != nil {
				return fmt.Errorf("failed to parse broker ids from cluster output: %w", err)
			}
			// exclude -> ids (string & int)
			excludeStrs := make([]string, 0, len(t.Params.ExcludeBrokers))
			for _, ip := range t.Params.ExcludeBrokers {
				idStr, err := kafkautil.KraftBrokerIDByIP(clusterOutput, ip)
				if err != nil {
					return fmt.Errorf("failed to get broker ID for exclude %s via bootstrap: %w", ip, err)
				}
				excludeStrs = append(excludeStrs, idStr)
				if n, e := strconv.Atoi(idStr); e == nil {
					excludeIDs = append(excludeIDs, n)
				}
			}
			for _, ip := range t.Params.NewBrokers {
				idStr, err := kafkautil.KraftBrokerIDByIP(clusterOutput, ip)
				if err != nil {
					return fmt.Errorf("failed to get broker ID for new %s via bootstrap: %w", ip, err)
				}
				if n, e := strconv.Atoi(idStr); e == nil {
					newIDs = append(newIDs, n)
				}
			}
			remainBrokers := difference(allBrokerIDs, excludeStrs)
			brokerListStr = strings.Join(remainBrokers, ",")
		} else {
			// 获取 exclude/new broker 的ID
			bIDs := make([]string, 0)
			for _, ip := range t.Params.ExcludeBrokers {
				id, err := kafkautil.GetBrokerIDByHost(conn, ip, zkPath)
				if err != nil {
					return fmt.Errorf("failed to get broker ID for exclude %s: %w", ip, err)
				}
				bIDs = append(bIDs, id)
				intID, _ := strconv.Atoi(id)
				excludeIDs = append(excludeIDs, intID)
			}
			for _, ip := range t.Params.NewBrokers {
				id, err := kafkautil.GetBrokerIDByHost(conn, ip, zkPath)
				if err != nil {
					return fmt.Errorf("failed to get broker ID for new %s: %w", ip, err)
				}
				intID, _ := strconv.Atoi(id)
				newIDs = append(newIDs, intID)
			}
			allBrokerIDs, err := kafkautil.GetBrokerIds(conn, zkPath)
			if err != nil {
				return fmt.Errorf("failed to get all broker IDs: %w", err)
			}
			remainBrokers := difference(allBrokerIDs, bIDs)
			brokerListStr = strings.Join(remainBrokers, ",")
		}
	} else if shrinkMode {
		// 1) 检查 exclude_brokers 是否在 kafka broker 列表里：
		//    如果所有 exclude_brokers 都不存在于集群中，则直接返回 nil（nothing to shrink）。
		//    如果部分存在，则以存在的那些作为要排除的目标继续后续流程。
		var allBrokerIDs []string
		excludeStrs := make([]string, 0, len(t.Params.ExcludeBrokers)) // 用于 KRaft 分支（string IDs）
		bIDs := make([]string, 0, len(t.Params.ExcludeBrokers))        // 用于 ZK 分支（string IDs）
		// a) collect exclude IDs from cluster (only collect those that actually exist)
		if useBootstrapAPI {
			allBrokerIDs, err = kafkautil.KraftBrokerIDs(clusterOutput)
			if err != nil {
				return fmt.Errorf("failed to parse broker ids from cluster output: %w", err)
			}
			// collect only those exclude brokers that exist in cluster
			foundExcludeStrs := make([]string, 0, len(t.Params.ExcludeBrokers))
			for _, ip := range t.Params.ExcludeBrokers {
				idStr, e := kafkautil.KraftBrokerIDByIP(clusterOutput, ip)
				if e != nil {
					logger.Warn("Exclude broker %s not found in cluster (via bootstrap), will ignore it: %v", ip, e)
					continue
				}
				foundExcludeStrs = append(foundExcludeStrs, idStr)
				if n, e2 := strconv.Atoi(idStr); e2 == nil {
					excludeIDs = append(excludeIDs, n)
				}
			}
			if len(foundExcludeStrs) == 0 {
				logger.Info("none of exclude brokers found in cluster (via bootstrap), nothing to shrink")
				if err = copyToDoneFile(); err != nil {
					return err
				}
				return nil
			}
			excludeStrs = foundExcludeStrs
			pCount := sumPartitionCounts(partitionCount, excludeStrs)
			if pCount == 0 {
				logger.Info("all exclude brokers have zero partitions, nothing to shrink")
				if err = copyToDoneFile(); err != nil {
					return err
				}
				return nil
			}
		} else {
			// ZK 分支：只收集实际存在的 exclude brokers
			foundBIDs := make([]string, 0, len(t.Params.ExcludeBrokers))
			for _, ip := range t.Params.ExcludeBrokers {
				id, e := kafkautil.GetBrokerIDByHost(conn, ip, zkPath)
				if e != nil {
					logger.Warn("Exclude broker %s not found in cluster (via zookeeper), will ignore it: %v", ip, e)
					continue
				}
				foundBIDs = append(foundBIDs, id)
				intID, _ := strconv.Atoi(id)
				excludeIDs = append(excludeIDs, intID)
			}
			if len(foundBIDs) == 0 {
				logger.Info("none of exclude brokers found in cluster (via zookeeper), nothing to shrink")
				if err = copyToDoneFile(); err != nil {
					return err
				}
				return nil
			}
			bIDs = foundBIDs
			pCount := sumPartitionCounts(partitionCount, bIDs)
			if pCount == 0 {
				logger.Info("all exclude brokers have zero partitions, nothing to shrink")
				if err = copyToDoneFile(); err != nil {
					return err
				}
				return nil
			}
			var allIDs []string
			allIDs, err = kafkautil.GetBrokerIds(conn, zkPath)
			if err != nil {
				return fmt.Errorf("failed to get all broker IDs: %w", err)
			}
			allBrokerIDs = allIDs
		}

		// c) 通过排除 excludeStrs / bIDs 获取 remain brokers（跟 replaceMode 相似），构造 brokerListStr
		if useBootstrapAPI {
			remainBrokers := difference(allBrokerIDs, excludeStrs)
			brokerListStr = strings.Join(remainBrokers, ",")
		} else {
			remainBrokers := difference(allBrokerIDs, bIDs)
			brokerListStr = strings.Join(remainBrokers, ",")
		}
		// 检查exclude_brokers在partitionCount里面的分区数是否都为0
		if useBootstrapAPI {

		}
	} else {
		// 普通模式，获取所有 broker 的ID
		brokerIDs := make([]string, 0)
		var id string
		for _, brokerIP := range t.Params.Brokers {
			if useBootstrapAPI {
				id, err = kafkautil.KraftBrokerIDByIP(clusterOutput, brokerIP)
			} else {
				id, err = kafkautil.GetBrokerIDByHost(conn, brokerIP, zkPath)
			}
			if err != nil {
				return fmt.Errorf("failed to get broker ID for %s: %w", brokerIP, err)
			}
			brokerIDs = append(brokerIDs, id)
		}
		brokerListStr = strings.Join(brokerIDs, ",")
	}

	// reassign endpoint depending on flag
	reassignEndpoint := zkStr
	if reassignFlag == cst.KafkaBootstrapFlag {
		reassignEndpoint = bootstrapStr + fmt.Sprintf(" --command-config %s ", cst.KafkaClientProperties)
	}

	for _, topic := range filterTopics {
		if topic == "" {
			continue
		}

		// 1. 生成topic JSON文件
		topicJSON := TopicJSON{
			Topics:  []Topic{{Topic: topic}},
			Version: 1,
		}
		jsonData, err := json.Marshal(topicJSON)
		if err != nil {
			return fmt.Errorf("failed to marshal topic JSON: %w", err)
		}
		topicJSONFile := fmt.Sprintf("%s.json", topic)
		if err := os.WriteFile(topicJSONFile, jsonData, 0644); err != nil {
			return fmt.Errorf("failed to write topic JSON file: %w", err)
		}

		// 2. 生成分配计划
		cmd = fmt.Sprintf("%s --broker-list %s --topics-to-move-json-file %s --generate %s %s",
			cst.DefaultReassignPartitionsBin, brokerListStr, topicJSONFile, reassignFlag, reassignEndpoint)
		logger.Info("Executing command to generate reassignment plan: %s", cmd)
		output, err := osutil.ExecShellCommandJ(false, cmd)

		// 检查输出中是否包含 rack 相关的错误提示
		needRetry := strings.Contains(output, "Not all brokers have rack information") ||
			strings.Contains(output, "Add --disable-rack-aware")

		if err != nil && !needRetry {
			return fmt.Errorf("failed to generate reassignment plan: %w; output: %s", err, output)
		}

		if needRetry {
			logger.Warn("Detected missing broker.rack info; retrying with --disable-rack-aware")
			cmd = fmt.Sprintf("%s --broker-list %s --topics-to-move-json-file %s --generate %s %s --disable-rack-aware",
				cst.DefaultReassignPartitionsBin, brokerListStr, topicJSONFile, reassignFlag, reassignEndpoint)
			logger.Info("Executing command to generate reassignment plan (disable rack aware): %s", cmd)
			output, err = osutil.ExecShellCommandJ(false, cmd)
			if err != nil {
				return fmt.Errorf("failed to generate reassignment plan with --disable-rack-aware: %w; output: %s", err, output)
			}
		}

		// 3. 解析current assignment
		parts := strings.Split(output, "Proposed partition reassignment configuration")
		logger.Info("Parts length: %d", len(parts))
		if len(parts) != 2 {
			return fmt.Errorf("unexpected output format from reassignment plan generation")
		}
		currentJSON := strings.TrimSpace(strings.TrimPrefix(parts[0], "Current partition replica assignment"))
		proposedJSON := strings.TrimSpace(parts[1])

		// 4. 写入rollback和reassign文件
		if err := os.WriteFile(fmt.Sprintf("rollback-%s.json", topic), []byte(currentJSON), 0644); err != nil {
			return fmt.Errorf("failed to write rollback JSON: %w", err)
		}

		if replaceMode {
			// 反序列化为ReassignmentPlan
			var plan kafkautil.ReassignmentPlan
			if err := json.Unmarshal([]byte(currentJSON), &plan); err != nil {
				return fmt.Errorf("unmarshal current assignment: %w", err)
			}
			// 替换exclude broker为new broker
			kafkautil.ReplaceBrokerIds(&plan, excludeIDs, newIDs)
			newAssignmentJSON, err := json.MarshalIndent(plan, "", "  ")
			if err != nil {
				return fmt.Errorf("marshal new assignment: %w", err)
			}
			if err := os.WriteFile(fmt.Sprintf("reassign-%s.json", topic), newAssignmentJSON, 0644); err != nil {
				return fmt.Errorf("failed to write reassignment JSON: %w", err)
			}
		} else {
			if err := os.WriteFile(fmt.Sprintf("reassign-%s.json", topic), []byte(proposedJSON), 0644); err != nil {
				return fmt.Errorf("failed to write reassignment JSON: %w", err)
			}
		}
	}
	return nil
}

// ExecuteReassignment executes the reassignment plans for all topics
func (t *TopicReassignComp) ExecuteReassignment() error {
	version, verErr := kafkautil.GetKafkaVersion(cst.DefaultTopicBin)
	logger.Info("Detected Kafka version: %s", version)
	useBootstrapAPI := false
	if verErr == nil {
		if kafkautil.CompareVersion(version, cst.Kafka400) >= 0 {
			useBootstrapAPI = true
		}
	}
	var err error
	var zkStr string
	if !useBootstrapAPI {
		// Get Zookeeper connection string
		zkHost, zkPath, err := kafkautil.GetZookeeperConnect(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get zookeeper connection string: %w", err)
		}
		zkStr = zkHost + zkPath
	}

	// Determine whether reassign binary supports --zookeeper or needs --bootstrap-server
	reassignBinHasZk, _ := supportsZookeeper(cst.DefaultReassignPartitionsBin)
	reassignFlag := cst.KafkaZKFlag
	if !reassignBinHasZk {
		reassignFlag = cst.KafkaBootstrapFlag
	}
	// If bootstrap-server needed, fetch it
	var bootstrapStr string
	if reassignFlag == cst.KafkaBootstrapFlag {
		bootstrapStr, err = kafkautil.GetBootstrapServers(cst.KafkaConfigFile)
		if err != nil {
			return fmt.Errorf("failed to get bootstrap servers: %w", err)
		}
		logger.Info("bootstrap servers: %s", bootstrapStr)
	}

	// Read list of topics
	topics, err := os.ReadFile(cst.TopicListFilePath)
	if err != nil {
		return fmt.Errorf("failed to read topic list: %w", err)
	}

	topicList := strings.Split(strings.TrimSpace(string(topics)), "\n")
	total := len(topicList)
	doneFile := cst.DoneFile
	logger.Info("Total topics to reassign: %d", total)

	// reassign endpoint
	reassignEndpoint := zkStr
	if reassignFlag == cst.KafkaBootstrapFlag {
		reassignEndpoint = bootstrapStr + fmt.Sprintf(" --command-config %s ", cst.KafkaClientProperties)
	}

	for i, topic := range topicList {
		if topic == "" {
			continue
		}

		// Skip if already done
		doneContentBytes, _ := os.ReadFile(doneFile)
		doneLines := strings.Split(strings.TrimSpace(string(doneContentBytes)), "\n")
		isDone := false
		for _, line := range doneLines {
			if strings.TrimSpace(line) == topic {
				isDone = true
				break
			}
		}
		if isDone {
			logger.Info("Skipping reassignment for topic %s (already done)", topic)
			continue
		}

		// 读取 throttle_rate.txt 文件, 动态修改速度
		throttleFile := cst.ThrottleFile
		throttleBytes, err := os.ReadFile(throttleFile)
		if err != nil {
			return fmt.Errorf("failed to read throttle rate file: %w", err)
		}
		throttleStr := strings.TrimSpace(string(throttleBytes))

		logger.Info("[%d/%d] Starting reassignment for topic %s...", i+1, total, topic)

		// Execute reassignment
		planJSONFile := fmt.Sprintf("reassign-%s.json", topic)

		cmd := fmt.Sprintf("%s --execute --reassignment-json-file %s --throttle %s %s %s",
			cst.DefaultReassignPartitionsBin, planJSONFile, throttleStr, reassignFlag, reassignEndpoint)

		logger.Info("Executing reassignment command: [%s]", cmd)
		if output, err, exitCode := osutil.ExecShellCommandBd(false, cmd); exitCode != 0 {
			return fmt.Errorf("failed to execute reassignment for topic %s: %s", topic, err+output)
		}

		// Wait for reassignment to complete
		for {
			cmd = fmt.Sprintf("%s --verify --reassignment-json-file %s %s %s",
				cst.DefaultReassignPartitionsBin, planJSONFile, reassignFlag, reassignEndpoint)
			logger.Info("Verifying reassignment status for topic %s: [%s]", topic, cmd)
			output, err, exitCode := osutil.ExecShellCommandBd(false, cmd)
			if exitCode != 0 {
				return fmt.Errorf("failed to verify reassignment for topic %s: %s", topic, err+output)
			}

			if !strings.Contains(output, "is still in progress") {
				logger.Info("[%d/%d] Topic %s reassignment completed", i+1, total, topic)
				break
			}

			logger.Info("[%d/%d] Topic %s reassignment in progress, waiting 10 seconds...", i+1, total, topic)
			time.Sleep(5 * time.Second)
		}

		// Mark as done
		f, err := os.OpenFile(doneFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			return fmt.Errorf("failed to open done file for append: %w", err)
		}
		defer f.Close()

		if _, err := f.WriteString(topic + "\n"); err != nil {
			return fmt.Errorf("failed to update done file: %w", err)
		}
	}

	logger.Info("All topic reassignments completed!")

	return nil

}

func cleanFiles() {
	// Clean up files
	filesToRemove := []string{cst.ThrottleFile, cst.TopicListFilePath, cst.DoneFile}
	jsonFiles, err := filepath.Glob("*.json")
	if err != nil {
		logger.Warn("failed to list JSON files: %v", err)
	}
	filesToRemove = append(filesToRemove, jsonFiles...)
	for _, file := range filesToRemove {
		if err := os.Remove(file); err != nil && !os.IsNotExist(err) {
			logger.Warn("failed to remove file %s: %v", file, err)
		}
	}
}

// wildcardToRegexp converts a wildcard pattern to a regular expression
func wildcardToRegexp(pattern string) string {
	// 先把*分割，分别转义，再用.*连接
	parts := strings.Split(pattern, "*")
	for i, p := range parts {
		parts[i] = regexp.QuoteMeta(p)
	}
	return "^" + strings.Join(parts, ".*") + "$"
}

// matchWildcard checks if a string matches a wildcard pattern
func matchWildcard(pattern, s string) bool {
	re := regexp.MustCompile(wildcardToRegexp(pattern))
	return re.MatchString(s)
}

// filterTopics filters topics based on patterns
func filterTopics(allTopics []string, topicPatterns []string) []string {
	var result []string
	for _, topic := range allTopics {
		for _, pattern := range topicPatterns {
			if matchWildcard(pattern, topic) {
				result = append(result, topic)
				break
			}
		}
	}
	return result
}

// difference returns the elements in slice 'a' that are not present in slice 'b'.
// It constructs a map from slice 'b' for efficient look-up and iterates over slice 'a',
// collecting elements that do not exist in the map.
func difference(a, b []string) []string {
	m := make(map[string]struct{})
	for _, item := range b {
		m[item] = struct{}{}
	}

	var diff []string
	for _, item := range a {
		if _, found := m[item]; !found {
			diff = append(diff, item)
		}
	}
	return diff
}

// supportsZookeeper checks if the given binary's help output contains "zookeeper".
// If executing the help command fails, it logs a warning and returns false without error
// (so the caller can fallback to using --bootstrap-server).
func supportsZookeeper(bin string) (bool, error) {
	helpCmd := bin
	output, _ := osutil.ExecShellCommandJ(false, helpCmd)
	logger.Warn("failed to exec help for %s, output: %s", bin, output)

	return strings.Contains(output, "--zookeeper"), nil
}

func copyToDoneFile() error {
	// 复制cst.TopicListFilePath到cst.DoneFilePath，表示操作成功完成但无实际变更
	doneFile := cst.DoneFile
	input, readErr := os.ReadFile(cst.TopicListFilePath)
	if readErr != nil {
		return fmt.Errorf("failed to read topic list file for done file creation: %w", readErr)
	}
	if writeErr := os.WriteFile(doneFile, input, 0644); writeErr != nil {
		return fmt.Errorf("failed to write done file: %w", writeErr)
	}

	return nil
}

func sumPartitionCounts(counts map[string]int, keys []string) int {
	if counts == nil {
		return 0
	}
	sum := 0
	for _, k := range keys {
		if v, ok := counts[k]; ok {
			sum += v
		}
	}
	return sum
}
