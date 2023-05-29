// Package config 配置库
package config

import (
	"log/slog"
	"os"
	"path"
	"path/filepath"

	"gopkg.in/yaml.v2"
)

// ChecksumConfig 校验配置
var ChecksumConfig *Config

type host struct {
	Ip       string `yaml:"ip"`
	Port     int    `yaml:"port"`
	User     string `yaml:"user"`
	Password string `yaml:"password"`
}

type filter struct {
	Databases            []string `yaml:"databases"`
	Tables               []string `yaml:"tables"`
	IgnoreDatabases      []string `yaml:"ignore_databases"`
	IgnoreTables         []string `yaml:"ignore_tables"`
	DatabasesRegex       string   `yaml:"databases_regex"`
	TablesRegex          string   `yaml:"tables_regex"`
	IgnoreDatabasesRegex string   `yaml:"ignore_databases_regex"`
	IgnoreTablesRegex    string   `yaml:"ignore_tables_regex"`
}

type ptChecksum struct {
	Path      string                   `yaml:"path"`
	Switches  []string                 `yaml:"switches"`
	Args      []map[string]interface{} `yaml:"args"`
	Replicate string                   `yaml:"replicate"`
}

// InnerRoleEnum 枚举
type InnerRoleEnum string

const (
	// RoleMaster master
	RoleMaster InnerRoleEnum = "master"
	// RoleRepeater repeater
	RoleRepeater InnerRoleEnum = "repeater"
	// RoleSlave slave
	RoleSlave InnerRoleEnum = "slave"
)

// Config 配置结构
type Config struct {
	BkBizId int `yaml:"bk_biz_id"`
	Cluster struct {
		Id           int    `yaml:"id"`
		ImmuteDomain string `yaml:"immute_domain"`
	} `yaml:"cluster"`
	host       `yaml:",inline"`
	InnerRole  InnerRoleEnum `yaml:"inner_role"`
	ReportPath string        `yaml:"report_path"`
	Slaves     []host        `yaml:"slaves"`
	Filter     filter        `yaml:"filter"`
	PtChecksum ptChecksum    `yaml:"pt_checksum"`
	Log        *LogConfig    `yaml:"log"`
	Schedule   string        `yaml:"schedule"`
	ApiUrl     string        `yaml:"api_url"`
}

// InitConfig 初始化配置
func InitConfig(configPath string) error {
	if !path.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			slog.Error("init config", slog.String("error", err.Error()))
			return err
		}
		configPath = filepath.Join(cwd, configPath)
	}

	content, err := os.ReadFile(configPath)
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}

	ChecksumConfig = &Config{}
	err = yaml.UnmarshalStrict(content, ChecksumConfig)
	if err != nil {
		slog.Error("init config", slog.String("error", err.Error()))
		return err
	}

	return nil
}
