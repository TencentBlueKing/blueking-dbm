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
	// 写入 ThrottleRate 到文件
	throttleFile := cst.ThrottleFile
	if err := os.WriteFile(throttleFile, fmt.Appendf(nil, "%d", t.Params.ThrottleRate), 0644); err != nil {
		return fmt.Errorf("failed to write throttle rate file: %w", err)
	}
	return nil
}

// GenerateReassignmentPlans generates reassignment plans for all topics
func (t *TopicReassignComp) GenerateReassignmentPlans() error {
	// 删除上次生成的文件
	cleanFiles()
	// Get Zookeeper connection string
	zkHost, zkPath, err := kafkautil.GetZookeeperConnect(cst.KafkaConfigFile)
	if err != nil {
		return fmt.Errorf("failed to get zookeeper connection string: %w", err)
	}
	zkStr := zkHost + zkPath
	logger.Info("zk: %s", zkStr)

	// Get list of topics
	cmd := fmt.Sprintf("%s --list --zookeeper %s", cst.DefaultTopicBin, zkStr)
	logger.Info("Executing command to get topic list: %s", cmd)
	output, err := osutil.ExecShellCommand(false, cmd)
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

	conn, _, err := zk.Connect([]string{zkHost}, 10*time.Second)
	if err != nil {
		logger.Error("Connect zk failed, %s", err)
		return err
	}
	defer conn.Close()

	replaceMode := len(t.Params.ExcludeBrokers) > 0
	logger.Info("Replace mode: %v", replaceMode)

	var brokerListStr string
	var excludeIDs, newIDs []int
	if replaceMode {
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
	} else {
		// 普通模式，获取所有 broker 的ID
		brokerIDs := make([]string, 0)
		for _, brokerIP := range t.Params.Brokers {
			id, err := kafkautil.GetBrokerIDByHost(conn, brokerIP, zkPath)
			if err != nil {
				return fmt.Errorf("failed to get broker ID for %s: %w", brokerIP, err)
			}
			brokerIDs = append(brokerIDs, id)
		}
		brokerListStr = strings.Join(brokerIDs, ",")
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
		cmd = fmt.Sprintf("%s --broker-list %s --topics-to-move-json-file %s --generate --zookeeper %s",
			cst.DefaultReassignPartitionsBin, brokerListStr, topicJSONFile, zkStr)
		logger.Info("Executing command to generate reassignment plan: %s", cmd)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			return fmt.Errorf("failed to generate reassignment plan: %w", err)
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
	// Get Zookeeper connection string
	zkHost, zkPath, err := kafkautil.GetZookeeperConnect(cst.KafkaConfigFile)
	if err != nil {
		return fmt.Errorf("failed to get zookeeper connection string: %w", err)
	}
	zkStr := zkHost + zkPath

	// Read list of topics
	topics, err := os.ReadFile(cst.TopicListFilePath)
	if err != nil {
		return fmt.Errorf("failed to read topic list: %w", err)
	}

	topicList := strings.Split(strings.TrimSpace(string(topics)), "\n")
	total := len(topicList)
	doneFile := cst.DoneFile
	logger.Info("Total topics to reassign: %d", total)

	// Create or clear done file
	if err := os.WriteFile(doneFile, []byte{}, 0644); err != nil {
		return fmt.Errorf("failed to create done file: %w", err)
	}

	for i, topic := range topicList {
		if topic == "" {
			continue
		}

		// Skip if already done
		doneContent, _ := os.ReadFile(doneFile)
		if strings.Contains(string(doneContent), topic) {
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

		cmd := fmt.Sprintf("%s --execute --reassignment-json-file %s --throttle %s --zookeeper %s",
			cst.DefaultReassignPartitionsBin, planJSONFile, throttleStr, zkStr)

		logger.Info("Executing reassignment command: [%s]", cmd)
		if output, err, exitCode := osutil.ExecShellCommandBd(false, cmd); exitCode != 0 {
			return fmt.Errorf("failed to execute reassignment for topic %s: %s", topic, err+output)
		}

		// Wait for reassignment to complete
		for {
			cmd = fmt.Sprintf("%s --verify --reassignment-json-file %s --zookeeper %s",
				cst.DefaultReassignPartitionsBin, planJSONFile, zkStr)
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
			time.Sleep(10 * time.Second)
		}

		// Mark as done
		f, err := os.OpenFile(doneFile, os.O_APPEND|os.O_WRONLY, 0644)
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
