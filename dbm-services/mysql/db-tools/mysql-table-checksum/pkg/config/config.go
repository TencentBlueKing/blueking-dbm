// Package config 配置库
package config

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"log/slog"
	"os"
	"path"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v2"
)

// ChecksumConfig 校验配置
var ChecksumConfig *Config

type Host struct {
	Ip       string `yaml:"ip"`
	Port     int    `yaml:"port"`
	User     string `yaml:"user"`
	Password string `yaml:"password"`
}

type Filter struct {
	Databases            []string `yaml:"databases"`
	Tables               []string `yaml:"tables"`
	IgnoreDatabases      []string `yaml:"ignore_databases"`
	IgnoreTables         []string `yaml:"ignore_tables"`
	DatabasesRegex       string   `yaml:"databases_regex"`
	TablesRegex          string   `yaml:"tables_regex"`
	IgnoreDatabasesRegex string   `yaml:"ignore_databases_regex"`
	IgnoreTablesRegex    string   `yaml:"ignore_tables_regex"`
}

type PtChecksum struct {
	Path      string                   `yaml:"path"`
	Switches  []string                 `yaml:"switches"`
	Args      []map[string]interface{} `yaml:"args"`
	Replicate string                   `yaml:"replicate"`
}

type Cluster struct {
	Id           int    `yaml:"id"`
	ImmuteDomain string `yaml:"immute_domain"`
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
	BkBizId    int `yaml:"bk_biz_id"`
	Cluster    `yaml:"cluster"`
	Host       `yaml:",inline"`
	InnerRole  InnerRoleEnum `yaml:"inner_role"`
	ReportPath string        `yaml:"report_path"`
	Slaves     []Host        `yaml:"slaves"`
	Filter     Filter        `yaml:"filter"`
	PtChecksum PtChecksum    `yaml:"pt_checksum"`
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

func (c *Config) SetFilter(dbPatterns, ignoreDbPatterns, tablePatterns, ignoreTablesPatterns []string) {
	var p1, p2, p3, p4 []string
	for _, p := range dbPatterns {
		if db_table_filter.ContainGlob(p) {
			p1 = append(p1, p)
		} else {
			c.Filter.Databases = append(c.Filter.Databases, p)
		}
	}
	for _, p := range ignoreDbPatterns {
		if db_table_filter.ContainGlob(p) {
			p2 = append(p2, p)
		} else {
			c.Filter.IgnoreDatabases = append(c.Filter.IgnoreDatabases, p)
		}
	}
	for _, p := range tablePatterns {
		if db_table_filter.ContainGlob(p) {
			p3 = append(p3, p)
		} else {
			c.Filter.Tables = append(c.Filter.Tables, p)
		}
	}
	for _, p := range ignoreTablesPatterns {
		if db_table_filter.ContainGlob(p) {
			p4 = append(p4, p)
		} else {
			c.Filter.IgnoreTables = append(c.Filter.IgnoreTables, p)
		}
	}

	if len(p1) > 0 {
		c.Filter.DatabasesRegex = buildRegex(p1)
	}
	if len(p2) > 0 {
		c.Filter.IgnoreDatabasesRegex = buildRegex(p2)
	}
	if len(p3) > 0 {
		c.Filter.TablesRegex = buildRegex(p3)
	}
	if len(p4) > 0 {
		c.Filter.IgnoreTablesRegex = buildRegex(p4)
	}
}

func buildRegex(ps []string) string {
	if len(ps) <= 0 {
		return ""
	}

	res := strings.Join(db_table_filter.ReplaceGlobs(ps), "|")
	return res
}
