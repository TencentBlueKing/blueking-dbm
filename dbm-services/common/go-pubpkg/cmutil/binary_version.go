/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmutil

import (
	"strings"
	"unicode/utf8"
)

const versionLogBytes = 300

// LogBinaryVersion 的调用方必须已经把 libmydumper 放进 LD_LIBRARY_PATH。
func LogBinaryVersion(bin string, info func(string, ...interface{}), warn func(string, ...interface{})) {
	bin = strings.TrimSpace(bin)
	if bin == "" {
		if warn != nil {
			warn("版本探测失败，二进制路径为空")
		}
		return
	}

	stdout, stderr, err := ExecCommand(false, "", bin, "--version")
	text := firstNonEmptyLine(stdout)
	if text == "" {
		text = firstNonEmptyLine(stderr)
	}
	text = capLogLine(text, versionLogBytes)
	if err != nil || text == "" {
		if warn != nil {
			warn("%s 版本探测失败: %s", bin, capLogLine(versionProbeReason(err, text), versionLogBytes))
		}
		return
	}
	if info != nil {
		info("%s 版本: %s", bin, text)
	}
}

func firstNonEmptyLine(s string) string {
	for _, line := range strings.Split(s, "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			return line
		}
	}
	return ""
}

func versionProbeReason(err error, text string) string {
	switch {
	case err != nil && text != "":
		return err.Error() + ": " + text
	case err != nil:
		return err.Error()
	default:
		return text
	}
}

func capLogLine(s string, maxBytes int) string {
	if len(s) <= maxBytes {
		return s
	}
	end := maxBytes
	for end > 0 && !utf8.RuneStart(s[end]) {
		end--
	}
	return s[:end]
}
