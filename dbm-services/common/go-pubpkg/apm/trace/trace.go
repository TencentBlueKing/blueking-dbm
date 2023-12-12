/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package trace TODO
package trace

import (
	"context"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/viper"
)

const (
	// TracerName trace name
	TracerName      = "bk-dbm/http-tracer"
	EnablePath      = "trace.enable"
	HostPath        = "trace.otlp.host"
	PortPath        = "trace.otlp.port"
	TokenPath       = "trace.otlp.token"
	OtlpTypePath    = "trace.otlp.type"
	ServiceNamePath = "trace.service_name"
	DataIDPath      = "trace.dataid"
)

var (
	OtlpEnable                    bool
	OtlpType                      string
	otlpHost, otlpPort, otlpToken string
	ServiceName                   string
	DataID                        int64
)

// Setup setupTrace
func Setup() {
	logger.Info(
		"setup trace for service: %s, please check: \n"+
			"TRACE_HOST: %s\n"+
			"TRACE_PORT: %s\n"+
			"TRACE_TOKEN: %s\n"+
			"TRACE_TYPE: %s\n"+
			"TRACE_SERVICE_NAME: %s\n"+
			"TRACE_DATA_ID: %s\n",
		ServiceName, otlpHost, otlpPort, otlpToken, OtlpType, DataID, ServiceName)

	if OtlpEnable {
		if otlpHost != "" && otlpPort != "" && otlpToken != "" && OtlpType != "" && DataID != 0 {
			logger.Info("init trace for service: %s", ServiceName)
			traceService := &Service{}
			traceService.Reload(context.TODO())
		} else {
			logger.Error("skip init trace for service: %s, please check trace config: %s\n", ServiceName)
		}
	} else {
		logger.Warn("skip init trace for disabled service: %s", ServiceName)
	}
}

// setDefaultConfig
func setDefaultConfig() {
	viper.AutomaticEnv()

	_ = viper.BindEnv(EnablePath, "TRACE_ENABLE")
	_ = viper.BindEnv(HostPath, "TRACE_HOST")
	_ = viper.BindEnv(PortPath, "TRACE_PORT")
	_ = viper.BindEnv(TokenPath, "TRACE_TOKEN")
	_ = viper.BindEnv(OtlpTypePath, "TRACE_TYPE")
	_ = viper.BindEnv(ServiceNamePath, "TRACE_SERVICE_NAME")
	_ = viper.BindEnv(DataIDPath, "TRACE_DATA_ID")

}

// InitConfig TODO
func InitConfig() {
	OtlpEnable = viper.GetBool(EnablePath)
	if !OtlpEnable {
		logger.Info("trace disabled.")
		return
	}

	logger.Info("trace enabled.")
	DataID = viper.GetInt64(DataIDPath)
	otlpHost = viper.GetString(HostPath)
	otlpPort = viper.GetString(PortPath)
	otlpToken = viper.GetString(TokenPath)
	logger.Info("trace will Otlp url->[%s:%s] token->[%s] dataid->[%s]", otlpHost, otlpPort, otlpToken, DataID)

	OtlpType = viper.GetString(OtlpTypePath)
	logger.Info("trace will Otlp as %s type", OtlpType)

	ServiceName = viper.GetString(ServiceNamePath)
	logger.Info("trace will Otlp service name:%s", ServiceName)
}

// init
func init() {
	logger.Info("trace init.")
	setDefaultConfig()
	InitConfig()
}
