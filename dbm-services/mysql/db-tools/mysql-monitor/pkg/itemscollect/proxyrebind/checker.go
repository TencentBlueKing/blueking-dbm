package proxyrebind

import (
	"bufio"
	"bytes"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"fmt"
	"log/slog"
	"os/exec"
	"regexp"
	"strings"

	"github.com/pkg/errors"
)

var name = "proxy-rebind"
var re *regexp.Regexp

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

	commandPath, err := exec.LookPath("lsof")
	if err != nil {
		slog.Error("find lsof failed", slog.String("error", err.Error()))
		return "", err
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
