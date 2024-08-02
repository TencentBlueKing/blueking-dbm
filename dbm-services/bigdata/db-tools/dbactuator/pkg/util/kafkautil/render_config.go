package kafkautil

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"text/template"
)

// TemplateData struct to hold the data for template rendering
type TemplateData struct {
	NumNetWorkThreads        int
	LogRetentionHours        int
	DefaultReplicationFactor int
	NumPartitions            int
	NumIOThreads             int
	NumReplicaFetchers       int
	LogDirs                  string
	Listeners                string
	ZookeeperConnect         string
	LogRetentionBytes        int
}

func renderTemplate(value string, data TemplateData) (string, error) {
	tmpl, err := template.New("config").Parse(value)
	if err != nil {
		return "", err
	}

	var renderedValue bytes.Buffer
	err = tmpl.Execute(&renderedValue, data)
	if err != nil {
		return "", err
	}

	return renderedValue.String(), nil
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
