/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

import (
	"fmt"
	"os"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
)

const (
	// DefaultErrorExitCode TODO
	DefaultErrorExitCode = 1
)

// CheckErr TODO
func CheckErr(err error) {
	if err == nil {
		return
	}
	msg, ok := StandardErrorMessage(err)
	if !ok {
		msg = err.Error()
		if !strings.HasPrefix(msg, "error: ") {
			msg = fmt.Sprintf("error: %s", msg)
		}
	}
	LoggerErrorStack(logger.Error, err)
	fatal(msg, DefaultErrorExitCode)
}

func fatal(msg string, code int) {
	if len(msg) > 0 {
		// add newline if needed
		if !strings.HasSuffix(msg, "\n") {
			msg += "\n"
		}
		fmt.Fprint(os.Stderr, msg)
	}
	os.Exit(code)
}

type debugError interface {
	DebugError() (msg string, args []interface{})
}

// StandardErrorMessage TODO
func StandardErrorMessage(err error) (string, bool) {
	if debugErr, ok := err.(debugError); ok {
		logger.Info(debugErr.DebugError())
	}
	return "", false
}
