package atomproxy

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/google/go-cmp/cmp"
	"github.com/pkg/errors"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

/*
 ==> Twemproxy : 1. 启动进程；2. 和集群中在使用的proxy 配置对比md5
 ==> Predixy   : 1. 启动进程；3.

 proxy 复用 走一遍proxy 的安装流程
  ===> . 在这之前需要清理掉一些已有的
*/

// ProxyReUseParams Proxy复用参数
type ProxyReUseParams struct {
	IP            string `json:"ip" validate:"required"`
	Port          int    `json:"port" validate:"required"` //  只支持1个端口
	Password      string `json:"password" validate:"required"`
	RedisPassword string `json:"redis_password" validate:"required"`
	ClusterType   string `json:"cluster_type" validate:"required"`
	ReUse         bool   `json:"reuse"`

	NutPrarms struct {
		Servers     []string               `json:"servers"`
		ConfConfigs map[string]interface{} `json:"conf_configs"`
	} `json:"twemproxy_confies" validate:"required"`
	// NutParams     *TwemproxyInstallParams
	PredixyParams struct {
		PredixyAdminPasswd string   `json:"predixyadminpasswd"`
		Servers            []string `json:"servers"`
		LoadModules        []string `json:"load_modules"` // 需要加载的模块, [redisbloom,rediscell,redisjson]
		DbConfig           struct {
			WorkerThreads        string `json:"workerthreads"`
			ClientTimeout        string `json:"clienttimeout"`
			RefreshInterval      string `json:"refreshinterval"`
			ServerFailureLimit   string `json:"serverfailurelimit"`
			ServerRetryTimeout   string `json:"serverretrytimeout"`
			KeepAlive            string `json:"keepalive"`
			ServerTimeout        string `json:"servertimeout"`
			SlowlogLogSlowerThan string `json:"slowloglogslowerthan"`
			SlowlogMaxLen        string `json:"slowlogmaxlen"`
		} `json:"dbconfig"`
	} `json:"predixy_confies" validate:"required"`
	// PredixyParams *PredixyConfParams
}

// ProxyReUse Proxy复用
type ProxyReUse struct {
	runtime *jobruntime.JobGenericRuntime
	params  ProxyReUseParams
	role    string // predixy or twemproxy
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*ProxyReUse)(nil)

// NewProxyReUse new
func NewProxyReUse() jobruntime.JobRunner {
	return &ProxyReUse{}
}

// Init prepare run env
func (job *ProxyReUse) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	x, _ := json.Marshal(job.params)
	job.runtime.Logger.Info("input params::%s", x)
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("ProxyReUse Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("ProxyReUse Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	if job.params.Port == 0 {
		err = fmt.Errorf("ProxyReUse Init port:%d==0", job.params.Port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// Name 原子任务名
func (job *ProxyReUse) Name() string {
	return "redis_proxy_reuse"
}

// Run Command Run
// 1. check ifneed
// 2. stop bk-dbmon && stop proxy
// 3. backup data-port ; install proxy
// 4. start proxy && start bk-dbmon
func (job *ProxyReUse) Run() (err error) {
	if err = job.getRole(); err != nil {
		return
	}
	if err = myredis.LocalRedisConnectTest(job.params.IP, []int{job.params.Port}, job.params.Password); err != nil {
		job.runtime.Logger.Warn("try connect 2 proxy %s:%d failed :%+v", job.params.IP, job.params.Port, err)
	}
	// 关闭 dbmon,最后再拉起
	if err = util.StopBkDbmon(); err != nil {
		return err
	}
	defer util.StartBkDbmon()

	// 当前/usr/local/twemproxy or /usr/local/predixy 指向版本不是 目标版本
	if err = job.stopProxy(); err != nil {
		return err
	}

	// 在传入需要复用的时候才执行 重新安装
	if job.params.ReUse {
		if err := job.backupProxyConfig(job.params.Port); err != nil {
			return err
		}
		// backup proxy data dir.
		if job.role == "predixy" {
			if err := job.reGeneratePredixyConfig(job.params.Port); err != nil {
				return err
			}
		} else if job.role == "twemproxy" {
			if err := job.reGenerateTwemproxyConfig(job.params.Port); err != nil {
				return err
			}
		} else {
			return fmt.Errorf("unknown proxy role :%s for cluster:%s",
				job.role, job.params.ClusterType)
		}
	}
	// 再 start proxy
	if err = job.startProxy(); err != nil {
		return err
	}
	// 连上proxy 检查版本信息，确认运行正常
	if err := job.isProxyRunningOK(); err != nil {
		return err
	}
	job.runtime.Logger.Info(fmt.Sprintf("[%s:%s:%d]proxy reuse job done ",
		job.role, job.params.IP, job.params.Port))
	return nil
}

func (job *ProxyReUse) getRole() (err error) {
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		job.role = "predixy"
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		job.role = "twemproxy"
	} else {
		err = fmt.Errorf("unknown ClusterType:%s", job.params.ClusterType)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

func (job *ProxyReUse) isProxyRunningOK() (err error) {
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		_, err = myredis.GetPredixyRunTimeVersion(job.params.IP, job.params.Port,
			job.params.Password)
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		_, err = myredis.GetTwemproxyRunTimeVersion(job.params.IP, job.params.Port)
	}
	return err
}

func (job *ProxyReUse) backupProxyConfig(port int) error {
	dataDir, exist_cnf, rename_cnf := consts.GetRedisDataDir(), "", ""
	// cd instance dir ; mv
	if job.role == "twemproxy" {
		instance_dir := fmt.Sprintf("%s/%s/%d", dataDir, twemproxyDir, port)
		exist_cnf = filepath.Join(instance_dir, fmt.Sprintf("nutcracker.%d.yml", port))
		rename_cnf = filepath.Join(instance_dir, fmt.Sprintf("nutcracker.%d.yml.%d", port, time.Now().Unix()))
	} else if job.role == "predixy" {
		instance_dir := fmt.Sprintf("%s/predixy/%d", dataDir, port)
		exist_cnf = filepath.Join(instance_dir, "predixy.conf")
		rename_cnf = filepath.Join(instance_dir, fmt.Sprintf("predixy.conf.%d", time.Now().Unix()))
	}
	job.runtime.Logger.Info("rename instance config 2 :%s", rename_cnf)
	if err := os.Rename(exist_cnf, rename_cnf); err != nil {
		if strings.Contains(err.Error(), "no such file") {
			job.runtime.Logger.Warn("maybe this is retry 4: %+v", err)
			return nil
		}
		return err
	}
	return nil
}

func (job *ProxyReUse) reGenerateTwemproxyConfig(port int) error {
	// /data/twemproxy-0.2.4/50010/nutcracker.50010.yml
	instConfigFileName := fmt.Sprintf("nutcracker.%d.yml", port)
	instConfigFilePath := filepath.Join(consts.GetRedisDataDir(), twemproxyDir, strconv.Itoa(port), instConfigFileName)

	// ti.params.ConfConfigs
	instConfig := common.NewTwemproxyConf()

	instConfig.NosqlProxy.Password = job.params.Password
	instConfig.NosqlProxy.RedisPassword = job.params.RedisPassword
	// 在Init 已经检查过了.
	newServers, _ := common.ReFormatTwemproxyConfServer(job.params.NutPrarms.Servers)
	instConfig.NosqlProxy.Servers = newServers
	instConfig.NosqlProxy.Listen = fmt.Sprintf("%s:%d", job.params.IP, job.params.Port)

	instConfig.NosqlProxy.SlowMs = 1000000 // 建议，经验值
	instConfig.NosqlProxy.Backlog = 512    // 建议，经验值
	// 固定参数
	instConfig.NosqlProxy.Redis = true              // 必须
	instConfig.NosqlProxy.Distribution = "modhash"  // 必须
	instConfig.NosqlProxy.Hash = "fnv1a_64"         // 必须
	instConfig.NosqlProxy.AutoEjectHosts = false    // 必须
	instConfig.NosqlProxy.ServerConnections = 1     // 必须，避免出现"后发先致"的问题
	instConfig.NosqlProxy.ServerFailureLimit = 3    // 建议，经验值
	instConfig.NosqlProxy.PreConnect = false        // 建议，经验值
	instConfig.NosqlProxy.ServerRetryTimeout = 2000 // 建议，经验值
	if v, e := job.params.NutPrarms.ConfConfigs["hash_tag"]; e {
		instConfig.NosqlProxy.HashTag, _ = v.(string)
	}

	exists, err := fileIsExists(instConfigFilePath)
	// 存在未知的错误
	if err != nil {
		return err
	}

	if exists {
		currInstConfig := common.NewTwemproxyConf()
		if err = currInstConfig.Load(instConfigFilePath); err != nil {
			return errors.Errorf("文件已存在，且读取失败, file:%s", instConfigFilePath)
		}
		if !cmp.Equal(currInstConfig, instConfig) {
			return errors.Errorf("文件已存在，内容不同, file:%s", instConfigFilePath)
		}
		job.runtime.Logger.Info("文件已存在，但内容相同. file:%s", instConfigFilePath)
		return nil
	}

	if err = instConfig.Save(instConfigFilePath, defaultFileMode); err != nil {
		return errors.Errorf("写入文件失败, file:%s, err:%v", instConfigFilePath, err)
	}
	return nil
}

func (job *ProxyReUse) reGeneratePredixyConfig(port int) error {

	job.runtime.Logger.Info("start to make config file content")
	// 配置文件
	conf := common.PredixConf
	// 修改配置文件
	instance_base := fmt.Sprintf("%s/predixy/%d", consts.GetRedisDataDir(), job.params.Port)
	config_path := fmt.Sprintf("%s/predixy.conf", instance_base)
	log := fmt.Sprintf("%s/logs/log", instance_base)

	bind := fmt.Sprintf("%s:%s", job.params.IP, strconv.Itoa(job.params.Port))
	var servers string
	for _, v := range job.params.PredixyParams.Servers {
		servers += fmt.Sprintf("    + %s\n", v)
	}
	slowloglogslowerthan := "100000"
	if job.params.PredixyParams.DbConfig.SlowlogLogSlowerThan != "" {
		slowloglogslowerthan = job.params.PredixyParams.DbConfig.SlowlogLogSlowerThan
	}
	slowlogmaxlen := "1024"
	if job.params.PredixyParams.DbConfig.SlowlogMaxLen != "" {
		slowlogmaxlen = job.params.PredixyParams.DbConfig.SlowlogMaxLen
	}
	conf = strings.Replace(conf, "{{ip:port}}", bind, -1)
	conf = strings.Replace(conf, "{{predixy_password}}", job.params.Password, -1)
	conf = strings.Replace(conf, "{{log_path}}", log, -1)
	conf = strings.Replace(conf, "{{redis_password}}", job.params.RedisPassword, -1)
	conf = strings.Replace(conf, "{{server:port}}", servers, -1)
	// 指定 worker_threads 为cpu核数
	conf = strings.Replace(conf, "{{worker_threads}}", strconv.Itoa(runtime.NumCPU()), -1)
	conf = strings.Replace(conf, "{{server_timeout}}", job.params.PredixyParams.DbConfig.ServerTimeout, -1)
	conf = strings.Replace(conf, "{{keep_alive}}", job.params.PredixyParams.DbConfig.KeepAlive, -1)
	conf = strings.Replace(conf, "{{client_timeout}}", job.params.PredixyParams.DbConfig.ClientTimeout, -1)
	conf = strings.Replace(conf, "{{slowlog_Log_slower_than}}", slowloglogslowerthan, -1)
	conf = strings.Replace(conf, "{{slowlog_max_len}}", slowlogmaxlen, -1)
	conf = strings.Replace(conf, "{{predixy_admin_password}}", job.params.PredixyParams.PredixyAdminPasswd, -1)
	conf = strings.Replace(conf, "{{refresh_interval}}",
		job.params.PredixyParams.DbConfig.RefreshInterval, -1)
	conf = strings.Replace(conf, "{{server_failure_limit}}",
		job.params.PredixyParams.DbConfig.ServerFailureLimit, -1)
	conf = strings.Replace(conf, "{{server_retry_timeout}}",
		job.params.PredixyParams.DbConfig.ServerRetryTimeout, -1)
	// 配置文件加入module commands
	if len(job.params.PredixyParams.LoadModules) != 0 {
		conf = conf + consts.GetPredixyModuleCommands(job.params.PredixyParams.LoadModules)
	}

	file, err := os.OpenFile(config_path, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("%s:create configer file fail, error:%s", job.Name(), err))
		return errors.New(fmt.Sprintf("%s:create configer file fail, error:%s", job.Name(), err))
	}
	defer file.Close()
	if _, err := file.WriteString(conf); err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("%s:configer file write content fail, error:%s", job.Name(), err))
		return errors.New(fmt.Sprintf("%s:configer file write content  fail, error:%s", job.Name(), err))
	}
	job.runtime.Logger.Info("make config file content successfully")
	return nil
}

// stopProxy 关闭 proxy
func (job *ProxyReUse) stopProxy() (err error) {
	stopScript := ""
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		stopScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "stop_predixy.sh")
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		stopScript = filepath.Join(consts.UsrLocal, "twemproxy", "bin", "stop_nutcracker.sh")
	}
	_, err = os.Stat(stopScript)
	if err != nil && os.IsNotExist(err) {
		job.runtime.Logger.Info("%s not exist", stopScript)
		return nil
	}
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s %d\"",
		consts.MysqlAaccount, stopScript, job.params.Port))

	maxRetryTimes := 5
	inUse := false
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		util.RunLocalCmd("su",
			[]string{consts.MysqlAaccount, "-c", stopScript + " " + strconv.Itoa(job.params.Port)},
			"", nil, 10*time.Minute)
		inUse, err = util.CheckPortIsInUse(job.params.IP, strconv.Itoa(job.params.Port))
		if err != nil {
			job.runtime.Logger.Error(fmt.Sprintf("check %s:%d inUse failed,err:%v", job.params.IP, job.params.Port, err))
			return err
		}
		if !inUse {
			break
		}
		time.Sleep(2 * time.Second)
	}
	if inUse {
		err = fmt.Errorf("stop %s (%s:%d) failed,port:%d still using",
			job.role, job.params.IP, job.params.Port, job.params.Port)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info("stop %s (%s:%d) success",
		job.role, job.params.IP, job.params.Port)
	return nil
}

// startProxy 拉起 proxy
func (job *ProxyReUse) startProxy() (err error) {
	startScript := ""
	port := job.params.Port
	if consts.IsPredixyClusterType(job.params.ClusterType) {
		startScript = filepath.Join(consts.UsrLocal, "predixy", "bin", "start_predixy.sh")
	} else if consts.IsTwemproxyClusterType(job.params.ClusterType) {
		startScript = filepath.Join(consts.UsrLocal, "twemproxy", "bin", "start_nutcracker.sh")
	}
	job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\" 2>/dev/null",
		consts.MysqlAaccount, startScript+" "+strconv.Itoa(port)))
	_, err = util.RunLocalCmd("su",
		[]string{consts.MysqlAaccount, "-c", startScript + " " + strconv.Itoa(port) + " 2>/dev/null"},
		"", nil, 10*time.Minute)
	if err != nil {
		return err
	}
	addr := fmt.Sprintf("%s:%d", job.params.IP, port)
	cli, err := myredis.NewRedisClientWithTimeout(addr, job.params.Password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	defer cli.Close()
	job.runtime.Logger.Info("start proxy (%s:%d) success", job.params.IP, port)
	return nil
}

// Retry times
func (job *ProxyReUse) Retry() uint {
	return 2
}

// Rollback rollback
func (job *ProxyReUse) Rollback() error {
	return nil
}
