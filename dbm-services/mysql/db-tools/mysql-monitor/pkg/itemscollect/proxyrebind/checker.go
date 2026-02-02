package proxyrebind

import (
	"bufio"
	"bytes"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/pkg/errors"
)

var name = "proxy-rebind"
var re *regexp.Regexp

// 常见的系统命令路径
var commonPaths = []string{
	"/usr/bin",
	"/bin",
	"/usr/sbin",
	"/sbin",
	"/usr/local/bin",
	"/usr/local/sbin",
}

// findCommand 在 $PATH 和常见路径中查找命令
func findCommand(cmd string) (string, error) {
	// 合并用户 $PATH 和常见路径，去重
	searchPaths := make([]string, 0)
	seen := make(map[string]bool)

	// 先加入用户 $PATH
	if pathEnv := os.Getenv("PATH"); pathEnv != "" {
		for _, p := range strings.Split(pathEnv, string(os.PathListSeparator)) {
			if p != "" && !seen[p] {
				seen[p] = true
				searchPaths = append(searchPaths, p)
			}
		}
	}

	// 再加入常见路径
	for _, p := range commonPaths {
		if !seen[p] {
			seen[p] = true
			searchPaths = append(searchPaths, p)
		}
	}

	slog.Info("search paths for command", slog.String("cmd", cmd), slog.Any("paths", searchPaths))

	// 在合并后的路径中查找
	for _, dir := range searchPaths {
		fullPath := filepath.Join(dir, cmd)
		if info, err := os.Stat(fullPath); err == nil && !info.IsDir() {
			// 检查是否有执行权限
			if info.Mode()&0111 != 0 {
				slog.Info("found command", slog.String("cmd", cmd), slog.String("path", fullPath))
				return fullPath, nil
			}
		}
	}

	return "", fmt.Errorf("command %s not found in PATH or common paths", cmd)
}

type Checker struct {
	//db *sqlx.DB
}

func (c *Checker) Run() (msg string, err error) {
	re = regexp.MustCompile(
		fmt.Sprintf(
			`^.*%s:%d\s+\(LISTEN\).*$`,
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
		),
	)
	slog.Info("find lsof command", slog.String("PATH", os.Getenv("PATH")))
	commandPath, err := findCommand("lsof")
	if err != nil {
		slog.Error("find lsof failed, skip check", slog.String("error", err.Error()))
		return "", nil
	}
	slog.Info("find lsof command", slog.String("path", commandPath))

	var stdout, stderr bytes.Buffer
	cmd := exec.Command("sh", "-c", fmt.Sprintf("%s -nP -iTCP -sTCP:LISTEN", commandPath))
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()
	slog.Info("run lsof", slog.String("stderr", stderr.String()), slog.String("stdout", stdout.String()))

	if err != nil {
		slog.Error("run lsof", slog.String("err", err.Error()))
		return "", err
	}
	if stderr.String() != "" {
		slog.Error("run lsof", slog.String("stderr", stderr.String()))
		return "", errors.New(stderr.String())
	}

	scanner := bufio.NewScanner(strings.NewReader(strings.TrimSpace(stdout.String())))
	scanner.Split(bufio.ScanLines)

	var cnt int
	for scanner.Scan() {
		if re.MatchString(scanner.Text()) {
			cnt += 1
		}
	}
	if err := scanner.Err(); err != nil {
		slog.Error("run lsof", slog.String("err", err.Error()))
		return "", err
	}

	if cnt > 1 {
		return fmt.Sprintf(
			"%s:%d bind to %d mysql-proxy",
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			cnt,
		), nil
	}

	return "", nil
}

func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
