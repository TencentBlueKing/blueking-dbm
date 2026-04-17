package kafkautil

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

// TemplateData struct to hold the data for template rendering
type TemplateData struct {
	NumNetWorkThreads                int
	LogRetentionHours                int
	DefaultReplicationFactor         int
	NumPartitions                    int
	NumIOThreads                     int
	NumReplicaFetchers               int
	LogDirs                          string
	Listeners                        string
	ZookeeperConnect                 string
	LogRetentionBytes                int
	BrokerRack                       string
	ControllerQuorumBootstrapServers string
	NodeId                           int
	ProcessRoles                     string
	UpperProcessRoles                string
}

// renderTemplate replaces known placeholders in value using a fixed whitelist.
// This avoids text/template injection risks while preserving the original substitution behavior.
func renderTemplate(value string, data TemplateData) (string, error) {
	r := strings.NewReplacer(
		"{{.NumNetWorkThreads}}", strconv.Itoa(data.NumNetWorkThreads),
		"{{.LogRetentionHours}}", strconv.Itoa(data.LogRetentionHours),
		"{{.DefaultReplicationFactor}}", strconv.Itoa(data.DefaultReplicationFactor),
		"{{.NumPartitions}}", strconv.Itoa(data.NumPartitions),
		"{{.NumIOThreads}}", strconv.Itoa(data.NumIOThreads),
		"{{.NumReplicaFetchers}}", strconv.Itoa(data.NumReplicaFetchers),
		"{{.LogRetentionBytes}}", strconv.Itoa(data.LogRetentionBytes),
		"{{.NodeId}}", strconv.Itoa(data.NodeId),
		"{{.LogDirs}}", data.LogDirs,
		"{{.Listeners}}", data.Listeners,
		"{{.ZookeeperConnect}}", data.ZookeeperConnect,
		"{{.BrokerRack}}", data.BrokerRack,
		"{{.ControllerQuorumBootstrapServers}}", data.ControllerQuorumBootstrapServers,
		"{{.ProcessRoles}}", data.ProcessRoles,
		"{{.UpperProcessRoles}}", data.UpperProcessRoles,
	)
	return r.Replace(value), nil
}

// CreateServerPropertiesFile creates the server.properties file from the given JSON data
func CreateServerPropertiesFile(jsonData []byte, templateData TemplateData, filePath string) error {

	config := make(map[string]interface{})

	err := json.Unmarshal(jsonData, &config)
	if err != nil {
		return fmt.Errorf("error parsing JSON: %v", err)
	}
	// Define a list of invalid Kafka configuration keys to be removed
	invalidKeys := []string{
		"adminPassword",
		"adminUser",
		"factor",
		"jmx_port",
		"no_security",
		"partition_num",
		"password",
		"port",
		"replication_num",
		"retention_hours",
		"username",
		"zookeeper_conf",
	}

	// Remove invalid keys from kafkaConfig
	for _, key := range invalidKeys {
		delete(config, key)
	}

	// Create the server.properties file
	file, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("error creating file: %v", err)
	}
	defer file.Close()

	// Sort the keys to ensure consistent output
	keys := make([]string, 0, len(config))
	for key := range config {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	// Write the key-value pairs to the file
	for _, key := range keys {
		value := config[key]
		strValue, ok := value.(string)
		if ok {
			renderedValue, err := renderTemplate(strValue, templateData)
			if err != nil {
				return fmt.Errorf("error rendering template for key %s: %v", key, err)
			}
			value = renderedValue
		}
		_, err := fmt.Fprintf(file, "%s=%v\n", key, value)
		if err != nil {
			return err
		}
	}
	return nil
}
