package common

import (
	"gopkg.in/yaml.v2"
)

// YamlMongoSConf 4.0及以上配置文件
type YamlMongoSConf struct {
	Sharding struct {
		ConfigDB string `yaml:"configDB"`
	} `yaml:"sharding"`
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
		SlowOpThresholdMs int `yaml:"slowOpThresholdMs,omitempty"`
	} `yaml:"operationProfiling,omitempty"`
	Security struct {
		KeyFile string `yaml:"keyFile,omitempty"`
	} `yaml:"security,omitempty"`
}

// NewYamlMongoSConf 生成结构体
func NewYamlMongoSConf() *YamlMongoSConf {
	return &YamlMongoSConf{}
}

// GetConfContent 获取配置文件内容
func (y *YamlMongoSConf) GetConfContent() ([]byte, error) {
	out, err := yaml.Marshal(y)
	if err != nil {
		return nil, err
	}
	return out, nil
}
