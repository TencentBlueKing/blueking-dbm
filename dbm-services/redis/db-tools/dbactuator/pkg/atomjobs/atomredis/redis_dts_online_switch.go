package atomredis

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisDtsOnlineSwitchParams 在线切换参数
type RedisDtsOnlineSwitchParams struct {
	DstProxyPkg           common.MediaPkg `json:"dst_proxy_pkg" validate:"required"`
	DtsBillID             int64           `json:"dts_bill_id" validate:"required"`
	SrcProxyIP            string          `json:"src_proxy_ip" validate:"required"`
	SrcProxyPort          int             `json:"src_proxy_port" validate:"required"`
	SrcProxyPassword      string          `json:"src_proxy_password" validate:"required"`
	SrcClusterType        string          `json:"src_cluster_type" validate:"required"`
	SrcClusterName        string          `json:"src_cluster_name" validate:"required"`
	DstProxyIP            string          `json:"dst_proxy_ip" validate:"required"`
	DstProxyPort          int             `json:"dst_proxy_port" validate:"required"`
	DstProxyPassword      string          `json:"dst_proxy_password" validate:"required"`
	DstClusterType        string          `json:"dst_cluster_type" validate:"required"`
	DstRedisIP            string          `json:"dst_redis_ip" validate:"required"`
	DstRedisPort          int             `json:"dst_redis_port" validate:"required"`
	DstClusterName        string          `json:"dst_cluster_name" validate:"required"`
	DstProxyConfigContent string          `json:"dst_proxy_config_content" validate:"required"`
}

// RedisDtsOnlineSwitch dts 在线切换
type RedisDtsOnlineSwitch struct {
	params                RedisDtsOnlineSwitchParams
	runtime               *jobruntime.JobGenericRuntime
	srcProxyConfigSaveDir string
	srcProxyConfigFile    string
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisDtsOnlineSwitch)(nil)

// NewRedisDtsOnlineSwitch new
func NewRedisDtsOnlineSwitch() jobruntime.JobRunner {
	return &RedisDtsOnlineSwitch{}
}

// Init 初始化
func (job *RedisDtsOnlineSwitch) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}
	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("%s Init params validate failed,err:%v,params:%+v",
				job.Name(), err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("%s Init params validate failed,err:%v,params:%+v", job.Name(), err, job.params)
			return err
		}
	}
	return nil
}

// Name 原子任务名
func (job *RedisDtsOnlineSwitch) Name() string {
	return "redis_dts_online_switch"
}

// Run 执行
func (job *RedisDtsOnlineSwitch) Run() (err error) {
	if !consts.IsTwemproxyClusterType(job.params.SrcClusterType) &&
		!consts.IsPredixyClusterType(job.params.SrcClusterType) {
		err = fmt.Errorf("src cluster type %s is not supported", job.params.SrcClusterType)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	if !consts.IsTwemproxyClusterType(job.params.DstClusterType) &&
		!consts.IsPredixyClusterType(job.params.DstClusterType) {
		err = fmt.Errorf("dst cluster type %s is not supported", job.params.DstClusterType)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	var sameType bool = false
	if consts.IsTwemproxyClusterType(job.params.SrcClusterType) &&
		consts.IsTwemproxyClusterType(job.params.DstClusterType) {
		sameType = true
	}
	if consts.IsPredixyClusterType(job.params.SrcClusterType) &&
		consts.IsPredixyClusterType(job.params.DstClusterType) {
		sameType = true
	}
	err = job.IsSrcProxyConnected()
	if err != nil {
		return err
	}
	err = job.IsSrcProxyConfigOK()
	if err != nil {
		return err
	}
	if sameType {
		err = job.BackupSrcProxyConfFile()
		if err != nil {
			return err
		}
		err = job.NewProxyConfigFileForSameType()
		if err != nil {
			return err
		}
		err = job.RestartProxyAndCheckBackends()
		if err != nil {
			return err
		}
		err = job.RestartDbMon()
		if err != nil {
			return err
		}
		return nil
	}
	err = job.UntarDstProxyMedia()
	if err != nil {
		return err
	}
	err = job.NewProxyConfigFileForDiffType()
	if err != nil {
		return err
	}
	err = job.RestartProxyAndCheckBackends()
	if err != nil {
		return err
	}
	err = job.RestartDbMon()
	if err != nil {
		return err
	}
	return nil
}

// Retry times
func (job *RedisDtsOnlineSwitch) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisDtsOnlineSwitch) Rollback() error {
	return nil
}

func (job *RedisDtsOnlineSwitch) getSrcProxyAddr() string {
	return fmt.Sprintf("%s:%d", job.params.SrcProxyIP, job.params.SrcProxyPort)
}

func (job *RedisDtsOnlineSwitch) getDstProxyAddr() string {
	return fmt.Sprintf("%s:%d", job.params.DstProxyIP, job.params.DstProxyPort)
}

func (job *RedisDtsOnlineSwitch) getProxyConfigSaveDir(clusterType string, proxyPort int) string {
	if consts.IsTwemproxyClusterType(clusterType) {
		return fmt.Sprintf("%s/twemproxy-0.2.4/%d/", consts.DataPath, proxyPort)
	}
	if consts.IsPredixyClusterType(clusterType) {
		return fmt.Sprintf("%s/predixy/%d/", consts.GetRedisDataDir(), proxyPort)
	}
	return ""
}

func (job *RedisDtsOnlineSwitch) getSrcProxyConfigSaveDir() string {
	if job.srcProxyConfigSaveDir == "" {
		return job.srcProxyConfigSaveDir
	}
	return job.getProxyConfigSaveDir(job.params.SrcClusterType, job.params.SrcProxyPort)
}

func (job *RedisDtsOnlineSwitch) getSrcConfigFileSuffix() string {
	if consts.IsTwemproxyClusterType(job.params.SrcClusterType) {
		return "yml"
	}
	if consts.IsPredixyClusterType(job.params.SrcClusterType) {
		return "conf"
	}
	return "conf"
}

func (job *RedisDtsOnlineSwitch) getProxyFile(clusterType string, proxyPort int) string {
	if consts.IsTwemproxyClusterType(clusterType) {
		return fmt.Sprintf("nutcracker.%d.yml", proxyPort)
	} else if consts.IsPredixyClusterType(clusterType) {
		return "predixy.conf"
	}
	return ""
}

func (job *RedisDtsOnlineSwitch) getProxyBackends(clusterType, proxyIP string, proxyPort int,
	proxyPassword string) (backends string, err error) {
	if consts.IsTwemproxyClusterType(clusterType) {
		return myredis.GetTwemproxyBackendsRaw(proxyIP, proxyPort)
	} else if consts.IsPredixyClusterType(clusterType) {
		return myredis.GetPredixyInfoServersRaw(proxyIP, proxyPort, proxyPassword)
	}
	return "", fmt.Errorf("invalid cluster type:%s", clusterType)
}

// IsSrcProxyConnected 检查源proxy是否连接
func (job *RedisDtsOnlineSwitch) IsSrcProxyConnected() (err error) {
	localip, err := util.GetLocalIP()
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	ok, err := util.CheckIPBelongToLocalServer(job.params.SrcProxyIP)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("CheckIPBelongToLocalServer failed,err:%+v", err))
		return err
	}
	if !ok {
		job.runtime.Logger.Error(fmt.Sprintf("src proxy ip:%s not belong to local server(%s)",
			job.params.SrcProxyIP, localip))
		return fmt.Errorf("src proxy ip:%s not belong to local server(%s)", job.params.SrcProxyIP, localip)
	}
	err = myredis.LocalRedisConnectTest(job.params.SrcProxyIP, []int{job.params.SrcProxyPort}, job.params.SrcProxyPassword)
	if err != nil {
		return err
	}
	return nil
}

// IsSrcProxyConfigOK 检查源proxy配置是否ok
// - 配置文件是否存在
// - 密码是否正确
func (job *RedisDtsOnlineSwitch) IsSrcProxyConfigOK() (err error) {
	var psCmd string

	if consts.IsTwemproxyClusterType(job.params.SrcClusterType) {
		psCmd = fmt.Sprintf(
			`ps aux|grep 'twemproxy'|grep -Ev 'grep|exporter'|grep %d|grep 'yml'|head -1|grep --only-match -P 'c .*.yml '|awk '{print $2}'`,
			job.params.SrcProxyPort)
	} else if consts.IsPredixyClusterType(job.params.SrcClusterType) {
		psCmd = fmt.Sprintf(`ps aux|grep 'predixy'|grep -Ev 'grep|exporter'|grep %d|grep 'conf'|awk '{print $NF}'`,
			job.params.SrcProxyPort)
	} else {
		err = fmt.Errorf("unknown src cluster type:%s", job.params.SrcClusterType)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.runtime.Logger.Info(fmt.Sprintf("psCmd:%s", psCmd))
	job.srcProxyConfigFile, err = util.RunBashCmd(psCmd, "", nil, 30*time.Second)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("psCmd(%s) fail,err:%+v", psCmd, err))
		return
	}
	if !util.FileExists(job.srcProxyConfigFile) {
		err = fmt.Errorf("src proxy config file(%s) not exists", job.srcProxyConfigFile)
		job.runtime.Logger.Error(err.Error())
		return
	}
	srcProxyBytes, err := os.ReadFile(job.srcProxyConfigFile)
	if err != nil {
		return err
	}
	srcProxyStr := string(srcProxyBytes)
	if !strings.Contains(srcProxyStr, job.getSrcProxyAddr()) {
		err = fmt.Errorf("src proxy config file(%s) not contains src proxy addr(%s)", job.srcProxyConfigFile,
			job.getSrcProxyAddr())
		job.runtime.Logger.Error(err.Error())
		return
	}
	if !strings.Contains(srcProxyStr, job.params.SrcProxyPassword) {
		err = fmt.Errorf("src proxy config file(%s) not contains correct password", job.srcProxyConfigFile)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.srcProxyConfigSaveDir = filepath.Dir(job.srcProxyConfigFile)
	return nil
}

// BackupSrcProxyConfFile 备份源proxy配置文件
func (job *RedisDtsOnlineSwitch) BackupSrcProxyConfFile() (err error) {
	var msg string
	bakFile := fmt.Sprintf("dts_bak_config.billid_%d.%s_%d.%s",
		job.params.DtsBillID, job.params.SrcProxyIP, job.params.SrcProxyPort,
		job.getSrcConfigFileSuffix())
	bakFile = filepath.Join(job.getSrcProxyConfigSaveDir(), bakFile)
	if util.FileExists(bakFile) {
		msg = fmt.Sprintf("bakFile(%s) already exists", bakFile)
		job.runtime.Logger.Info(msg)
		return
	}
	cpCmd := fmt.Sprintf("cp %s %s", job.srcProxyConfigFile, bakFile)
	job.runtime.Logger.Info(fmt.Sprintf("cpCmd:%s", cpCmd))
	_, err = util.RunBashCmd(cpCmd, "", nil, 30*time.Second)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("cpCmd(%s) fail,err:%+v", cpCmd, err))
		return
	}
	return nil
}

// NewProxyConfigFileForSameType (类型不变时)生成新的proxy配置文件
func (job *RedisDtsOnlineSwitch) NewProxyConfigFileForSameType() (err error) {
	dstConfContent := job.params.DstProxyConfigContent
	dstConfContent = strings.ReplaceAll(dstConfContent, job.getDstProxyAddr(), job.getSrcProxyAddr())
	job.runtime.Logger.Info(fmt.Sprintf("replace dstConfContent dstProxyAddr:%s => srcProxyAddr:%s",
		job.getDstProxyAddr(), job.getDstProxyAddr()))
	dstConfContent = strings.ReplaceAll(dstConfContent, "\\n", "\n")
	if consts.IsTwemproxyClusterType(job.params.SrcClusterType) {
		re := regexp.MustCompile(`\s\spassword\s*:\s*` + job.params.DstProxyPassword)
		dstConfContent = re.ReplaceAllString(dstConfContent, "  password: "+job.params.SrcProxyPassword)
		dstConfContent = strings.ReplaceAll(dstConfContent, "hash_tag: {}", "hash_tag: '{}'")
	} else if consts.IsPredixyClusterType(job.params.SrcClusterType) {
		re := regexp.MustCompile(`Auth\s*"` + job.params.DstProxyPassword + `"`)
		dstConfContent = re.ReplaceAllString(dstConfContent, `Auth "`+job.params.SrcProxyPassword+`"`)
	}

	newFile := fmt.Sprintf("dts_new_config.billid_%d.%s_%d.%s", job.params.DtsBillID, job.params.SrcProxyIP,
		job.params.SrcProxyPort, job.getSrcConfigFileSuffix())
	newFile = filepath.Join(job.getSrcProxyConfigSaveDir(), newFile)
	err = os.WriteFile(newFile, []byte(dstConfContent), 0644)
	if err != nil {
		err = fmt.Errorf("write new proxy config file(%s) fail,err:%+v", newFile, err)
		job.runtime.Logger.Error(err.Error())
		return
	}
	newFileMd5, err := util.GetFileMd5(newFile)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return
	}
	currentMd5, err := util.GetFileMd5(job.srcProxyConfigFile)
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return
	}
	if newFileMd5 == currentMd5 {
		job.runtime.Logger.Info(fmt.Sprintf("newFile(%s) md5(%s) equals currentFile(%s) md5(%s),no need to update",
			newFile, newFileMd5, job.srcProxyConfigFile, currentMd5))
		return nil
	}
	mvCmd := fmt.Sprintf("mv %s %s", newFile, job.srcProxyConfigFile)
	job.runtime.Logger.Info(fmt.Sprintf("mvCmd:%s", mvCmd))
	_, err = util.RunBashCmd(mvCmd, "", nil, 30*time.Second)
	if err != nil {
		return
	}
	return nil
}

// NewProxyConfigFileForDiffType (类型变化时)生成新的proxy配置文件
func (job *RedisDtsOnlineSwitch) NewProxyConfigFileForDiffType() (err error) {
	saveDirForDstPort := job.getProxyConfigSaveDir(job.params.DstClusterType, job.params.DstProxyPort)
	util.MkDirsIfNotExists([]string{saveDirForDstPort})
	dstConfContent := job.params.DstProxyConfigContent
	// 先替换 ip,password,不替换 port
	dstConfContent = strings.ReplaceAll(dstConfContent, job.params.DstProxyIP, job.params.SrcProxyIP)
	dstConfContent = strings.ReplaceAll(dstConfContent, "\\n", "\n")
	if consts.IsTwemproxyClusterType(job.params.DstClusterType) {
		re := regexp.MustCompile(`\s\spassword\s*:\s*` + job.params.DstProxyPassword)
		dstConfContent = re.ReplaceAllString(dstConfContent, "  password: "+job.params.SrcProxyPassword)
		dstConfContent = strings.ReplaceAll(dstConfContent, "hash_tag: {}", "hash_tag: '{}'")
		dstConfContent = strings.ReplaceAll(dstConfContent,
			":1 "+job.params.DstClusterName+" ",
			":1 "+job.params.SrcClusterName+" ")
	} else if consts.IsPredixyClusterType(job.params.DstClusterType) {
		re := regexp.MustCompile(`Auth\s*"` + job.params.DstProxyPassword + `"`)
		dstConfContent = re.ReplaceAllString(dstConfContent, `Auth "`+job.params.SrcProxyPassword+`"`)
	}

	proxyFileForDstPort := job.getProxyFile(job.params.DstClusterType, job.params.DstProxyPort)
	proxyFileForDstPort = filepath.Join(saveDirForDstPort, proxyFileForDstPort)
	err = os.WriteFile(proxyFileForDstPort, []byte(dstConfContent), 0644)
	if err != nil {
		err = fmt.Errorf("write new proxy config file(%s) fail,err:%+v", proxyFileForDstPort, err)
		job.runtime.Logger.Error(err.Error())
		return
	}
	util.LocalDirChownMysql(saveDirForDstPort)

	// 重启 proxy(此时端口还是 dstProxyPort)
	err = job.StopProxy(job.params.SrcProxyIP, job.params.DstProxyPort,
		job.params.SrcProxyPassword, job.params.DstClusterType)
	if err != nil {
		return
	}
	err = job.StartProxy(job.params.SrcProxyIP, job.params.DstProxyPort,
		job.params.SrcProxyPassword, job.params.DstClusterType)
	if err != nil {
		return
	}
	// 确定dstProxy backends包含 dstRedis
	proxyBackends, err := job.getProxyBackends(job.params.DstClusterType,
		job.params.SrcProxyIP, job.params.DstProxyPort,
		job.params.SrcProxyPassword)
	if err != nil {
		return err
	}
	dstRedisAddr := fmt.Sprintf("%s:%d", job.params.DstRedisIP, job.params.DstRedisPort)
	if !strings.Contains(proxyBackends, dstRedisAddr) {
		err = fmt.Errorf("new proxy(%s:%d) backends(%s) not contains dst redis(%s)",
			job.params.SrcProxyIP, job.params.DstProxyPort, proxyBackends, dstRedisAddr)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info(fmt.Sprintf("new proxy(%s:%d) backends contains dst redis(%s)",
		job.params.SrcProxyIP, job.params.DstProxyPort, dstRedisAddr))

	// 再次 stop proxy,修改端口
	err = job.StopProxy(job.params.SrcProxyIP, job.params.DstProxyPort,
		job.params.SrcProxyPassword, job.params.DstClusterType)
	if err != nil {
		return
	}
	// 修改端口
	dstConfContent = strings.ReplaceAll(dstConfContent,
		job.params.SrcProxyIP+":"+strconv.Itoa(job.params.DstProxyPort),
		job.params.SrcProxyIP+":"+strconv.Itoa(job.params.SrcProxyPort),
	)
	dstConfContent = strings.ReplaceAll(dstConfContent,
		strconv.Itoa(job.params.DstProxyPort),
		strconv.Itoa(job.params.SrcProxyPort))
	err = os.WriteFile(proxyFileForDstPort, []byte(dstConfContent), 0644)
	if err != nil {
		err = fmt.Errorf("write final proxy config file(%s) fail,err:%+v", proxyFileForDstPort, err)
		job.runtime.Logger.Error(err.Error())
		return
	}
	// 下面执行逻辑,例如:
	// mv /data/twemproxy-0.2.4/50100/ /data/twemproxy-0.2.4/50000/
	// cd /data/twemproxy-0.2.4/50000/ && mv nutcracker.50100.yml nutcracker.50000.yml
	saveDirForSrcPort := job.getProxyConfigSaveDir(job.params.DstClusterType, job.params.SrcProxyPort)
	if util.FileExists(saveDirForSrcPort) {
		// 先删除
		rmCmd := fmt.Sprintf("rm -rf %s", saveDirForSrcPort)
		job.runtime.Logger.Info(rmCmd)
		util.RunBashCmd(rmCmd, "", nil, 30*time.Second)
	}
	mvCmd := fmt.Sprintf("mv %s %s", saveDirForDstPort, saveDirForSrcPort)
	job.runtime.Logger.Info(mvCmd)
	_, err = util.RunBashCmd(mvCmd, "", nil, 30*time.Second)
	if err != nil {
		err = fmt.Errorf("mv proxy config dir(%s) to dir(%s) fail,err:%+v", saveDirForDstPort, saveDirForSrcPort, err)
		job.runtime.Logger.Error(err.Error())
		return
	}
	proxyFileForSrcPort := job.getProxyFile(job.params.DstClusterType, job.params.SrcProxyPort)
	if filepath.Base(proxyFileForDstPort) != proxyFileForSrcPort {
		mvCmd = fmt.Sprintf("cd %s && mv %s %s", saveDirForSrcPort, filepath.Base(proxyFileForDstPort), proxyFileForSrcPort)
		job.runtime.Logger.Info(mvCmd)
		_, err = util.RunBashCmd(mvCmd, "", nil, 30*time.Second)
		if err != nil {
			return
		}
	}

	util.LocalDirChownMysql(saveDirForSrcPort)

	return nil
}

// IsProxyAlive 检查proxy是否存活
func (job *RedisDtsOnlineSwitch) IsProxyAlive(proxyIP string, proxyPort int, proxyPassword string) (alive bool) {
	var err error
	alive, err = util.CheckPortIsInUse(proxyIP, strconv.Itoa(proxyPort))
	if !alive {
		return alive
	}
	addr := fmt.Sprintf("%s:%d", proxyIP, proxyPort)
	client, err := myredis.NewRedisClientWithTimeout(addr, proxyPassword, 0, consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		return false
	}
	defer client.Close()
	return true
}

// StartProxy 启动proxy
func (job *RedisDtsOnlineSwitch) StartProxy(proxyIP string, proxyPort int,
	proxyPassword string, clusterType string) (err error) {
	if job.IsProxyAlive(proxyIP, proxyPort, proxyPassword) {
		job.runtime.Logger.Info(fmt.Sprintf("proxy(%s:%d) already started,skip...", proxyIP, proxyPort))
		return nil
	}
	var cmd string
	if consts.IsTwemproxyClusterType(clusterType) {
		cmd = fmt.Sprintf("/usr/local/twemproxy/bin/start_nutcracker.sh %d", proxyPort)
	} else if consts.IsPredixyClusterType(clusterType) {
		cmd = fmt.Sprintf("/usr/local/predixy/bin/start_predixy.sh %d", proxyPort)
	}
	job.runtime.Logger.Info(fmt.Sprintf("start proxy(%s:%d) cmd:%s", proxyIP, proxyPort, cmd))
	startCmd := []string{"su", consts.MysqlAaccount, "-c", cmd}
	maxRetryTimes := 5
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		err = nil
		_, err = util.RunLocalCmd(startCmd[0], startCmd[1:], "", nil, 30*time.Second)
		if err != nil {
			job.runtime.Logger.Warn(fmt.Sprintf("start proxy(%s:%d) fail,err:%+v,retry...", proxyIP, proxyPort, err))
			time.Sleep(5 * time.Second)
			continue
		}
		if !job.IsProxyAlive(proxyIP, proxyPort, proxyPassword) {
			job.runtime.Logger.Warn(fmt.Sprintf("start proxy(%s:%d) fail,proxy not alive,retry...", proxyIP, proxyPort))
			time.Sleep(5 * time.Second)
			continue
		}
		break
	}
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("start proxy(%s:%d) fail,err:%+v, not retry", proxyIP, proxyPort, err))
		return
	}
	job.runtime.Logger.Info(fmt.Sprintf("start proxy(%s:%d) success", proxyIP, proxyPort))
	return nil
}

// StopProxy 停止proxy
func (job *RedisDtsOnlineSwitch) StopProxy(proxyIP string, proxyPort int,
	proxyPassword string, clusterType string) error {
	var err error
	if !job.IsProxyAlive(proxyIP, proxyPort, proxyPassword) {
		job.runtime.Logger.Info(fmt.Sprintf("proxy(%s:%d) already stopped,skip...", proxyIP, proxyPort))
		return nil
	}
	var cmd1, killCmd string
	if consts.IsTwemproxyClusterType(clusterType) {
		cmd1 = fmt.Sprintf("/usr/local/twemproxy/bin/stop_nutcracker.sh %d", proxyPort)
		killCmd = fmt.Sprintf(
			`ps aux|grep 'twemproxy'|grep -Ev 'grep|exporter'|grep %d|head -1|awk '{print $2}'|xargs kill -9`,
			proxyPort)
	} else if consts.IsPredixyClusterType(clusterType) {
		cmd1 = fmt.Sprintf("/usr/local/predixy/bin/stop_predixy.sh %d", proxyPort)
		killCmd = fmt.Sprintf(`ps aux|grep 'predixy'|grep -Ev 'grep|exporter'|grep %d|awk '{print $2}'|xargs kill -9`,
			proxyPort)
	}
	job.runtime.Logger.Info(fmt.Sprintf("stop proxy(%s:%d) cmd1:%s,cmd2:%s", proxyIP, proxyPort, cmd1, killCmd))
	stopCmd := []string{"su", consts.MysqlAaccount, "-c", cmd1}
	util.RunLocalCmd(stopCmd[0], stopCmd[1:], "", nil, 30*time.Second)
	if !job.IsProxyAlive(proxyIP, proxyPort, proxyPassword) {
		job.runtime.Logger.Info(fmt.Sprintf("proxy(%s:%d) stop success", proxyIP, proxyPort))
		return nil
	}
	time.Sleep(2 * time.Second)
	_, err = util.RunBashCmd(killCmd, "", nil, 30*time.Second)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("proxy(%s:%d) stop fail,err:%+v", proxyIP, proxyPort, err))
		return err
	}
	if job.IsProxyAlive(proxyIP, proxyPort, proxyPassword) {
		err = fmt.Errorf("proxy(%s:%d) stop fail,proxy still alive", proxyIP, proxyPort)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info(fmt.Sprintf("proxy(%s:%d) stop success", proxyIP, proxyPort))
	return nil
}

// RestartProxyAndCheckBackends 重启proxy并检查后端是否正常
func (job *RedisDtsOnlineSwitch) RestartProxyAndCheckBackends() (err error) {
	err = job.StopProxy(job.params.SrcProxyIP, job.params.SrcProxyPort,
		job.params.SrcProxyPassword, job.params.SrcClusterType)
	if err != nil {
		return
	}
	time.Sleep(2 * time.Second)
	err = job.StartProxy(job.params.SrcProxyIP, job.params.SrcProxyPort,
		job.params.SrcProxyPassword, job.params.DstClusterType)
	if err != nil {
		return err
	}
	proxyBackends, err := job.getProxyBackends(job.params.DstClusterType,
		job.params.SrcProxyIP, job.params.SrcProxyPort,
		job.params.SrcProxyPassword)
	if err != nil {
		return err
	}
	dstRedisAddr := fmt.Sprintf("%s:%d", job.params.DstRedisIP, job.params.DstRedisPort)
	if !strings.Contains(proxyBackends, dstRedisAddr) {
		err = fmt.Errorf("proxy(%s:%d) backends(%s) not contains dst redis(%s)",
			job.params.SrcProxyIP, job.params.SrcProxyPort, proxyBackends, dstRedisAddr)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	job.runtime.Logger.Info(fmt.Sprintf("proxy(%s:%d) backends contains dst redis(%s)",
		job.params.SrcProxyIP, job.params.SrcProxyPort, dstRedisAddr))
	return nil
}

func (job *RedisDtsOnlineSwitch) getProxyRoleByClusterType(clusterType string) string {
	if consts.IsTwemproxyClusterType(clusterType) {
		return "twemproxy"
	} else if consts.IsPredixyClusterType(clusterType) {
		return "predixy"
	}
	return ""
}

// RestartDbMon 如果集群类型有变化,修复dbmon 配置,重启 dbmon
func (job *RedisDtsOnlineSwitch) RestartDbMon() (err error) {
	if job.params.SrcClusterType == job.params.DstClusterType {
		job.runtime.Logger.Info("src cluster type equals dst cluster type,skip restart dbmon")
		return nil
	}
	sedCmd := fmt.Sprintf(`sed -i 's/cluster_type: %s/cluster_type: %s/g' %s`,
		job.params.SrcClusterType, job.params.DstClusterType, consts.BkDbmonConfFile)
	job.runtime.Logger.Info(sedCmd)
	_, err = util.RunBashCmd(sedCmd, "", nil, 30*time.Second)
	if err != nil {
		return
	}
	srcProxyRole := job.getProxyRoleByClusterType(job.params.SrcClusterType)
	dstProxyRole := job.getProxyRoleByClusterType(job.params.DstClusterType)
	if srcProxyRole != dstProxyRole {
		sedCmd = fmt.Sprintf(`sed -i 's/meta_role: %s/meta_role: %s/g' %s`,
			srcProxyRole, dstProxyRole, consts.BkDbmonConfFile)
		job.runtime.Logger.Info(sedCmd)
		_, err = util.RunBashCmd(sedCmd, "", nil, 30*time.Second)
		if err != nil {
			return
		}
	}
	// 重启 dbmon
	err = util.StopBkDbmon()
	if err != nil {
		return err
	}
	err = util.StartBkDbmon()
	if err != nil {
		return err
	}
	return nil
}

// UntarDstProxyMedia 解压目标 proxy 介质
func (job *RedisDtsOnlineSwitch) UntarDstProxyMedia() (err error) {
	// 如果源集群、目标集群都是 twemproxy 类型 or 都是 predixy 类型,则不需要解压介质 s
	if consts.IsTwemproxyClusterType(job.params.SrcClusterType) &&
		consts.IsTwemproxyClusterType(job.params.DstClusterType) {
		job.runtime.Logger.Info("src cluster and dst cluster both twemproxy,skip untar media")
		return
	}
	if consts.IsPredixyClusterType(job.params.SrcClusterType) &&
		consts.IsPredixyClusterType(job.params.DstClusterType) {
		job.runtime.Logger.Info("src cluster and dst cluster both predixy,skip untar media")
		return
	}
	err = job.params.DstProxyPkg.Check()
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("check dst proxy pkg fail,err:%+v", err))
		return err
	}
	pkgBaseName := job.params.DstProxyPkg.GePkgBaseName()
	dstProxyBinDir := filepath.Join(consts.UsrLocal, pkgBaseName) + string(filepath.Separator)
	_, err = os.Stat(dstProxyBinDir)
	if err != nil && os.IsNotExist(err) {
		// 如果包不存在,则解压到 /usr/local 下
		pkgAbsPath := job.params.DstProxyPkg.GetAbsolutePath()
		tarCmd := fmt.Sprintf("tar -zxf %s -C %s", pkgAbsPath, consts.UsrLocal)
		job.runtime.Logger.Info(tarCmd)
		_, err = util.RunBashCmd(tarCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
		util.LocalDirChownMysql(dstProxyBinDir)
	}
	var proxySoftLink string
	if consts.IsTwemproxyClusterType(job.params.DstClusterType) {
		proxySoftLink = filepath.Join(consts.UsrLocal, "twemproxy")
	} else if consts.IsPredixyClusterType(job.params.DstClusterType) {
		proxySoftLink = filepath.Join(consts.UsrLocal, "predixy")
	}
	var createSoftLink bool = false
	var softLinkTarget string
	_, err = os.Stat(proxySoftLink)
	if err != nil && os.IsNotExist(err) {
		// 如果软连接不存在,则创建软连接
		createSoftLink = true
	} else {
		// 如果软连接存在,则判断是否指向了正确的目录
		softLinkTarget, err = os.Readlink(proxySoftLink)
		if err != nil {
			job.runtime.Logger.Error(fmt.Sprintf("read soft link(%s) fail,err:%+v", proxySoftLink, err))
			return err
		}
		if softLinkTarget != dstProxyBinDir {
			// 如果软连接指向的目录不正确,则删除软连接,重新创建
			createSoftLink = true
			rmSoftLinkCmd := fmt.Sprintf("rm -f %s", proxySoftLink)
			job.runtime.Logger.Info(rmSoftLinkCmd)
			_, err = util.RunBashCmd(rmSoftLinkCmd, "", nil, 10*time.Second)
			if err != nil {
				return err
			}
		}
	}
	if createSoftLink {
		// 创建软连接
		softLinkCmd := fmt.Sprintf("ln -s %s %s", dstProxyBinDir, proxySoftLink)
		job.runtime.Logger.Info(softLinkCmd)
		_, err = util.RunBashCmd(softLinkCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
		job.runtime.Logger.Info(fmt.Sprintf("create soft link(%s) success", proxySoftLink))
	}
	job.runtime.Logger.Info(fmt.Sprintf("soft link(%s) => %s", proxySoftLink, dstProxyBinDir))
	util.LocalDirChownMysql(proxySoftLink + string(filepath.Separator))

	if consts.IsPredixyClusterType(job.params.DstClusterType) {
		sedCmd := fmt.Sprintf("sed -i 's#/data#%s#g' %s", consts.GetRedisDataDir(),
			filepath.Join(proxySoftLink, "bin", "start_predixy.sh"))
		job.runtime.Logger.Info(sedCmd)
		_, err = util.RunBashCmd(sedCmd, "", nil, 30*time.Second)
		if err != nil {
			return
		}
	}
	return nil
}

// MvSrcProxyCfgDirForDiffType move源 proxy 配置文件目录(如果源集群、目标集群类型不一致)
func (job *RedisDtsOnlineSwitch) MvSrcProxyCfgDirForDiffType() (err error) {
	srcProxyConfDir := job.getSrcProxyConfigSaveDir()
	parentDir := filepath.Dir(srcProxyConfDir)

	targetConfDir := fmt.Sprintf("dts_online_switch_bak.billid_%d.%d", job.params.DtsBillID, job.params.SrcProxyPort)
	targetConfDir = filepath.Join(parentDir, targetConfDir)
	_, err = os.Stat(targetConfDir)
	if err == nil {
		// 如果目标目录已经存在,则直接返回
		job.runtime.Logger.Info(fmt.Sprintf("target conf dir(%s) already exist,skip mv", targetConfDir))
		return nil
	}
	mvCmd := fmt.Sprintf("mv %s %s", srcProxyConfDir, targetConfDir)
	job.runtime.Logger.Info(mvCmd)
	_, err = util.RunBashCmd(mvCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	job.runtime.Logger.Info(fmt.Sprintf("mv src proxy conf dir(%s) to target dir(%s) success",
		srcProxyConfDir, targetConfDir))
	return nil
}
