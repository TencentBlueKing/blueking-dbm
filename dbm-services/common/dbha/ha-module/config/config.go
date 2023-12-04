// Package config TODO
package config

import (
	"fmt"
	"io/ioutil"

	"github.com/go-playground/validator/v10"
	"gopkg.in/yaml.v2"
)

// Config configure for agent/gm
type Config struct {
	// configure for Log File
	LogConf LogConfig `yaml:"log_conf"`
	// configure for AgentConf component
	AgentConf *AgentConfig `yaml:"agent_conf"`
	// configure for GMConf component
	GMConf *GMConfig `yaml:"gm_conf"`
	// configure for DB detect
	DBConf DBConfig `yaml:"db_conf"`
	// configure for SSH detect
	SSH SSHConfig `yaml:"ssh"`
	// configure for NameServices API
	NameServices NameServicesConfig `yaml:"name_services"`
	// configure for bk monitor
	Monitor MonitorConfig `yaml:"monitor"`
	// configure for timezone
	Timezone TimezoneConfig `yaml:"timezone"`
	// configure for password service
	PasswdConf APIConfig `yaml:"password_conf"`
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
	// instance city for detect, value 0 allowed, so required tag could not assign
	CityID int `yaml:"city_id"`
	// instance campus for detect
	Campus string `yaml:"campus"`
	// cloud id for agent, value 0 allowed, so required tag could not assign
	CloudID int `yaml:"cloud_id"`
	// fetch cmdb instance's interval(second)
	FetchInterval  int `yaml:"fetch_interval"`
	ReportInterval int `yaml:"reporter_interval"`
}

// GMConfig configure for gm component
type GMConfig struct {
	//value 0 allowed, so required tag could not assign
	CityID int    `yaml:"city_id"`
	Campus string `yaml:"campus" validate:"required"`
	//value 0 allowed, so required tag could not assign
	CloudID        int       `yaml:"cloud_id"`
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
	// Riak instance detect info
	Riak RiakConfig `yaml:"riak"`
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

// RiakConfig riak detect configure
type RiakConfig struct {
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
type NameServicesConfig struct {
	DnsConf     APIConfig `yaml:"dns_conf"`
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

// CheckConfig check whether config field invalid
func (c *Config) CheckConfig() error {
	var hasAgent, hasGM bool
	if c.AgentConf != nil {
		hasAgent = true
	}
	if c.GMConf != nil {
		hasGM = true
	}

	if hasAgent && hasGM && c.AgentConf.CloudID != c.GMConf.CloudID {
		fmt.Printf("the cloud id of agent and gm is not equal")
		return fmt.Errorf("the cloud id of agent and gm is not equal")
	}

	return nil
}

func (c *Config) GetCloudId() int {
	if c.AgentConf != nil {
		return c.AgentConf.CloudID
	}
	if c.GMConf != nil {
		return c.GMConf.CloudID
	}

	fmt.Printf("gm and agent lack cloud_id field")
	return 0
}
