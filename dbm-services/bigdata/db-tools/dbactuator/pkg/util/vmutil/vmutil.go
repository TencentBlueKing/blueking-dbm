// Package vmutil TODO
package vmutil

import (
	"bytes"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"encoding/json"
	"fmt"
	"html/template"
	"strings"

	"gopkg.in/yaml.v2"
)

// VMConfig TODO
type VMConfig struct {
	RetentionPeriod   string `json:"retentionPeriod"`
	StorageDataPath   string `json:"storageDataPath"`
	ReplicationFactor int    `json:"replicationFactor"`
	StorageNode       string `json:"storageNode"`
	AuthConfig        string `json:"authConfig"`
	HTTPListenAddr    string `json:"httpListenAddr"`
}

func processJSON(jsonData []byte, config VMConfig) string {
	// 解析JSON数据
	fmt.Println(string(jsonData))
	var data map[string]interface{}
	if err := json.Unmarshal(jsonData, &data); err != nil {
		panic(err)
	}

	// 创建一个buffer来存储结果
	var buf bytes.Buffer

	// 遍历map
	for key, value := range data {
		// 如果值是一个字符串并且包含模板变量，使用配置数据来渲染模板
		if strValue, ok := value.(string); ok && strings.Contains(strValue, "{{") {
			tmpl, err := template.New("config").Parse(strValue)
			if err != nil {
				panic(err)
			}

			var rendered bytes.Buffer
			if err := tmpl.Execute(&rendered, config); err != nil {
				panic(err)
			}

			// 将渲染后的字符串作为值
			value = rendered.String()
		}

		// 将键值对格式化为-key value的形式，并添加到buffer
		buf.WriteString(fmt.Sprintf("-%s %v ", key, value))
	}

	// 返回结果字符串
	return buf.String()
}

// VMRunScript 生成执行脚本
func VMRunScript(role string, data []byte, config VMConfig) []byte {
	// /data/vmenv/vm/bin/vmstorage-prod -key1 value1 -key2 value -key3 value3\
	env := cst.DefaultVMEnv
	params := processJSON(data, config)
	scripts := []byte(fmt.Sprintf("#!/bin/bash\nexec %s/vm/bin/%s-prod %s", env, role, params))

	return scripts
}

// VMSuperIni 生成supervisor的ini文件
func VMSuperIni(role string, scriptPath string) []byte {
	logPath := fmt.Sprintf("%s/%s.log", cst.DefaultVMLogDir, role)
	iniRaw := fmt.Sprintf(
		"[program:%s]\n"+
			"command=%s\n"+
			"numprocs=1\n"+
			"autostart=true\n"+
			"startsecs=3\n"+
			"startretries=99\n"+
			"autorestart=true\n"+
			"exitcodes=0\n"+
			"user=%s\n"+
			"redirect_stderr=true\n"+
			"stdout_logfile=%s\n"+
			"stdout_logfile_maxbytes=50MB\n"+
			"stdout_logfile_backups=10\n",
		role, scriptPath, cst.DefaultExecUser, logPath,
	)
	return []byte(iniRaw)
}

// AuthConfig vmauth的配置项
type AuthConfig struct {
	UnauthorizedUser struct {
		URLPrefix []string `yaml:"url_prefix"`
	} `yaml:"unauthorized_user"`
}

// GenerateAuthYAML 生成auth.config
func GenerateAuthYAML(input string) ([]byte, error) {
	// Split the input string by comma
	rawURLs := strings.Split(input, ",")
	// Prepare a slice to hold the formatted URLs
	formattedURLs := make([]string, len(rawURLs))

	// Add "http://" prefix and "/" suffix to each URL
	for i, url := range rawURLs {
		formattedURLs[i] = fmt.Sprintf("http://%s/", url)
	}

	// Assign the formatted URLs to the config struct
	config := AuthConfig{}
	config.UnauthorizedUser.URLPrefix = formattedURLs

	// Marshal the config struct to YAML
	data, err := yaml.Marshal(&config)
	if err != nil {
		return []byte{}, err
	}

	// Convert the YAML byte slice to a string and return
	return data, nil
}
