package common

import (
	"gopkg.in/yaml.v2"
)

// YamlMongoDBConf 3.0及以上配置文件
type YamlMongoDBConf struct {
	Storage struct {
		DbPath     string `yaml:"dbPath"`
		Engine     string `yaml:"engine"`
		WiredTiger struct {
			EngineConfig struct {
				CacheSizeGB int `yaml:"cacheSizeGB"`
			} `yaml:"engineConfig"`
		} `yaml:"wiredTiger"`
	} `yaml:"storage"`
	Replication struct {
		OplogSizeMB int    `yaml:"oplogSizeMB"`
		ReplSetName string `yaml:"replSetName"`
	} `yaml:"replication"`
	SystemLog struct {
		LogAppend   bool   `yaml:"logAppend"`
		Path        string `yaml:"path"`
		Destination string `yaml:"destination"`
	} `yaml:"systemLog"`
	ProcessManagement struct {
		Fork        bool   `yaml:"fork"`
		PidFilePath string `yaml:"pidFilePath"`
	} `yaml:"processManagement"`
	Net struct {
		Port            int    `yaml:"port"`
		BindIp          string `yaml:"bindIp"`
		WireObjectCheck bool   `yaml:"wireObjectCheck"`
	} `yaml:"net"`
	OperationProfiling struct {
		SlowOpThresholdMs int `yaml:"slowOpThresholdMs"`
	} `yaml:"operationProfiling"`
	Sharding struct {
		ClusterRole string `yaml:"clusterRole,omitempty"`
	} `yaml:"sharding,omitempty"`
	Security struct {
		KeyFile string `yaml:"keyFile,omitempty"`
	} `yaml:"security,omitempty"`
}

// NewYamlMongoDBConf 生成结构体
func NewYamlMongoDBConf() *YamlMongoDBConf {
	return &YamlMongoDBConf{}
}

// GetConfContent 获取配置文件内容
func (y *YamlMongoDBConf) GetConfContent() ([]byte, error) {
	out, err := yaml.Marshal(y)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// IniNoAuthMongoDBConf 3.0以下配置文件
var IniNoAuthMongoDBConf = `replSet={{replSet}}
dbpath={{dbpath}}
logpath={{logpath}}
pidfilepath={{pidfilepath}}
logappend=true
port={{port}}
bind_ip={{bind_ip}}
fork=true
nssize=16
oplogSize={{oplogSize}}
{{instanceRole}} = true`

// IniAuthMongoDBConf 3.0以下配置文件
var IniAuthMongoDBConf = `replSet={{replSet}}
dbpath={{dbpath}}
logpath={{logpath}}
pidfilepath={{pidfilepath}}
logappend=true
port={{port}}
bind_ip={{bind_ip}}
keyFile={{keyFile}}
fork=true
nssize=16
oplogSize={{oplogSize}}
{{instanceRole}} = true
`
