/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package config TODO
package config

import (
	"log"

	"dbm-services/common/db-resource/internal/svr/yunti"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/viper"
)

// AppConfig static app config
var AppConfig Config

// Config config tpl
type Config struct {
	Gormlog             bool   `yaml:"gormlog"`
	RunMode             string `yaml:"runMode"`
	ListenAddress       string `yaml:"listenAddress"`
	NotInspectionBizids string `yaml:"notInspectionBizids"`
	//	dbmeta: http://bk-dbm
	DbMeta           string            `yaml:"dbmeta"`
	BkCmdbApiUrl     string            `yaml:"bkCmdbApiUrl"`
	BkJobApiUrl      string            `yaml:"bkJobApiUrl"`
	BkNodeManApiUrl  string            `yaml:"bkNodeManApiUrl"`
	Db               Db                `yaml:"db"`
	CmdbDb           Db                `yaml:"cmdb_db" mapstructure:"cmdb_db"`
	LoggerConfig     LoggerConfig      `yaml:"loggerConfig"`
	BkSecretConfig   BkSecretConfig    `yaml:"bkSecretConfig"`
	Redis            Redis             `yaml:"redis"`
	CloudCertificate *CloudCertificate `yaml:"cloudCertificate"`
	Yunti            yunti.YuntiConfig `yaml:"yunti"`
	LLM              LLMConfig         `yaml:"llm" mapstructure:"llm"`
	// 中转业务ID
	TransBizId int `yaml:"transBizId"`
	// CheckExt3DataDisk 导入机器时是否检查数据盘为 ext3，未配置时默认 true
	CheckExt3DataDisk bool   `yaml:"checkExt3DataDisk" mapstructure:"checkExt3DataDisk"`
	Tenant            Tenant `yaml:"tenant"`
}

// LLMConfig LLM 大模型配置
type LLMConfig struct {
	Enabled  bool         `yaml:"enabled" mapstructure:"enabled"`
	Provider string       `yaml:"provider" mapstructure:"provider"` // openai / azure
	OpenAI   OpenAIConfig `yaml:"openai" mapstructure:"openai"`
	Agent    AgentConfig  `yaml:"agent" mapstructure:"agent"`
	BkAi     BkAiConfig   `yaml:"bk_ai" mapstructure:"bk_ai"`
}

// BkAiConfig Bk AI 配置
type BkAiConfig struct {
	AppCode   string `yaml:"app_code" mapstructure:"app_code"`
	AppSecret string `yaml:"app_secret" mapstructure:"app_secret"`
	BaseURL   string `yaml:"base_url" mapstructure:"base_url"`
	Model     string `yaml:"model" mapstructure:"model"`
	MaxTokens int    `yaml:"max_tokens" mapstructure:"max_tokens"`
	// Temperature 采样温度，用指针区分「未配置」与「显式配置为 0」
	Temperature *float32 `yaml:"temperature" mapstructure:"temperature"`
}

// OpenAIConfig OpenAI 配置
type OpenAIConfig struct {
	APIKey      string  `yaml:"api_key" mapstructure:"api_key"`
	BaseURL     string  `yaml:"base_url" mapstructure:"base_url"`
	Model       string  `yaml:"model" mapstructure:"model"`
	MaxTokens   int     `yaml:"max_tokens" mapstructure:"max_tokens"`
	Temperature float32 `yaml:"temperature" mapstructure:"temperature"`
}

// AgentConfig Agent 配置
type AgentConfig struct {
	MaxIterations  int `yaml:"max_iterations" mapstructure:"max_iterations"`
	TimeoutSeconds int `yaml:"timeout_seconds" mapstructure:"timeout_seconds"`
}

// Tenant config
type Tenant struct {
	Id     string `yaml:"id"`
	Enable bool   `yaml:"enable"`
}

// Db config
type Db struct {
	Name         string `yaml:"name"`
	Addr         string `yaml:"addr"`
	UserName     string `yaml:"username"`
	PassWord     string `yaml:"password"`
	MaxOpenConns int    `yaml:"maxOpenConns"`
	MaxIdleConns int    `yaml:"maxIdleConns"`
	MaxLifetime  int    `yaml:"maxLifetime"` // 单位：小时
}

// 数据库连接池默认值
const (
	defaultMaxOpenConns = 200
	defaultMaxIdleConns = 20
	defaultMaxLifetime  = 1 // 小时
)

// SetDefaults 为零值字段填充默认值
func (c *Db) SetDefaults() {
	if c.MaxOpenConns <= 0 {
		c.MaxOpenConns = defaultMaxOpenConns
	}
	if c.MaxIdleConns <= 0 {
		c.MaxIdleConns = defaultMaxIdleConns
	}
	if c.MaxLifetime <= 0 {
		c.MaxLifetime = defaultMaxLifetime
	}
}

// LoggerConfig 日志配置
type LoggerConfig struct {
	LogWriters string `yaml:"logWriters"` // file,stdout
	LogLevel   string `yaml:"logLevel"`
	LogFile    string `yaml:"logfile"`
}

// BkSecretConfig TODO
type BkSecretConfig struct {
	BkAppCode   string `yaml:"bk_app_code" mapstructure:"bk_app_code"`
	BKAppSecret string `yaml:"bk_app_secret" mapstructure:"bk_app_secret"`
	BkUserName  string `yaml:"bk_username" mapstructure:"bk_username"`
	BkBaseUrl   string `yaml:"bk_base_url" mapstructure:"bk_base_url"`
	GseBaseUrl  string `yaml:"gse_base_url" mapstructure:"gse_base_url"`
}

// Redis redis
type Redis struct {
	Addr     string `yaml:"addr"`
	Password string `yaml:"password"`
}

// CloudCertificate TODO
type CloudCertificate struct {
	// cloud vendor reserved field
	CloudVendor string `yaml:"cloud_vendor" mapstructure:"cloud_vendor"`
	SecretId    string `yaml:"secret_id" mapstructure:"secret_id"`
	SecretKey   string `yaml:"secret_key" mapstructure:"secret_key"`
} // load configuration file

// InitConfig 初始化配置
func InitConfig() {
	log.Println("init config")
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./conf")
	viper.AddConfigPath("$HOME/conf")
	viper.AddConfigPath("./")
	// 未配置时默认开启 ext3 数据盘检查，兼容存量配置文件
	viper.SetDefault("checkExt3DataDisk", true)
	if err := viper.ReadInConfig(); err != nil {
		logger.Fatal("failed to read configuration file:%v", err)
	}
	if err := viper.Unmarshal(&AppConfig); err != nil {
		logger.Fatal("unmarshal configuration failed: %v", err)
	}
	AppConfig.Db.SetDefaults()
	AppConfig.CmdbDb.SetDefaults()
}
