// Package dtstaskstatus 从本机 Master OpenAPI 拉取任务状态并上报。
package dtstaskstatus

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
)

const name = "dts-task-status"

const httpTimeout = 5 * time.Second

type Checker struct {
	httpGet func(url string) ([]byte, error)
}

func defaultHTTPGet(url string) ([]byte, error) {
	client := &http.Client{Timeout: httpTimeout}
	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("openapi status %d: %s", resp.StatusCode, strings.TrimSpace(string(body)))
	}
	return body, nil
}

func masterTasksURL(ip string, port int) (string, error) {
	ip = strings.TrimSpace(ip)
	if ip == "" || port <= 0 {
		return "", fmt.Errorf("dts master listen addr is empty")
	}
	return "http://" + net.JoinHostPort(ip, strconv.Itoa(port)) + "/api/v1/tasks?with_status=true", nil
}

func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	ip, port := "", 0
	if config.MonitorConfig != nil {
		ip = config.MonitorConfig.Ip
		port = config.MonitorConfig.Port
	}
	url, err := masterTasksURL(ip, port)
	if err != nil {
		return nil, "", err
	}
	getter := c.httpGet
	if getter == nil {
		getter = defaultHTTPGet
	}
	body, err := getter(url)
	if err != nil {
		return nil, "", err
	}
	tasks, err := parseTaskList(body)
	if err != nil {
		return nil, "", err
	}
	for _, task := range tasks {
		dim := taskDimension(task)
		utils.SendMonitorMetrics(metricTaskState, task.StageValue, dim)
		if task.Lag != nil {
			utils.SendMonitorMetrics(metricLag, *task.Lag, dim)
		}
	}
	return nil, "", nil
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(_ *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}
