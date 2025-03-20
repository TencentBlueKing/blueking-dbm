// Package config 配置包
package config

import (
	"encoding/json"
	"fmt"
	"time"
)

// BkDbmLabel bk dbm label for Instance
type BkDbmLabel struct {
	BkCloudID     int64  `json:"bk_cloud_id" mapstructure:"bk_cloud_id" yaml:"bk_cloud_id"`
	BkBizID       int    `json:"bk_biz_id" mapstructure:"bk_biz_id" yaml:"bk_biz_id" yaml:"bk_biz_id"`
	App           string `json:"app" mapstructure:"app" yaml:"app"`
	AppName       string `json:"app_name" mapstructure:"app_name" yaml:"app_name"`
	ClusterDomain string `json:"cluster_domain" mapstructure:"cluster_domain" yaml:"cluster_domain"`
	ClusterId     int64  `json:"cluster_id" mapstructure:"cluster_id" yaml:"cluster_id"`
	ClusterName   string `json:"cluster_name" mapstructure:"cluster_name" yaml:"cluster_name"`
	ClusterType   string `json:"cluster_type" mapstructure:"cluster_type" yaml:"cluster_type"`
	RoleType      string `json:"role_type" mapstructure:"role_type" yaml:"role_type"` // shardsvr,mongos,configsvr
	MetaRole      string `json:"meta_role" mapstructure:"meta_role" yaml:"meta_role"` // m0,m1,backup...|mongos
	IP            string `json:"ip" mapstructure:"ip" yaml:"ip"`
	Port          int    `json:"port" mapstructure:"port" yaml:"port" `
	SetName       string `json:"set_name" mapstructure:"set_name" yaml:"set_name"`
}

// ParseBkDbmLabel 解析BkDbmLabel, 允许为空
func ParseBkDbmLabel(labels string) (*BkDbmLabel, error) {
	if labels == "" {
		return &BkDbmLabel{}, nil
	}

	var v = &BkDbmLabel{}
	if err := json.Unmarshal([]byte(labels), v); err != nil {
		return nil, err
	} else {
		return v, nil
	}
}

// ConfServerItem servers配置项
// User Password 可以为空
type ConfServerItem struct {
	BkDbmLabel `yaml:",inline" json:",inline" mapstructure:",squash"`
	UserName   string `yaml:"username" json:"username,omitempty" mapstructure:"username"`
	Password   string `yaml:"password" json:"password,omitempty" mapstructure:"password"`
}

// Addr return ip:port
func (c *ConfServerItem) Addr() string {
	return fmt.Sprintf("%s:%d", c.IP, c.Port)
}

// GetClusterIdStr  return cluster id string
func (c *ConfServerItem) GetClusterIdStr() string {
	return fmt.Sprintf("%d", c.ClusterId)
}

// MetaForLog 用于日志输出.
func (c *ConfServerItem) MetaForLog() string {
	return fmt.Sprintf(
		`"meta":{"app":%q,"appid":%d,"cluster_domain":%q,"cluster_name":%q,"cluster_role":%q,"cluster_type":%q,`+
			`"instance_set_name":%q,`+
			`"instance":%q,"instance_host":%q,"instance_port":%d,"instance_role":%q}`,
		c.App, c.BkBizID,
		c.ClusterDomain, c.ClusterName, c.RoleType, c.ClusterType,
		c.SetName, c.Addr(), c.IP, c.Port, c.MetaRole)
}

// BkMonitorData 注册在Bk的Event.
type BkMonitorData struct {
	DataID int64  `yaml:"data_id" json:"data_id" mapstructure:"data_id"`
	Token  string `yaml:"token" json:"token" mapstructure:"token"`
}

// BkMonitorBeatConfig bkmonitorbeat配置
type BkMonitorBeatConfig struct {
	AgentAddress string        `yaml:"agent_address" json:"agent_address" mapstructure:"agent_address"`
	BeatPath     string        `yaml:"beat_path" json:"beat_path" mapstructure:"beat_path"`
	EventConfig  BkMonitorData `yaml:"event_config"  json:"event_config" mapstructure:"event_config"`
	MetricConfig BkMonitorData `yaml:"metric_config" json:"metric_config" mapstructure:"metric_config"`
}

// Configuration 配置
type Configuration struct {
	ReportSaveDir            string              `yaml:"report_save_dir" json:"report_save_dir" mapstructure:"report_save_dir"`
	ReportLeftDay            int                 `yaml:"report_left_day"  json:"report_left_day" mapstructure:"report_left_day"`
	BackupClientStrorageType string              `yaml:"backup_client_storage_type"  json:"backup_client_storage_type" mapstructure:"backup_client_storage_type"`
	HttpAddress              string              `yaml:"http_address"  json:"http_address" mapstructure:"http_address"`
	BkMonitorBeat            BkMonitorBeatConfig `yaml:"bkmonitorbeat"  json:"bkmonitorbeat" mapstructure:"bkmonitorbeat"`
	Servers                  []ConfServerItem    `yaml:"servers" json:"servers" mapstructure:"servers"`
	LoadTime                 time.Time           `yaml:"-" json:"-" mapstructure:"-"`
	LoadCount                int                 `yaml:"-" json:"-" mapstructure:"-"`
}

func (c *Configuration) SetDefault() {
	if c.BackupClientStrorageType == "" {
		c.BackupClientStrorageType = "cos"
	}
	if c.ReportLeftDay == 0 {
		c.ReportLeftDay = 15
	}
	c.LoadTime = time.Now()
}

// String string
func (c *Configuration) String() string {
	tmp, _ := json.Marshal(c)
	return string(tmp)
}
