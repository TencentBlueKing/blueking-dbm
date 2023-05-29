package mysql

import (
	"fmt"
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

func (c *DeployMySQLCrondComp) Stop() (err error) {
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(
				`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "stop.sh"),
			),
		}...,
	)

	err = cmd.Run()
	if err != nil {
		logger.Error("stop mysql-crond failed: %s", err.Error())
		return err
	}
	logger.Info("stop mysql-crond success")
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

	logger.Info("mysql-crond started")
	return nil
}

func (c *DeployMySQLCrondComp) CheckStart() (err error) {
	/*
	   EXIT STATUS
	          0      One or more processes matched the criteria. For pkill the process must also have been successfully signalled.
	          1      No processes matched or none of them could be signalled.
	          2      Syntax error in the command line.
	          3      Fatal error: out of memory etc.
	*/
	for i := 0; i < 10; i++ {
		time.Sleep(5 * time.Second)

		cmd := exec.Command(
			"su", "mysql", "-c", "pgrep -x 'mysql-crond'")

		err = cmd.Run()
		if err != nil {
			var exitErr *exec.ExitError
			if errors.As(err, &exitErr) {
				if exitErr.ExitCode() == 1 {
					err = errors.Errorf("%d time check: mysql-crond process not found", i+1)
					logger.Warn(err.Error())
					continue // 没找到就重试
				} else {
					err = fmt.Errorf("run %s failed, exit code: %d",
						cmd.String(), exitErr.ExitCode())
					logger.Error(err.Error())
					return err
				}
			} else {
				logger.Error("find mysql-crond process failed: %s", err.Error())
				return err
			}
		}

		return nil // 如果能走到这里, 说明正常启动了
	}

	err = errors.Errorf("mysql-crond check start failed")

	startErrFilePath := path.Join(cst.MySQLCrondInstallPath, "start-crond.err")
	_, err = os.Stat(startErrFilePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			sterr := errors.Errorf("start mysql-crond failed without start-crond.err file")
			return sterr
		} else {
			sterr := errors.Wrapf(err, "get start-crond.err stat failed")
			logger.Error(sterr.Error())
			return sterr
		}
	}

	content, err := os.ReadFile(startErrFilePath)
	if err != nil {
		logger.Error("read mysql-crond.err", err.Error())
		return err
	}
	if len(content) > 0 {
		ferr := errors.Errorf("start-crond.err content: %s", string(content))
		logger.Error(ferr.Error())
		return ferr
	} else {
		err := errors.Errorf("start mysql-crond failed with empty start-crond.err")
		logger.Error(err.Error())
		return err
	}
}

func (c *DeployMySQLCrondComp) AddKeepAlive() (err error) {
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(
				`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "add_keep_alive.sh"),
			),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("add mysql-crond keep alive crontab failed: %s", err.Error())
		return err
	}
	logger.Info("add mysql-crond keep alive crontab success")
	return nil
}

func (c *DeployMySQLCrondComp) RemoveKeepAlive() (err error) {
	cmd := exec.Command(
		"su", []string{
			"-", "mysql", "-c",
			fmt.Sprintf(
				`/bin/sh %s`,
				path.Join(cst.MySQLCrondInstallPath, "remove_keep_alive.sh"),
			),
		}...,
	)
	err = cmd.Run()
	if err != nil {
		logger.Error("remove mysql-crond keep alive crontab failed: %s", err.Error())
		return err
	}
	logger.Info("remove mysql-crond keep alive crond success")

	time.Sleep(1 * time.Minute) //确保现在在跑的周期完成
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
