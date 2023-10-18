package mysql

import (
	"bytes"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path"
	"text/template"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

// DeployMySQLCrondComp 部署参数
type DeployMySQLCrondComp struct {
	GeneralParam *components.GeneralParam `json:"general_param"`
	Params       *DeployMySQLCrondParam   `json:"params"`
	tools        *tools.ToolSet
}

// DeployMySQLCrondParam 部署参数
type DeployMySQLCrondParam struct {
	components.Medium
	Ip        string `json:"ip"`
	BkCloudId int    `json:"bk_cloud_id"`
	// EventName        string `json:"event_name"`
	EventDataId    int    `json:"event_data_id"`
	EventDataToken string `json:"event_data_token"`
	// MetricsName      string `json:"metrics_name"`
	MetricsDataId    int    `json:"metrics_data_id"`
	MetricsDataToken string `json:"metrics_data_token"`
	BeatPath         string `json:"beat_path"`
	AgentAddress     string `json:"agent_address"`
	BkBizId          int    `json:"bk_biz_id"`
}

// Init 初始化二进制位置
func (c *DeployMySQLCrondComp) Init() (err error) {
	c.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMySQLCrond)
	return nil
}

// Precheck 校验码检查
func (c *DeployMySQLCrondComp) Precheck() (err error) {
	if err = c.Params.Check(); err != nil {
		logger.Error("check mysql-crond pkg failed: %s", err.Error())
		return err
	}
	return nil
}

// DeployBinary 部署二进制
func (c *DeployMySQLCrondComp) DeployBinary() (err error) {
	err = os.MkdirAll(cst.MySQLCrondInstallPath, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}

	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		c.Params.Medium.GetAbsolutePath(), cst.MySQLCrondInstallPath,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress mysql-crond pkg failed: %s", err.Error())
		return err
	}

	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.MySQLCrondInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}
	return nil
}

// GeneralRuntimeConfig 生成 runtime 配置
func (c *DeployMySQLCrondComp) GeneralRuntimeConfig() (err error) {
	t, err := template.ParseFiles(path.Join(cst.MySQLCrondInstallPath, "mysql-crond.conf.go.tpl"))
	if err != nil {
		logger.Error("read mysql-crond runtime config template failed: %s", err.Error())
		return err
	}

	f, err := os.OpenFile(
		path.Join(cst.MySQLCrondInstallPath, "runtime.yaml"),
		os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
		0644,
	)
	if err != nil {
		logger.Error("create mysql-crond runtime.yaml failed: %s", err.Error())
		return err
	}

	err = t.Execute(
		f,
		struct {
			IP        string
			BkCloudId int
			// EventName        string
			EventDataId    int
			EventDataToken string
			// MetricsName      string
			MetricsDataId    int
			MetricsDataToken string
			LogPath          string
			PidPath          string
			InstallPath      string
			BeatPath         string
			AgentAddress     string
		}{
			IP:        c.Params.Ip,
			BkCloudId: c.Params.BkCloudId,
			// EventName:        c.Params.EventName,
			EventDataId:    c.Params.EventDataId,
			EventDataToken: c.Params.EventDataToken,
			// MetricsName:      c.Params.MetricsName,
			MetricsDataId:    c.Params.MetricsDataId,
			MetricsDataToken: c.Params.MetricsDataToken,
			LogPath:          path.Join(cst.MySQLCrondInstallPath, "logs"),
			PidPath:          cst.MySQLCrondInstallPath,
			InstallPath:      cst.MySQLCrondInstallPath,
			BeatPath:         c.Params.BeatPath,
			AgentAddress:     c.Params.AgentAddress,
		},
	)
	if err != nil {
		logger.Error("execute template for mysql-crond failed: %s", err.Error())
		return err
	}
	return nil
}

// TouchJobsConfig 生成一个空的任务配置
func (c *DeployMySQLCrondComp) TouchJobsConfig() (err error) {
	jobsConfigFilePath := path.Join(cst.MySQLCrondInstallPath, "jobs-config.yaml")
	if _, err = os.Stat(jobsConfigFilePath); errors.Is(err, os.ErrNotExist) {
		jc := struct {
			Jobs    []int `yaml:"jobs"` // 实际这里不是 int, 但是这不重要, 反正是空的, 占位而已
			BkBizId int   `yaml:"bk_biz_id"`
		}{
			Jobs:    nil,
			BkBizId: c.Params.BkBizId,
		}
		content, err := yaml.Marshal(jc)
		if err != nil {
			logger.Error("marshal init jobs config file failed: %s", err.Error())
			return err
		}

		f, err := os.OpenFile(
			jobsConfigFilePath,
			os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
			0644,
		)
		if err != nil {
			logger.Error("create jobs config failed: %s", err.Error())
			return err
		}

		_, err = f.Write(content)
		if err != nil {
			logger.Error("write jobs config failed: %s", err.Error())
			return err
		}
	}
	return nil
}

// Start 启动进程
func (c *DeployMySQLCrondComp) Start() (err error) {
	chownCmd := fmt.Sprintf(`chown -R mysql %s`, cst.MySQLCrondInstallPath)
	_, err = osutil.ExecShellCommand(false, chownCmd)
	if err != nil {
		logger.Error("chown %s to mysql failed: %s", cst.MySQLCrondInstallPath, err.Error())
		return err
	}

	/*
		前台启动 mysql-crond
		目的是试试看能不能正常启动, 方便捕捉错误
	*/
	errChan := make(chan error)
	go func() {
		// 重装的时候无脑尝试关闭一次
		resp, err := http.Get("http://127.0.0.1:9999/quit")
		if err != nil {
			logger.Error("send quit request failed for forehead start", err.Error())
			errChan <- errors.Wrap(err, "send quit request failed for forehead start")
			return
		}
		defer func() {
			_ = resp.Body.Close()
		}()

		time.Sleep(15 * time.Second)

		cmd := exec.Command(
			"su", "-", "mysql", "-c",
			fmt.Sprintf(
				`%s -c %s`,
				path.Join(cst.MySQLCrondInstallPath, "mysql-crond"),
				path.Join(cst.MySQLCrondInstallPath, "runtime.yaml"),
			),
		)
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		err = cmd.Run()
		if err != nil {
			errChan <- errors.Wrap(err, stderr.String())
		}
		errChan <- nil
	}()

	started := false
LabelSelectLoop:
	for i := 1; i <= 30; i++ {
		select {
		case err := <-errChan:
			if err != nil {
				logger.Error("start mysql-crond failed: %s", err.Error())
				return err
			}
		case <-time.After(1 * time.Second):
			logger.Info("try to connect mysql-crond %d times", i)
			resp, err := http.Get("http://127.0.0.1:9999/entries")
			if err != nil {
				logger.Info("try to connect mysql-crond %d times failed: %s", i, err.Error())
				break
			}
			_ = resp.Body.Close()
			started = true
			logger.Info("try to connect mysql-crond %d times success", i)
			break LabelSelectLoop
		}
	}

	if !started {
		err := errors.Errorf("start mysql-crond failed: try to connect too many times")
		logger.Error(err.Error())
		return err
	}

	// 关闭前台启动的 mysql-crond
	resp, err := http.Get("http://127.0.0.1:9999/quit")
	if err != nil {
		logger.Error("send quit request failed", err.Error())
		return err
	}
	defer func() {
		_ = resp.Body.Close()
	}()
	logger.Info("send quit request success")

	time.Sleep(15 * time.Second)

	// 确认监听端口已经关闭
	logger.Info("check mysql-crond bind port")
	closed := false
	for i := 1; i <= 5; i++ {
		logger.Info("check mysql-crond port %d times", i)
		_, err := net.DialTimeout("tcp", "127.0.0.1:9999", 1*time.Second)
		if err != nil {
			logger.Info("port closed")
			closed = true
			break
		}
		logger.Info("port opened, try later")
		time.Sleep(2 * time.Second)
	}

	if !closed {
		err := errors.Errorf("mysql-crond quit failed, confirm port close too many times")
		logger.Error(err.Error())
		return err
	}

	// 正式后台启动 mysql-crond
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c", // mysql 写死
			fmt.Sprintf(
				`%s -c %s`,
				path.Join(cst.MySQLCrondInstallPath, "start.sh"),
				path.Join(cst.MySQLCrondInstallPath, "runtime.yaml"),
			),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("start mysql-crond failed: %s", err.Error())
		return err
	}

	// 再次检查能不能连接
	started = false
	for i := 1; i <= 10; i++ {
		logger.Info("try to connect mysql-crond %d times", i)
		resp, err := http.Get("http://127.0.0.1:9999/entries")
		if err != nil {
			logger.Info("try to connect mysql-crond %d times failed: %s", i, err.Error())
			time.Sleep(2 * time.Second)
			continue
		}
		_ = resp.Body.Close()
		started = true
		logger.Info("try to connect mysql-crond %d times success", i)
		break
	}

	if !started {
		err := errors.Errorf("start mysql-crond failed: try to connect too many times")
		logger.Error(err.Error())
		return err
	}

	logger.Info("mysql-crond started")

	return nil
}

// Example 例子
func (c *DeployMySQLCrondComp) Example() interface{} {
	return DeployMySQLCrondComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: &DeployMySQLCrondParam{
			Medium: components.Medium{
				Pkg:    "mysql-crond.tar.gz",
				PkgMd5: "12345",
			},
			Ip:        "127.0.0.1",
			BkCloudId: 0,
			// EventName:        "mysql_crond_event",
			EventDataId:    123,
			EventDataToken: "abc",
			// MetricsName:      "mysql_crond_beat",
			MetricsDataId:    456,
			MetricsDataToken: "xyz",
		},
	}
}
