// Package vmutil TODO
package vmutil

import (
	"bytes"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"encoding/json"
	"fmt"
	"html/template"
	"strings"
)

// VMConfig TODO
type VMConfig struct {
	RetentionPeriod   string `json:"retentionPeriod"`
	StorageDataPath   string `json:"storageDataPath"`
	ReplicationFactor int    `json:"replicationFactor"`
	StorageNode       string `json:"storageNode"`
}

func processJSON(jsonData []byte, config VMConfig) string {
	// 解析JSON数据
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
	scripts := []byte(fmt.Sprintf("%s/vm/bin/%s-prod %s", env, role, params))

	return scripts
}

// VMSuperIni TODO
func VMSuperIni(role string, scriptPath string) []byte {
	// /data/vmlog/vmstorage.log
	logPath := fmt.Sprintf("%s/%s.log", cst.DefaultVMLogDir, role)
	iniRaw := []byte(fmt.Sprintf(`[program:%s]
	command=%s ; 
	numprocs=1 ; 
	autostart=true ; 
	startsecs=3 ; 
	startretries=99 ; 
	autorestart=true ; 
	exitcodes=0 ; 
	user=%s ;
	redirect_stderr=true ; 
	stdout_logfile=%s ; 
	stdout_logfile_maxbytes=50MB ; 
	stdout_logfile_backups=10 ;`, role, scriptPath, cst.DefaultVMEnv, logPath))

	return iniRaw
}
