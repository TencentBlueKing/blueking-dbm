// Package config TODO
package config

import (
	"fmt"
	"io/ioutil"
	"strconv"

	"github.com/go-playground/validator/v10"
	"gopkg.in/yaml.v2"
)

// Config configure for agent/gm
type Config struct {
	// configure for Log File
	LogConf LogConfig `yaml:"log_conf"`
	// configure for AgentConf component
	AgentConf AgentConfig `yaml:"agent_conf"`
	// configure for GMConf component
	GMConf GMConfig `yaml:"gm_conf"`
	// configure for DB detect
	DBConf DBConfig `yaml:"db_conf"`
	// configure for SSH detect
	SSH SSHConfig `yaml:"ssh"`
	// configure for DNS API
	DNS      DNSConfig      `yaml:"dns"`
	Monitor  MonitorConfig  `yaml:"monitor"`
	Timezone TimezoneConfig `yaml:"timezone"`
}

// LogConfig configure for log
type LogConfig struct {
	// the path of log file
	LogPath string `yaml:"log_path"`
	// the level of log
	LogLevel string `yaml:"log_level"`
	// maximum size of per log file, Unit: M
	LogMaxSize int `yaml:"log_maxsize"`
	// maximum number of backup files
	LogMaxBackups int `yaml:"log_maxbackups"`
	// maximum saving age
	LogMaxAge int `yaml:"log_maxage"`
	// support compress or not
	LogCompress bool `yaml:"log_compress"`
}

// AgentConfig configure for agent component
type AgentConfig struct {
	// active type list for db detect, valid type in constant.go
	ActiveDBType []string `yaml:"active_db_type"`
	// instance city for detect
	City string `yaml:"city"`
	// instance campus for detect
	Campus string `yaml:"campus"`
	// cloud id for agent
	Cloud string `yaml:"cloud" validate:"required"`
	// fetch cmdb instance's interval(second)
	FetchInterval  int `yaml:"fetch_interval"`
	ReportInterval int `yaml:"reporter_interval"`
}

// GMConfig configure for gm component
type GMConfig struct {
	City           string    `yaml:"city" validate:"required"`
	Campus         string    `yaml:"campus" validate:"required"`
	Cloud          string    `yaml:"cloud" validate:"required"`
	ListenPort     int       `yaml:"liston_port" validate:"required"`
	ReportInterval int       `yaml:"report_interval" validate:"required"`
	GDM            GDMConfig `yaml:"GDM"`
	GMM            GMMConfig `yaml:"GMM"`
	GQA            GQAConfig `yaml:"GQA"`
	GCM            GCMConfig `yaml:"GCM"`
}

// GDMConfig configure for GDM component
type GDMConfig struct {
	DupExpire    int `yaml:"dup_expire"`
	ScanInterval int `yaml:"scan_interval"`
}

// GMMConfig configure for GMM component
type GMMConfig struct {
}

// GQAConfig configure for GQA component
type GQAConfig struct {
	IDCCacheExpire       int `yaml:"idc_cache_expire"`
	SingleSwitchIDC      int `yaml:"single_switch_idc"`
	SingleSwitchInterval int `yaml:"single_switch_interval"`
	SingleSwitchLimit    int `yaml:"single_switch_limit"`
	AllHostSwitchLimit   int `yaml:"all_host_switch_limit"`
	AllSwitchInterval    int `yaml:"all_switch_interval"`
}

// GCMConfig configure for GCM component
type GCMConfig struct {
	AllowedChecksumMaxOffset int `yaml:"allowed_checksum_max_offset"`
	AllowedSlaveDelayMax     int `yaml:"allowed_slave_delay_max"`
	AllowedTimeDelayMax      int `yaml:"allowed_time_delay_max"`
	ExecSlowKBytes           int `yaml:"exec_slow_kbytes"`
}

// DBConfig configure for database component
type DBConfig struct {
	// HADB for agent/GMConf report log, heartbeat
	HADB APIConfig `yaml:"hadb"`
	// CMDB for agent/GMConf fetch instance metadata
	CMDB APIConfig `yaml:"cmdb"`
	// MySQL instance detect info
	MySQL MySQLConfig `yaml:"mysql"`
	// Redis instance detect info
	Redis RedisConfig `yaml:"redis"`
}

// MySQLConfig mysql instance connect info
type MySQLConfig struct {
	User      string `yaml:"user"`
	Pass      string `yaml:"pass"`
	ProxyUser string `yaml:"proxy_user"`
	ProxyPass string `yaml:"proxy_pass"`
	Timeout   int    `yaml:"timeout"`
}

// RedisConfig redis detect configure
type RedisConfig struct {
	Timeout int `yaml:"timeout"`
}

// SSHConfig ssh detect configure
type SSHConfig struct {
	Port    int    `yaml:"port"`
	User    string `yaml:"user"`
	Pass    string `yaml:"pass"`
	Dest    string `yaml:"dest"`
	Timeout int    `yaml:"timeout"`
}

// DNSConfig dns api configure info
type DNSConfig struct {
	BindConf    APIConfig `yaml:"bind_conf"`
	PolarisConf APIConfig `yaml:"polaris_conf"`
	ClbConf     APIConfig `yaml:"clb_conf"`
	// TODO need remove from this struct
	RemoteConf APIConfig `yaml:"remote_conf"`
}

// APIConfig api request info
type APIConfig struct {
	Host    string   `yaml:"host"`
	Port    int      `yaml:"port"`
	UrlPre  string   `yaml:"url_pre"`
	User    string   `yaml:"user"`
	Pass    string   `yaml:"pass"`
	Timeout int      `yaml:"timeout"`
	BKConf  BKConfig `yaml:"bk_conf"`
}

// BKConfig BK API authenticate configure
type BKConfig struct {
	BkToken string `yaml:"bk_token"`
}

// MonitorConfig monitor configure
type MonitorConfig struct {
	BkDataId     int    `yaml:"bk_data_id"`
	AccessToken  string `yaml:"access_token"`
	BeatPath     string `yaml:"beat_path"`
	AgentAddress string `yaml:"agent_address"`
}

// TimezoneConfig support config timezone
type TimezoneConfig struct {
	Local string `yaml:"local"`
}

// ParseConfigureFile Parse Configure file
func ParseConfigureFile(fileName string) (*Config, error) {
	valid := validator.New()
	cfg := Config{}
	yamlFile, err := ioutil.ReadFile(fileName)
	if err != nil {
		fmt.Printf("yamlFile.Get err    #%v", err)
		return nil, err
	}

	if err = yaml.Unmarshal(yamlFile, &cfg); err != nil {
		fmt.Printf("yamlFile Unmarshal: #%v", err)
		return nil, err
	}

	if err = valid.Struct(&cfg); err != nil {
		return nil, err
	}

	return &cfg, err
}

// GetAPIAddress return host:port
func (c *Config) GetAPIAddress(apiInfo APIConfig) string {
	return fmt.Sprintf("%s:%d", apiInfo.Host, apiInfo.Port)
}

// GetBKToken return bktoken
func (c *Config) GetBKToken(apiInfo APIConfig) string {
	return apiInfo.BKConf.BkToken
}

// CheckConfig check some of config field is invalid or not
func (c *Config) CheckConfig() error {
	var err error
	var hasAgent bool
	var agentCid int
	if len(c.AgentConf.Cloud) != 0 {
		hasAgent = true
		agentCid, err = strconv.Atoi(c.AgentConf.Cloud)
		if err != nil {
			fmt.Printf("cloud field convert to integer failed, %s", c.AgentConf.Cloud)
			return err
		}
	}

	var hasGm bool
	var gmCid int
	if len(c.GMConf.Cloud) != 0 {
		hasGm = true
		gmCid, err = strconv.Atoi(c.GMConf.Cloud)
		if err != nil {
			fmt.Printf("gm field convert to integer failed, %s", c.GMConf.Cloud)
			return err
		}
	}

	if hasAgent && hasGm && agentCid != gmCid {
		fmt.Printf("the cloud id of agent and gm is not equal")
		return fmt.Errorf("the cloud id of agent and gm is not equal")
	}

	if !hasAgent && !hasGm {
		return fmt.Errorf("the cloud id of agent and gm is not set")
	}
	return nil
}

// GetCloudId convert the stirng of Cloud to integer
func (c *Config) GetCloudId() int {
	if len(c.AgentConf.Cloud) > 0 {
		cloudId, err := strconv.Atoi(c.AgentConf.Cloud)
		if err != nil {
			fmt.Printf("convert cloud to integer failed, err:%s", err.Error())
			return 0
		} else {
			return cloudId
		}
	}

	if len(c.GMConf.Cloud) > 0 {
		cloudId, err := strconv.Atoi(c.GMConf.Cloud)
		if err != nil {
			fmt.Printf("convert cloud to integer failed, err:%s", err.Error())
			return 0
		} else {
			return cloudId
		}
	}

	fmt.Printf("gm and agent lack cloud field")
	return 0
}

// GetCloud the string of Cloud
func (c *Config) GetCloud() string {
	if len(c.AgentConf.Cloud) > 0 {
		return c.AgentConf.Cloud
	}

	if len(c.GMConf.Cloud) > 0 {
		return c.GMConf.Cloud
	}

	fmt.Printf("gm and agent lack cloud field")
	return ""
}
