/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Package config provides configuration management for the DBHA v2 admin module.
package config

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

var Cfg = Configuration{
	Name:    "admin",
	PidFile: "./pids/admin.pid",
	Log: LogConfig{
		Path:      "./logs/admin.log",
		Level:     logger.InfoLevel.String(),
		FileCount: 10,
		FileSize:  100,
	},
}

// DiscoveryConfig discovery configuration
type DiscoveryConfig struct {
	Endpoint string `yaml:"endpoint" mapstructure:"endpoint"`
	User     string `yaml:"user"     mapstructure:"user"`
	Password string `yaml:"password" mapstructure:"password"`
}

// ApmConfig apm's configuration
type ApmConfig struct {
	ReadTimeout   time.Duration `yaml:"readTimeout"   mapstructure:"readTimeout"`
	WriteTimeout  time.Duration `yaml:"writeTimeout"  mapstructure:"writeTimeout"`
	ListenAddress string        `yaml:"listenAddress" mapstructure:"listenAddress"`
}

// GrpcConfig grpc configuration
type GrpcConfig struct {
	ListenAddress string `yaml:"listenAddress" mapstructure:"listenAddress"`
}

// WebConfig web configuration
type WebConfig struct {
	Host         string        `yaml:"host" 		 mapstructure:"host"`
	Port         int           `yaml:"port" 		 mapstructure:"port"`
	ReadTimeout  time.Duration `yaml:"readTimeout"   mapstructure:"readTimeout"`
	WriteTimeout time.Duration `yaml:"writeTimeout"  mapstructure:"writeTimeout"`
}

// DbmApi the API config of the DBM metadata
type DbmApi struct {
	Name    string        `yaml:"name"    mapstructure:"name"`
	Api     string        `yaml:"api"     mapstructure:"api"`
	Token   string        `yaml:"token"   mapstructure:"token"`
	Method  string        `yaml:"method"  mapstructure:"method"`
	Timeout time.Duration `yaml:"timeout" mapstructure:"timeout"`
}

// StorageConfig dbha database configuration
type StorageConfig struct {
	Endpoint string `yaml:"endpoint" mapstructure:"endpoint"`
	User     string `yaml:"user"     mapstructure:"user"`
	Password string `yaml:"password" mapstructure:"password"`
}

// LogConfig log configuration
type LogConfig struct {
	Path      string `yaml:"path"      mapstructure:"path"`
	Level     string `yaml:"level"     mapstructure:"level"`
	FileCount int    `yaml:"fileCount" mapstructure:"fileCount"`
	FileSize  int    `yaml:"fileSize"  mapstructure:"fileSize"`
}

// Configuration admin's configuration
type Configuration struct {
	Name       string          `yaml:"name"       mapstructure:"name"`
	Version    string          `yaml:"version"    mapstructure:"version"`
	PidFile    string          `yaml:"pidFile"    mapstructure:"pidFile"`
	DocFileDir string          `yaml:"docFileDir" mapstructure:"docFileDir"`
	Discovery  DiscoveryConfig `yaml:"discovery"  mapstructure:"discovery"`
	Apm        ApmConfig       `yaml:"apm"        mapstructure:"apm"`
	Grpc       GrpcConfig      `yaml:"grpc"       mapstructure:"grpc"`
	Web        WebConfig       `yaml:"web"        mapstructure:"web"`
	DbmApis    []DbmApi        `yaml:"dbmApi"     mapstructure:"dbmApi"`
	Storage    StorageConfig   `yaml:"storage"    mapstructure:"storage"`
	Log        LogConfig       `yaml:"log"        mapstructure:"log"`
}
