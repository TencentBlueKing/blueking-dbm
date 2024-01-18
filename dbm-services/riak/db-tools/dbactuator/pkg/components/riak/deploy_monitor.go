// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

import (
	"bytes"
	"dbm-services/common/go-pubpkg/logger"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/riak/db-tools/dbactuator/pkg/components"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path"
	"text/template"
	"time"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v2"
)

// DeployMonitorComp TODO
type DeployMonitorComp struct {
	Params                  *DeployMonitorParam `json:"extend"`
	DeployMonitorRunTimeCtx `json:"-"`
}

// DeployMonitorParam TODO
type DeployMonitorParam struct {
	CrondPkg      components.Medium `json:"crond_pkg" validate:"required"`
	MonitorPkg    components.Medium `json:"monitor_pkg" validate:"required"`
	CrondConfig   CrondConfigYaml   `json:"crond_config" validate:"required"`
	MonitorConfig MonitorConfigYaml `json:"monitor_config" validate:"required"`
	MonitorItems  []MonitorItem     `json:"monitor_items" validate:"required"`
	JobsConfig    JobsConfig        `json:"jobs_config" validate:"required"`
}

type JobsConfig struct {
	Jobs    []Job `json:"jobs" yaml:"jobs"`
	BkBizId int   `json:"bk_biz_id" yaml:"bk_biz_id" validate:"required"`
}

type Job struct {
	Name     string   `json:"name" yaml:"name"`
	Enable   bool     `json:"enable" yaml:"enable"`
	Command  string   `json:"command" yaml:"command"`
	Args     []string `json:"args" yaml:"args"`
	Schedule string   `json:"schedule" yaml:"schedule"`
	Creator  string   `json:"creator" yaml:"creator"`
	WorkDir  string   `json:"work_dir" yaml:"work_dir"`
}

// DeployMonitorRunTimeCtx 运行时上下文
type DeployMonitorRunTimeCtx struct {
	LocalIp string
}

type CrondConfigYaml struct {
	IP               string `json:"ip" validate:"required,ipv4"`
	BkCloudId        *int   `json:"bk_cloud_id" validate:"required,gte=0"`
	EventDataId      int    `json:"event_data_id" validate:"required"`
	EventDataToken   string `json:"event_data_token" validate:"required"`
	MetricsDataId    int    `json:"metrics_data_id" validate:"required"`
	MetricsDataToken string `json:"metrics_data_token" validate:"required"`
	LogPath          string `json:"log_file_dir"`
	PidPath          string `json:"pid_path"`
	InstallPath      string `json:"install_path"`
	BeatPath         string `json:"beat_path" validate:"required"`
	AgentAddress     string `json:"agent_address" validate:"required"`
}

type MonitorConfigYaml struct {
	BkBizId         int           `json:"bk_biz_id" validate:"required"`
	IP              string        `json:"ip" validate:"required,ipv4"`
	Port            int           `json:"port" validate:"required,gt=1024,lte=65535"`
	BkInstanceId    int           `json:"bk_instance_id" validate:"required,gt=0"`
	ImmuteDomain    string        `json:"immute_domain" validate:"required"`
	MachineType     string        `json:"machine_type" validate:"required"`
	BkCloudId       *int          `json:"bk_cloud_id" validate:"required,gte=0"`
	LogPath         string        `json:"log_path"`
	ItemsConfigPath string        `json:"items_config_file" validate:"required"`
	InteractTimeout time.Duration `json:"interact_timeout" validate:"required"`
}

type MonitorItem struct {
	Name        string   `json:"name" yaml:"name"`
	Enable      *bool    `json:"enable" yaml:"enable"`
	Schedule    *string  `json:"schedule" yaml:"schedule"`
	MachineType []string `json:"machine_type" yaml:"machine_type"`
}

// DeployMonitor 启动监控
func (i *DeployMonitorComp) DeployMonitor() error {
	// riak-monitor启动指令存储到jobs-config.yaml，jobs-config.yaml作为mysql-crond的runtime.yaml中的jobs_config
	// 启动mysql-crond时，会完成riak-monitor监控项注册。mysql-crond定时执行riak-monitor的指令，实现监控。

	// 前台执行mysql-crond，方便获取报错
	errChan := make(chan error)
	var dryRunErr error
	go func() {
		dryRunCmd := fmt.Sprintf("%s -c %s", path.Join(cst.CrondPath, "mysql-crond"),
			path.Join(cst.CrondPath, "runtime.yaml"))
		cmd := exec.Command("bash", "-c", dryRunCmd)
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		err := cmd.Run()
		if err != nil {
			errChan <- errors.Wrap(err, stderr.String())
			return
		}
		errChan <- nil
		return
	}()
	select {
	case dryRunErr = <-errChan:
		if dryRunErr != nil {
			dryRunErr = fmt.Errorf("crond dry-run error: %s", dryRunErr.Error())
			logger.Error(dryRunErr.Error())
			return dryRunErr
		}
	case <-time.After(time.Second * 10):
		// crond运行正常不会自动退出，10秒后没有报错，进一步检查是否启动正常
		logger.Info("crond dry-run running 10s without error")
	}

	// 检查crond是否启动
	err := GetCrondEntries()
	if err != nil {
		logger.Error("crond dry-run check error: %s", err.Error())
		return err
	}

	// 退出前台mysql-crond
	err = QuitCrond()
	if err != nil {
		logger.Error("quit crond dry-run error: %s", err.Error())
		return err
	}
	// 后台执行mysql-crond
	nohup := fmt.Sprintf("%s -c %s", path.Join(cst.CrondPath, "start.sh"),
		path.Join(cst.CrondPath, "runtime.yaml"))
	logger.Info("start crond cmd: %s", nohup)
	cmd := exec.Command("bash", "-c", nohup)
	err = cmd.Run()
	if err != nil {
		logger.Error("execute crond failed: %s", err.Error())
		return err
	}
	time.Sleep(10 * time.Second)
	// 检查crond是否启动
	err = GetCrondEntries()
	if err != nil {
		logger.Error("crond check error: %s", err.Error())
		return err
	}
	logger.Info("crond started")
	return nil
}

// DeployBinary 部署二进制
func (i *DeployMonitorComp) DeployBinary() (err error) {
	// 解压crond介质
	err = Decompress(i.Params.CrondPkg.GetAbsolutePath(), cst.CrondPath)
	if err != nil {
		logger.Error("decompress: %s to %s failed: %s", i.Params.CrondPkg.GetAbsolutePath(),
			cst.CrondPath, err.Error())
		return err
	}
	// 解压监控的介质
	err = Decompress(i.Params.MonitorPkg.GetAbsolutePath(), cst.RiakMonitorPath)
	if err != nil {
		logger.Error("decompress: %s to %s failed: %s", i.Params.MonitorPkg.GetAbsolutePath(),
			cst.RiakMonitorPath, err.Error())
		return err
	}
	return nil
}

// GenerateCrondConfigYaml 生成crond的runtime.yaml文件
func (i *DeployMonitorComp) GenerateCrondConfigYaml() (err error) {
	i.Params.CrondConfig.LogPath = path.Join(cst.CrondPath, i.Params.CrondConfig.LogPath)
	i.Params.CrondConfig.PidPath = cst.CrondPath
	i.Params.CrondConfig.InstallPath = cst.CrondPath
	err = UseTemplate(cst.CrondPath, "mysql-crond.conf.go.tpl", "runtime.yaml", i.Params.CrondConfig)
	if err != nil {
		logger.Error("generate crond runtime.yaml error: %s", err.Error())
		return err
	}
	// todo mysql-crond 模版中jobs_user不是固定值
	cmd := fmt.Sprintf(`sed -i "s/jobs_user: mysql/jobs_user: root/g" %s`, path.Join(cst.CrondPath, "runtime.yaml"))
	_, err = osutil.ExecShellCommand(false, cmd)
	if err != nil {
		logger.Error("execute %s error: %s", cmd, err.Error())
		return err
	}
	return nil
}

// GenerateMonitorConfigYaml 生成runtime.yaml文件
func (i *DeployMonitorComp) GenerateMonitorConfigYaml() (err error) {
	i.Params.MonitorConfig.LogPath = path.Join(cst.RiakMonitorPath, i.Params.MonitorConfig.LogPath)
	i.Params.MonitorConfig.ItemsConfigPath = path.Join(cst.RiakMonitorPath, i.Params.MonitorConfig.ItemsConfigPath)
	err = UseTemplate(cst.RiakMonitorPath, "config.yaml.go.tpl", "runtime.yaml", i.Params.MonitorConfig)
	if err != nil {
		logger.Error("generate monitor runtime.yaml error: %s", err.Error())
		return err
	}
	return nil
}

// GenerateJobsConfigYaml 生成jobs-config.yaml文件
func (i *DeployMonitorComp) GenerateJobsConfigYaml() (err error) {
	err = CreateYaml(cst.CrondPath, "jobs-config.yaml", i.Params.JobsConfig)
	if err != nil {
		logger.Error("create items-config.yaml file failed: %s", err.Error())
		return err
	}
	return nil
}

// GenerateItemsConfigYaml 生成items-config.yaml文件
func (i *DeployMonitorComp) GenerateItemsConfigYaml() (err error) {
	err = CreateYaml(cst.RiakMonitorPath, "items-config.yaml", i.Params.MonitorItems)
	if err != nil {
		logger.Error("create items-config.yaml file failed: %s", err.Error())
		return err
	}
	return nil
}

// Decompress 解压文件到目标路径
func Decompress(source, target string) error {
	err := os.MkdirAll(target, 0755)
	if err != nil {
		logger.Error("mkdir %s failed: %s", target, err.Error())
		return err
	}
	decompressCmd := fmt.Sprintf(
		`tar zxf %s -C %s`,
		source, target,
	)
	_, err = osutil.ExecShellCommand(false, decompressCmd)
	if err != nil {
		logger.Error("decompress mysql-crond pkg failed: %s", err.Error())
		return err
	}
	return nil
}

// UseTemplate 使用模版生成yaml文件
func UseTemplate(vpath, tpl, target string, data interface{}) error {
	t, err := template.ParseFiles(path.Join(vpath, tpl))
	if err != nil {
		logger.Error("read config template failed: %s", err.Error())
		return err
	}

	f, err := os.OpenFile(
		path.Join(vpath, target),
		os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
		0644,
	)
	if err != nil {
		logger.Error("create yaml failed: %s", err.Error())
		return err
	}

	err = t.Execute(f, data)
	if err != nil {
		logger.Error("execute template failed: %s", err.Error())
		return err
	}
	return nil
}

// CreateYaml 根据结构体生成yaml文件
func CreateYaml(vpath, target string, data interface{}) error {
	content, err := yaml.Marshal(data)
	if err != nil {
		logger.Error("marshal data failed: %s", err.Error())
		return err
	}
	f, err := os.OpenFile(path.Join(vpath, target),
		os.O_CREATE|os.O_TRUNC|os.O_RDWR, 0755)
	if err != nil {
		logger.Error("create file failed: %s", err.Error())
		return err
	}
	_, err = f.Write(append(content, []byte("\n")...))
	if err != nil {
		logger.Error("write file failed: %s", err.Error())
		return err
	}
	return nil
}

func GetCrondEntries() error {
	url := fmt.Sprintf("http://127.0.0.1:%d/entries", cst.CrondListenPort)
	resp, err := http.Get(url)
	defer resp.Body.Close()
	if err != nil {
		err = fmt.Errorf("connect crond failed: %s", err.Error())
		logger.Error(err.Error())
		return err
	}
	if resp.StatusCode != 200 {
		err = fmt.Errorf("connect crond response status code is: %d not 200 ", resp.StatusCode)
		logger.Error(err.Error())
		return err
	}
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		err = fmt.Errorf("get crond response failed: %s", err.Error())
		logger.Info(err.Error())
		return err
	}
	logger.Info("monitor entries register in crond:\n%s", string(body))
	return nil
}

func QuitCrond() error {
	// 关闭启动的 mysql-crond
	manager := ma.NewManager("http://127.0.0.1:9999")
	err := manager.Quit()
	if err != nil {
		logger.Error("quit crond failed: %s", err.Error())
	}
	logger.Info("quit crond success")
	return nil
}
