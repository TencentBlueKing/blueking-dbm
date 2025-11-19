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
	"bufio"
	"context"
	"fmt"
	"io"
	"log/slog"
	"strings"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/tools/remotecommand"

	commutil "k8s-dbs/common/util"
)

const (
	// Shell 类型
	shellTypeBash = "bash"
	shellTypeSh   = "sh"

	// 标记字符串
	initDoneMarker  = "__INIT_DONE__"
	exitCodePrefix  = "__EXIT_CODE__"
	endMarkerPrefix = "__DBM_END_"

	// 超时设置
	shellInitTimeout   = 3 * time.Second
	shellInitWait      = 50 * time.Millisecond
	commandExecTimeout = 30 * time.Second
	shellCloseTimeout  = 2 * time.Second
)

// Shell 持久化的 shell 会话，复用单个 Kubernetes exec 连接
type Shell struct {
	k8sClient *commutil.K8sClient
	namespace string
	podName   string

	stdin  io.WriteCloser
	stdout *bufio.Reader
	stderr *bufio.Reader

	cmdMutex sync.Mutex // 确保命令串行执行

	ctx    context.Context
	cancel context.CancelFunc
	done   chan struct{}

	currentCwd string
	shellType  string // "bash" 或 "sh"
}

// CommandResult 命令执行结果
type CommandResult struct {
	Output   string
	ExitCode string
	Cwd      string
	Error    error
}

// NewShell 创建持久化 shell 会话
func NewShell(
	k8sClient *commutil.K8sClient,
	namespace string,
	podName string,
) (*Shell, error) {
	ctx, cancel := context.WithCancel(context.Background())

	s := &Shell{
		k8sClient: k8sClient,
		namespace: namespace,
		podName:   podName,
		ctx:       ctx,
		cancel:    cancel,
		done:      make(chan struct{}),
	}

	// 尝试启动 shell
	if err := s.start(); err != nil {
		cancel()
		return nil, fmt.Errorf("启动持久 shell 失败: %w", err)
	}

	return s, nil
}

// start 启动持久 shell 进程
func (s *Shell) start() error {
	// 优先尝试 bash（补全更完善），再降级到 sh
	shells := []string{"/bin/bash", "bash", "/bin/sh", "sh"}

	var lastErr error
	for _, shell := range shells {
		// 先设置 shellType，以便 initShell 使用
		if strings.Contains(shell, "bash") {
			s.shellType = shellTypeBash
		} else {
			s.shellType = shellTypeSh
		}

		err := s.startShell(shell)
		if err == nil {
			return nil
		}
		lastErr = err
	}

	slog.Error("所有 shell 都无法启动", "error", lastErr, "podName", s.podName)
	return fmt.Errorf("所有 shell 都无法启动，最后错误: %w", lastErr)
}

// startShell 启动指定的 shell
func (s *Shell) startShell(shellPath string) error {
	req := s.k8sClient.ClientSet.CoreV1().RESTClient().Post().
		Resource("pods").
		Name(s.podName).
		Namespace(s.namespace).
		SubResource("exec")

	// 使用交互模式但不启用 TTY
	req.VersionedParams(&corev1.PodExecOptions{
		Command: []string{shellPath, "-i"},
		Stdin:   true,
		Stdout:  true,
		Stderr:  true,
		TTY:     false,
	}, scheme.ParameterCodec)

	executor, err := remotecommand.NewSPDYExecutor(s.k8sClient.RestConfig, "POST", req.URL())
	if err != nil {
		return err
	}

	// 创建管道
	stdinReader, stdinWriter := io.Pipe()
	stdoutReader, stdoutWriter := io.Pipe()
	stderrReader, stderrWriter := io.Pipe()

	s.stdin = stdinWriter
	s.stdout = bufio.NewReader(stdoutReader)
	s.stderr = bufio.NewReader(stderrReader)

	// 每次启动都创建新的 done channel（避免重复关闭）
	s.done = make(chan struct{})

	// 启动 executor
	go func() {
		defer close(s.done)
		_ = executor.StreamWithContext(s.ctx, remotecommand.StreamOptions{
			Stdin:  stdinReader,
			Stdout: stdoutWriter,
			Stderr: stderrWriter,
		})
		stdinReader.Close()
		stdoutWriter.Close()
		stderrWriter.Close()
	}()

	// 初始化 shell 环境
	return s.initShell()
}

// initShell 初始化 shell 环境
func (s *Shell) initShell() error {
	// 等待 shell 启动（缩短等待时间）
	time.Sleep(shellInitWait)

	// 禁用 prompt 和其他干扰输出
	initCommands := []string{
		"PS1=''", // 禁用主 prompt
		"PS2=''", // 禁用次 prompt
	}

	if s.shellType == shellTypeBash {
		initCommands = append(initCommands,
			"unset PROMPT_COMMAND",          // 禁用 prompt 命令
			"set +o histexpand 2>/dev/null", // 禁用历史扩展
			"HISTFILE=/dev/null",            // 禁用历史文件
		)
	}

	// 写入初始化命令，使用标记确认完成
	marker := initDoneMarker
	for _, cmd := range initCommands {
		fmt.Fprintf(s.stdin, "%s 2>/dev/null || true\n", cmd)
	}
	fmt.Fprintf(s.stdin, "echo '%s'\n", marker)

	// 读取直到看到标记（带超时）
	timeout := time.After(shellInitTimeout)
	initSuccess := false
	for {
		select {
		case <-timeout:
			return fmt.Errorf("shell 初始化超时")
		case <-s.ctx.Done():
			return fmt.Errorf("shell 已关闭")
		default:
			line, err := s.stdout.ReadString('\n')
			if err != nil {
				return fmt.Errorf("shell 初始化失败: %w", err)
			}
			if strings.Contains(line, marker) {
				initSuccess = true
				goto initDone
			}
		}
	}

initDone:
	if !initSuccess {
		return fmt.Errorf("shell 初始化未完成")
	}

	// 获取初始 cwd
	result := s.Execute("pwd")
	if result.Error != nil {
		return fmt.Errorf("无法获取初始工作目录: %w", result.Error)
	}

	s.currentCwd = strings.TrimSpace(result.Output)
	if s.currentCwd == "" {
		s.currentCwd = DefaultCwd
	}

	return nil
}

// Execute 执行命令并返回结果
func (s *Shell) Execute(cmd string) CommandResult {
	s.cmdMutex.Lock()
	defer s.cmdMutex.Unlock()

	cmd = strings.TrimSpace(cmd)
	if cmd == "" {
		return CommandResult{Output: "", ExitCode: "0", Cwd: s.currentCwd}
	}

	// 生成唯一标记
	marker := fmt.Sprintf("%s%d__", endMarkerPrefix, time.Now().UnixNano())

	// 构造命令序列：命令 → 输出退出码 → 输出 cwd → 输出标记
	// 使用 { cmd; } 2>&1 将整个代码块的 stderr 重定向到 stdout
	// 不能用 (cmd) 因为括号会创建子 shell，导致 cd 等命令无法改变父 shell 的状态
	script := fmt.Sprintf("{ %s; } 2>&1\necho \"%s$?\"\npwd\necho '%s'\n", cmd, exitCodePrefix, marker)

	// 写入命令
	_, err := s.stdin.Write([]byte(script))
	if err != nil {
		return CommandResult{Error: fmt.Errorf("写入命令失败: %w", err)}
	}

	// 读取输出直到遇到标记
	var lines []string
	timeout := time.After(commandExecTimeout)

	for {
		select {
		case <-timeout:
			return CommandResult{Error: fmt.Errorf("命令执行超时")}
		case <-s.ctx.Done():
			return CommandResult{Error: fmt.Errorf("shell 已关闭")}
		default:
			line, err := s.stdout.ReadString('\n')
			if err != nil {
				if err == io.EOF {
					return CommandResult{Error: fmt.Errorf("shell 连接已断开")}
				}
				return CommandResult{Error: fmt.Errorf("读取输出失败: %w", err)}
			}

			// 检测到结束标记
			if strings.Contains(line, marker) {
				return s.parseOutput(lines)
			}

			lines = append(lines, line)
		}
	}
}

// parseOutput 解析命令输出
func (s *Shell) parseOutput(lines []string) CommandResult {
	if len(lines) < 2 {
		return CommandResult{
			Output:   strings.Join(lines, ""),
			ExitCode: "0",
			Cwd:      s.currentCwd,
		}
	}

	// 最后两行是：__EXIT_CODE__0 和 /path/to/cwd
	n := len(lines)
	exitCodeLine := strings.TrimSpace(lines[n-2])
	cwdLine := strings.TrimSpace(lines[n-1])

	// 提取退出码
	exitCode := "0"
	if strings.HasPrefix(exitCodeLine, exitCodePrefix) {
		exitCode = strings.TrimPrefix(exitCodeLine, exitCodePrefix)
	}

	// 更新 cwd
	if cwdLine != "" && !strings.Contains(cwdLine, exitCodePrefix) {
		s.currentCwd = cwdLine
	}

	// 实际输出是除了最后两行之外的所有行
	output := strings.Join(lines[:n-2], "")

	return CommandResult{
		Output:   output,
		ExitCode: exitCode,
		Cwd:      s.currentCwd,
	}
}

// Complete 执行 Tab 补全
func (s *Shell) Complete(input string) []string {
	token := ExtractLastToken(input)

	// 判断是否为命令补全位置
	// 规则：
	// 1. 如果包含路径分隔符（/, ./, ../），则按文件/目录补全
	// 2. 如果有空白分隔符（如 "ls "），则按文件/目录补全
	// 3. 否则按命令补全
	isPathLike := strings.Contains(token, "/") || strings.HasPrefix(token, "./") || strings.HasPrefix(token, "../")
	hasSep := strings.ContainsAny(input, " \t")
	isCommandCompletion := !hasSep && !isPathLike

	// 根据位置决定补全策略
	var script string
	if s.shellType == shellTypeBash {
		script = s.buildBashCompleteScript(token, isCommandCompletion)
	} else {
		script = s.buildShCompleteScript(token, isCommandCompletion)
	}

	result := s.Execute(script)
	if result.Error != nil {
		slog.Error("补全失败", "error", result.Error)
		return []string{}
	}

	return s.parseCompletions(result.Output, token)
}

// buildBashCompleteScript 构建 bash 补全脚本
func (s *Shell) buildBashCompleteScript(token string, isCommandCompletion bool) string {
	quoted := shellQuote(token)

	if isCommandCompletion {
		// 命令补全
		return fmt.Sprintf("compgen -c -- %s 2>/dev/null", quoted)
	}

	// 文件/目录补全
	script := fmt.Sprintf(
		"compgen -f -- %s 2>/dev/null | while read f; do [ -d \"$f\" ] && echo \"$f/\" || echo \"$f\"; done",
		quoted,
	)
	return script
}

// buildShCompleteScript 构建 sh 兼容的补全脚本
func (s *Shell) buildShCompleteScript(token string, isCommandCompletion bool) string {
	if isCommandCompletion {
		// 命令补全：搜索 PATH
		return fmt.Sprintf(`
IFS=:
for dir in $PATH; do
	[ -d "$dir" ] || continue
	for f in "$dir"/%s*; do
		[ -f "$f" ] && [ -x "$f" ] && basename "$f"
	done
done | sort -u
`, token)
	}

	// 文件/目录补全
	pattern := token

	return fmt.Sprintf(`
for f in %s*; do
	[ -e "$f" ] || continue
	[ -d "$f" ] && echo "$f/" || echo "$f"
done
`, pattern)
}

// parseCompletions 解析补全结果
func (s *Shell) parseCompletions(output string, token string) []string {
	output = strings.TrimSpace(output)
	if output == "" {
		return []string{}
	}

	lines := strings.Split(output, "\n")
	var results []string
	seen := make(map[string]bool)

	// 提取目录前缀
	var dirPrefix string
	if idx := strings.LastIndex(token, "/"); idx >= 0 {
		dirPrefix = token[:idx+1]
	}

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		// 去重
		if !seen[line] {
			seen[line] = true
			results = append(results, line)
		}
	}

	// 如果只有一个结果，保持完整路径供 completeCommand 使用
	if len(results) > 1 && dirPrefix != "" {
		for i, r := range results {
			if strings.HasPrefix(r, dirPrefix) {
				results[i] = strings.TrimPrefix(r, dirPrefix)
			}
		}
	}

	return results
}

// GetCwd 获取当前工作目录
func (s *Shell) GetCwd() string {
	s.cmdMutex.Lock()
	defer s.cmdMutex.Unlock()
	return s.currentCwd
}

// Close 关闭持久 shell
func (s *Shell) Close() error {
	// 发送 exit 命令
	if s.stdin != nil {
		_, _ = s.stdin.Write([]byte("exit\n"))
		s.stdin.Close()
	}

	// 取消 context
	s.cancel()

	// 等待 goroutine 结束（最多 2 秒）
	select {
	case <-s.done:
		// Shell 已正常关闭
	case <-time.After(shellCloseTimeout):
		slog.Warn("Shell 关闭超时", "podName", s.podName)
	}

	return nil
}

// ExtractLastToken 提取输入中的最后一个 token
func ExtractLastToken(s string) string {
	if s == "" || strings.HasSuffix(s, " ") {
		return ""
	}
	s = strings.TrimRight(s, "\t\r\n")
	idx := strings.LastIndexAny(s, " \t")
	if idx == -1 {
		return s
	}
	return s[idx+1:]
}

// shellQuote 将任意字符串以单引号安全包裹，供 POSIX sh 使用
func shellQuote(s string) string {
	if s == "" {
		return "''"
	}
	return "'" + strings.ReplaceAll(s, "'", "'\\''") + "'"
}
