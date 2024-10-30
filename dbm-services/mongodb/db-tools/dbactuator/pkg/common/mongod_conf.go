package common

import (
	"os"

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
	Replication *Replication `yaml:"replication,omitempty"`
	SystemLog   struct {
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
	Sharding *Sharding `yaml:"sharding,omitempty"`
	Security *Security `yaml:"security,omitempty"`
}

func (y *YamlMongoDBConf) Write(filePath string) error {
	content, err := y.GetConfContent()
	if err != nil {
		return err
	}
	return os.WriteFile(filePath, content, 0644)
}

type Security struct {
	KeyFile string `yaml:"keyFile,omitempty"`
}

type Sharding struct {
	ClusterRole string `yaml:"clusterRole,omitempty"`
}
type Replication struct {
	OplogSizeMB int    `yaml:"oplogSizeMB"`
	ReplSetName string `yaml:"replSetName"`
}

// NewYamlMongoDBConf 生成结构体
func NewYamlMongoDBConf() *YamlMongoDBConf {
	var conf = YamlMongoDBConf{}
	conf.Sharding = &Sharding{}
	conf.Replication = &Replication{}
	conf.Security = &Security{}
	return &conf
}

// LoadMongoDBConfFromFile 从文件中加载配置
func LoadMongoDBConfFromFile(filePath string) (*YamlMongoDBConf, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	var y YamlMongoDBConf
	err = yaml.Unmarshal(content, &y)
	if err != nil {
		return nil, err
	}
	return &y, nil
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
