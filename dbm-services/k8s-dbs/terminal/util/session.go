/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package util

import (
	"fmt"
	"strings"
)

const (
	DefaultCwd = "/"
	CwdMarker  = "<<<CWD_MARKER>>>"
)

// TerminalSession 保存与一个 WebSocket 连接绑定的会话态（cwd 跟踪）
type TerminalSession struct {
	currentCwd string
	promptHost string
	promptUser string
}

// NewTerminalSession 创建新的终端会话
func NewTerminalSession(host, user string) *TerminalSession {
	return &TerminalSession{
		promptHost: host,
		promptUser: user,
		currentCwd: DefaultCwd,
	}
}

// GetCwd 获取当前工作目录
func (s *TerminalSession) GetCwd() string {
	return s.currentCwd
}

// SetCwd 设置当前工作目录
func (s *TerminalSession) SetCwd(cwd string) {
	s.currentCwd = strings.TrimSpace(cwd)
}

// BuildPrompt 构建提示符字符串
func (s *TerminalSession) BuildPrompt() string {
	if s == nil {
		return "$ "
	}

	// 格式化目录显示：只显示最后一级目录名（basename）
	displayPath := formatCwd(s.currentCwd)

	return fmt.Sprintf("%s@%s:%s$ ", s.promptUser, s.promptHost, displayPath)
}

// formatCwd 格式化 cwd 显示（只显示最后一级目录）
func formatCwd(cwd string) string {
	if cwd == "" || cwd == "/" {
		return "/"
	}
	// 去掉尾部斜杠
	cwd = strings.TrimRight(cwd, "/")
	// 获取最后一级目录
	parts := strings.Split(cwd, "/")
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return "~"
}

// ParseCwdFromOutput 从命令输出中解析 cwd（使用标记分隔）
func ParseCwdFromOutput(output, marker string) (actualOutput, newCwd string) {
	parts := strings.Split(output, marker)
	actualOutput = parts[0]
	if len(parts) > 1 {
		// 提取 pwd 输出作为新 cwd
		lines := strings.Split(strings.TrimSpace(parts[1]), "\n")
		if len(lines) > 0 {
			newCwd = strings.TrimSpace(lines[0])
		}
	}
	return actualOutput, newCwd
}
