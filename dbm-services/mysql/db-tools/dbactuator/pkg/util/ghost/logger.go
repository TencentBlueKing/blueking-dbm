/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package ghost

import (
	"fmt"

	"github.com/openark/golib/log"

	"dbm-services/common/go-pubpkg/logger"
)

type ghostLogger struct{}

func transGhost2dbmLogger() *ghostLogger {
	return &ghostLogger{}
}

func (*ghostLogger) Debug(args ...any) {
	if len(args) == 0 {
		return
	}
	if format, ok := args[0].(string); ok {
		logger.Debug(fmt.Sprintf(format, args[1:]...))
	} else {
		logger.Debug(fmt.Sprint(args...))
	}
}
func (*ghostLogger) Debugf(format string, args ...any) {
	logger.Debug(format, args...)
}

func (*ghostLogger) Info(args ...any) {
	if len(args) == 0 {
		return
	}
	if format, ok := args[0].(string); ok {
		logger.Info(fmt.Sprintf(format, args[1:]...))
	} else {
		logger.Info(fmt.Sprint(args...))
	}
}

func (*ghostLogger) Infof(format string, args ...any) {
	logger.Info(format, args...)
}

func (*ghostLogger) Warning(args ...any) error {
	if len(args) == 0 {
		return nil
	}
	if format, ok := args[0].(string); ok {
		logger.Warn(fmt.Sprintf(format, args[1:]...))
		return fmt.Errorf(format, args[1:]...)
	} else {
		msg := fmt.Sprint(args...)
		logger.Warn(msg)
		return fmt.Errorf(msg)
	}
}

func (*ghostLogger) Warningf(format string, args ...any) error {
	logger.Warn(format, args...)
	return fmt.Errorf(format, args...)
}

func (*ghostLogger) Error(args ...any) error {
	if len(args) == 0 {
		return nil
	}
	if format, ok := args[0].(string); ok {
		logger.Error(fmt.Sprintf(format, args[1:]...))
		return fmt.Errorf(format, args[1:]...)
	} else {
		msg := fmt.Sprint(args...)
		logger.Error(msg)
		return fmt.Errorf(msg)
	}
}

func (*ghostLogger) Errorf(format string, args ...any) error {
	logger.Error(format, args...)
	return fmt.Errorf(format, args...)
}

func (*ghostLogger) Errore(err error) error {
	if err != nil {
		logger.Error(err.Error())
	}
	return err
}

func (*ghostLogger) Fatal(args ...any) error {
	if len(args) == 0 {
		return nil
	}
	if format, ok := args[0].(string); ok {
		logger.Error(fmt.Sprintf(format, args[1:]...))
		return fmt.Errorf(format, args[1:]...)
	} else {
		msg := fmt.Sprint(args...)
		logger.Error(msg)
		return fmt.Errorf(msg)
	}
}

func (*ghostLogger) Fatalf(format string, args ...any) error {
	logger.Error(format, args...)
	return fmt.Errorf(format, args...)
}

func (*ghostLogger) Fatale(err error) error {
	if err != nil {
		logger.Error(err.Error())
	}
	return err
}

func (*ghostLogger) SetLevel(_ log.LogLevel) {
}

func (*ghostLogger) SetPrintStackTrace(_ bool) {
}
