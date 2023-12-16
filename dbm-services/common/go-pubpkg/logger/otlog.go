/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package logger

import (
	"context"
	"fmt"

	"github.com/uptrace/opentelemetry-go-extra/otelzap"
	"go.uber.org/zap/zapcore"
)

var OtLogger = otelzap.New(GetLogger(),
	otelzap.WithTraceIDField(true),
	otelzap.WithCaller(true),
	otelzap.WithStackTrace(true),
	otelzap.WithMinLevel(zapcore.InfoLevel),
	otelzap.WithErrorStatusLevel(zapcore.ErrorLevel),
)

// Warnf TODO
func Warnf(ctx context.Context, format string, v ...any) {
	OtLogger.Ctx(ctx).Warn(fmt.Sprintf(format, v...))
}

// Infof TODO
func Infof(ctx context.Context, format string, v ...any) {
	OtLogger.Ctx(ctx).Info(fmt.Sprintf(format, v...))
}

// Errorf TODO
func Errorf(ctx context.Context, format string, v ...any) {
	OtLogger.Ctx(ctx).Error(fmt.Sprintf(format, v...))
}

// Debugf TODO
func Debugf(ctx context.Context, format string, v ...any) {
	OtLogger.Ctx(ctx).Debug(fmt.Sprintf(format, v...))
}

// Panicf TODO
func Panicf(ctx context.Context, format string, v ...any) {
	OtLogger.Ctx(ctx).Panic(fmt.Sprintf(format, v...))
}

// Fatalf TODO
func Fatalf(ctx context.Context, format string, v ...any) {
	OtLogger.Ctx(ctx).Fatal(fmt.Sprintf(format, v...))
}
