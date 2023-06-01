package influxdb

import (
	"fmt"
	"io/ioutil"
	"os"
	"os/user"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InstallInfluxdbComp TODO
type InstallInfluxdbComp struct {
	GeneralParam *components.GeneralParam
	Params       *InstallInfluxdbParams
	KafkaConfig
	RollBackContext rollback.RollBackObjects
}

// InstallInfluxdbParams TODO
type InstallInfluxdbParams struct {
	Version   string `json:"version" ` // 版本号eg: 7.10.2
	Port      int    `json:"port" `    // 连接端口
	Host      string `json:"host" `
	GroupName string `json:"group_name" ` // 组名
	GroupId   int    `json:"group_id" `   // 连接端口
	Username  string `json:"username" `
	Password  string `json:"password" `
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int
type socket = string

// KafkaConfig 目录定义等
type KafkaConfig struct {
	InstallDir     string `json:"install_dir"`     // /data
	InfluxdbEnvDir string `json:"influxdbenv_dir"` //  /data/influxdbenv
}

// RenderConfig 需要替换的配置值 Todo
type RenderConfig struct {
	ClusterName          string
	NodeName             string
	HttpPort             int
	CharacterSetServer   string
	InnodbBufferPoolSize string
	Logdir               string
	ServerId             uint64
}

// InitDefaultParam TODO
func (i *InstallInfluxdbComp) InitDefaultParam() (err error) {
	logger.Info("start InitDefaultParam")
	// var mountpoint string
	i.InstallDir = cst.DefaultPkgDir
	i.InfluxdbEnvDir = cst.DefaultInfluxdbEnv

	return nil
}

// InitInfluxdbNode TODO
/*
创建实例相关的数据，日志目录以及修改权限
*/
func (i *InstallInfluxdbComp) InitInfluxdbNode() (err error) {

	execUser := cst.DefaultInfluxdbExecUser
	logger.Info("检查用户[%s]是否存在", execUser)
	if _, err := user.Lookup(execUser); err != nil {
		extraCmd := `groupadd influxdb && useradd influxdb -g influxdb -s /bin/bash -d /home/influxdb -m`
		if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("创建系统用户[%s]失败,%v", "influxdb", err.Error())
			return err
		}
		logger.Info("用户[%s]创建成功", execUser)
	} else {
		logger.Info("用户[%s]存在, 跳过创建", execUser)
	}

	// mkdir
	extraCmd := fmt.Sprintf("rm -rf %s", i.InfluxdbEnvDir)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}
	extraCmd = fmt.Sprintf("mkdir -p %s ; chown -R influxdb:influxdb %s", i.InfluxdbEnvDir, "/data/influxdb*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	scripts := []byte(`
echo "
* - nofile 200000
* soft nofile 200000
* hard nofile 200000
" >> /etc/security/limits.conf
echo "
vm.overcommit_memory=1
vm.swappiness=1
net.ipv4.ip_local_port_range=25000 50000
net.ipv4.tcp_tw_reuse=1
net.ipv4.tcp_tw_recycle=1
" >> /etc/sysctl.conf`)

	scriptFile := "/data/influxdbenv/init.sh"
	if err = ioutil.WriteFile(scriptFile, scripts, 0644); err != nil {
		logger.Error("write %s failed, %v", scriptFile, err)
	}

	extraCmd = fmt.Sprintf("bash %s", scriptFile)
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("修改系统参数失败:%s", err.Error())
		return err
	}

	return nil
}

// DecompressInfluxdbPkg TODO
/**
 * @description:  校验、解压kafka安装包
 * @return {*}
 */
func (i *InstallInfluxdbComp) DecompressInfluxdbPkg() (err error) {

	pkgAbPath := "influxdbpack-" + i.Params.Version + ".tar.gz"
	extraCmd := fmt.Sprintf("cp %s %s", i.InstallDir+"/"+pkgAbPath, i.InfluxdbEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	if err = os.Chdir(i.InfluxdbEnvDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InfluxdbEnvDir, err)
	}
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s", pkgAbPath)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}

	logger.Info("influxdb binary directory: %s", i.InfluxdbEnvDir)
	if _, err := os.Stat(i.InfluxdbEnvDir); err != nil {
		logger.Error("%s check failed, %v", i.InfluxdbEnvDir, err)
		return err
	}
	logger.Info("decompress influxdb pkg successfully")
	return nil
}

// InstallSupervisor TODO
/**
 * @description:  安装supervisor
 * @return {*}
 */
func (i *InstallInfluxdbComp) InstallSupervisor() (err error) {
	// Todo: check supervisor exist
	// supervisor

	if !util.FileExists(cst.DefaultInfluxdbSupervisorConf) {
		logger.Error("supervisor not exist, %v", err)
		return err

	}

	extraCmd := fmt.Sprintf("rm -rf %s", i.InfluxdbEnvDir+"/"+"python")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InfluxdbEnvDir+"/"+"pypy-5.9.0", i.InfluxdbEnvDir+"/"+"python")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf %s", "/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InfluxdbEnvDir+"/"+"supervisor/conf/supervisord.conf",
		"/etc/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf %s", "/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InfluxdbEnvDir+"/"+"supervisor/bin/supervisorctl",
		"/usr/local/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm -rf %s", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InfluxdbEnvDir+"/"+"python/bin/supervisord", "/usr/local/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/influxdbenv/g' %s", i.InfluxdbEnvDir+"/supervisor/check_supervisord.sh")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/influxdbenv/g' %s", i.InfluxdbEnvDir+"/supervisor/conf/supervisord.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/influxdbenv/g' %s", i.InfluxdbEnvDir+"/supervisor/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/influxdbenv/g' %s", i.InfluxdbEnvDir+"/pypy-5.9.0/bin/supervisord")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("sed -i 's/esenv/influxdbenv/g' %s", i.InfluxdbEnvDir+"/python/bin/supervisorctl")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("rm %s ", i.InfluxdbEnvDir+"/supervisor/conf/elasticsearch.ini")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R influxdb:influxdb %s ", i.InfluxdbEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = "ps -ef | grep supervisord | grep -v grep | awk {'print \"kill -9 \" $2'} | sh"
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	// crontab
	extraCmd = `crontab  -l -u influxdb >/home/influxdb/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
	}

	extraCmd = `cp /home/influxdb/crontab.bak /home/influxdb/crontab.tmp`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `sed -i '/check_supervisord.sh/d' /home/influxdb/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd =
		`echo '*/1 * * * *  /data/influxdbenv/supervisor/check_supervisord.sh >> /data/influxdbenv/supervisor/check_supervisord.err 2>&1' >>/home/influxdb/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = `crontab -u influxdb /home/influxdb/crontab.bak`
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	startCmd := `su - influxdb -c "/usr/local/bin/supervisord -c /data/influxdbenv/supervisor/conf/supervisord.conf"`

	logger.Info(fmt.Sprintf("execute supervisor [%s] begin", startCmd))
	pid, err := osutil.RunInBG(false, startCmd)
	logger.Info(fmt.Sprintf("execute supervisor [%s] end, pid: %d", startCmd, pid))
	if err != nil {
		return err
	}
	return nil
}

// InstallInfluxdb TODO
/**
 * @description: 安装broker
 * @return {*}
 */
func (i *InstallInfluxdbComp) InstallInfluxdb() (err error) {
	var (
		version         string = i.Params.Version
		port            int    = i.Params.Port
		influxdbBaseDir string = fmt.Sprintf("%s/influxdb-%s-1", cst.DefaultInfluxdbEnv, version)
	)

	influxdbLink := fmt.Sprintf("%s/influxdb", cst.DefaultInfluxdbEnv)
	extraCmd := fmt.Sprintf("rm -rf %s", influxdbLink)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("ln -s %s %s ", influxdbBaseDir, influxdbLink)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("copy basedir failed, %s, %s", output, err.Error())
		return err
	}

	// mkdir
	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultInfluxdbLogDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("rm -rf %s", cst.DefaultInfluxdbDataDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	extraCmd = fmt.Sprintf("mkdir -p %s ; mkdir -p %s ; chown -R influxdb:influxdb %s", cst.DefaultInfluxdbDataDir,
		cst.DefaultInfluxdbLogDir, "/data/influxdb*")
	if _, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("初始化实例目录失败:%s", err.Error())
		return err
	}

	logger.Info("开始渲染influxdb.conf")
	extraCmd = fmt.Sprintf(`echo 'reporting-disabled = true
[meta]
  dir = "%s/meta"

[data]
  dir = "%s/data"
  wal-dir = "%s/wal"
  index-version = "tsi1"
  cache-snapshot-memory-size = "25m"
  max-series-per-database = 0
  max-values-per-tag = 1000000
  query-log-enabled = true
  cache-max-memory-size = "8g"
  flux-enabled = true

[coordinator]
  query-timeout = "60s"
  log-queries-after = "10s"

[http]
  bind-address = ":%d"
  auth-enabled = true
  max-row-limit = 50000
  log-enabled = false
  write-tracing = false
  access-log-path = "%s/var/log/access.log"

[ifql]

[continuous_queries]

[logging]' > %s`, cst.DefaultInfluxdbDataDir, cst.DefaultInfluxdbDataDir, cst.DefaultInfluxdbDataDir, port, influxdbLink, influxdbLink+"/etc/influxdb/influxdb.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("生成influxdb.ini文件")
	influxdbini := esutil.GenInfluxdbini()
	influxdbiniFile := fmt.Sprintf("%s/influxdb.ini", cst.DefaultInfluxdbSupervisorConf)
	if err = ioutil.WriteFile(influxdbiniFile, influxdbini, 0); err != nil {
		logger.Error("write %s failed, %v", influxdbiniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/influxdb.ini ", cst.DefaultInfluxdbSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R influxdb:influxdb %s ", i.InfluxdbEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}

	extraCmd = fmt.Sprintf("sleep 60")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}

// InitUser TODO
func (i *InstallInfluxdbComp) InitUser() (err error) {

	var (
		username        string = i.Params.Username
		password        string = i.Params.Password
		port            int    = i.Params.Port
		influxdbBaseDir string = fmt.Sprintf("%s/influxdb", cst.DefaultInfluxdbEnv)
	)
	extraCmd := fmt.Sprintf(
		`%s/usr/bin/influx -host localhost -port %d -execute "create user '%s' with password '%s' with all privileges"`,
		influxdbBaseDir, port, username, password)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("copy basedir failed, %s, %s", output, err.Error())
		return err
	}

	return nil
}

// InstallTelegraf TODO
func (i *InstallInfluxdbComp) InstallTelegraf() (err error) {

	var (
		host      string = i.Params.Host
		port      int    = i.Params.Port
		groupName string = i.Params.GroupName
		groupId   int    = i.Params.GroupId
	)

	logger.Info("开始渲染telegraf.conf")
	extraCmd := fmt.Sprintf(`echo '[global_tags]
    cluster = "%s"
    dbrole = "influxdb"
    dbgroup = "%s"
    dbgroup_id = "%d"
    influx_host = "%s"
    influx_port = "%d"

# Configuration for telegraf agent
[agent]
    interval = "30s"
    debug = true
    hostname = "%s"
    round_interval = true
    flush_interval = "10s"
    flush_jitter = "0s"
    collection_jitter = "0s"
    metric_batch_size = 1000
    metric_buffer_limit = 500000
    quiet = false
    logfile = ""
    omit_hostname = false

###############################################################################
#                                  OUTPUTS                                    #
###############################################################################

[[outputs.prometheus_client]]
    listen = ":9274"
    path = "/metrics"
    expiration_interval = "340s"
    collectors_exclude = ["gocollector", "process"]

###############################################################################
#                                  INPUTS                                     #
###############################################################################
### os
[[inputs.mem]]
[[inputs.cpu]]
    percpu = false
    totalcpu = true
[[inputs.diskio]]
[[inputs.disk]]

#### influxdb
[[inputs.influxdb]]
  urls = [
    "http://localhost:%d/debug/vars"
  ]
  timeout = "30s"
  interval = "1m"
  namedrop = ["influxdb_memstats*", "influxdb_runtime*"]

#### procstat
[[inputs.procstat]]
  exe = "influxd"
  pid_finder = "pgrep"
  pid_tag = true
  process_name = "influxd"
  interval = "30s"

#### http_response
[[inputs.http_response]]
   address = "http://%s:%d/ping"
   response_timeout = "2s"
   method = "GET"' > %s`, groupName, groupName, groupId, host, port, host, port, host, port, cst.DefaultInfluxdbEnv+"/telegraf/etc/telegraf/telegraf.conf")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("生成telegraf.ini文件")
	influxdbini := esutil.GenTelegrafini()
	influxdbiniFile := fmt.Sprintf("%s/telegraf.ini", cst.DefaultInfluxdbSupervisorConf)
	if err = ioutil.WriteFile(influxdbiniFile, influxdbini, 0); err != nil {
		logger.Error("write %s failed, %v", influxdbiniFile, err)
	}

	extraCmd = fmt.Sprintf("chmod 777 %s/telegraf.ini ", cst.DefaultInfluxdbSupervisorConf)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	extraCmd = fmt.Sprintf("chown -R influxdb:influxdb %s ", i.InfluxdbEnvDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	if err = esutil.SupervisorctlUpdate(); err != nil {
		logger.Error("supervisort update failed %v", err)
	}

	return nil
}
