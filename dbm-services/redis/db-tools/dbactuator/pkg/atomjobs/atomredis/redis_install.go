package atomredis

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/report"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// RedisInstallParams 安装参数
type RedisInstallParams struct {
	common.MediaPkg
	DbToolsPkg       common.DbToolsMediaPkg      `json:"dbtoolspkg"`
	RedisModulesPkg  common.RedisModulesMediaPkg `json:"redis_modules_pkg"`
	DataDirs         []string                    `json:"data_dirs"`
	IP               string                      `json:"ip" validate:"required"`
	Ports            []int                       `json:"ports"`      // 如果端口不连续,可直接指定端口
	StartPort        int                         `json:"start_port"` // 如果端口连续,则可直接指定起始端口和实例个数
	InstNum          int                         `json:"inst_num"`
	Password         string                      `json:"password" validate:"required"`
	Databases        int                         `json:"databases" validate:"required"`
	RedisConfConfigs map[string]string           `json:"redis_conf_configs" validate:"required"`
	DbType           string                      `json:"db_type" validate:"required"`
	// MaxMemory         uint64                      `json:"maxmemory"` //不要它了撒
	LoadModulesDetail []LoadModuleItem `json:"load_modules_detail"`
}

// LoadModuleItem 加载module信息
type LoadModuleItem struct {
	MajorVersion string `json:"major_version"`
	ModuleName   string `json:"module_name"`
	SoFile       string `json:"so_file"`
}

// RedisInstall redis install atomjob
type RedisInstall struct {
	runtime           *jobruntime.JobGenericRuntime
	params            RedisInstallParams
	RealDataDir       string // /data/redis
	RedisBinDir       string // /usr/local/redis
	RedisConfTemplate string // 配置模版
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisInstall)(nil)

// NewRedisInstall new
func NewRedisInstall() jobruntime.JobRunner {
	return &RedisInstall{}
}

// Init 初始化
func (job *RedisInstall) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("RedisInstall Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisInstall Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	// ports 和 inst_num 不能同时为空
	if len(job.params.Ports) == 0 && job.params.InstNum == 0 {
		err = fmt.Errorf("RedisInstall ports(%+v) and inst_num(%d) is invalid", job.params.Ports, job.params.InstNum)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	// 6379<= start_port <= 55535
	if job.params.InstNum > 0 && (job.params.StartPort > 55535 || job.params.StartPort < 6379) {
		err = fmt.Errorf("RedisInstall start_port(%d) must range [6379,5535]", job.params.StartPort)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	if job.params.InstNum > 0 {
		ports := make([]int, 0, job.params.InstNum)
		for idx := 0; idx < job.params.InstNum; idx++ {
			ports = append(ports, job.params.StartPort+idx)
		}
		job.params.Ports = ports
	}
	job.runtime.Logger.Info(fmt.Sprintf("init end, server:%s,ports:%s",
		job.params.IP, myredis.ConvertSlotToStr(job.params.Ports)))

	return nil
}

// Name 原子任务名
func (job *RedisInstall) Name() string {
	return "redis_install"
}

// Run 执行
func (job *RedisInstall) Run() (err error) {
	// 增加文件锁
	lockFileName := fmt.Sprintf("%s/%s", consts.PackageSavePath, "redis_install.lock")
	fl := util.NewFileLock(lockFileName)
	runTimes := 0
	startTime := time.Now()
	dur := 30 * time.Minute
	timer := time.NewTimer(dur)

	sleepTime := time.Duration(rand.Intn(10)+1) * time.Second
	time.Sleep(sleepTime)
	// 如果持续半个小时都没拿到锁就认为任务失败了
	for {
		err := fl.TryFileLock()
		if err == nil {
			job.runtime.Logger.Info("get file lock:%s success, will install redis port %+v",
				lockFileName, job.params.Ports)
			break
		}

		select {
		case <-timer.C:
			return errors.New("the task has been executed for more than 30 minutes")
		default:
			runTimes++
			sleepTime := time.Duration(rand.Intn(5)+5) * time.Second
			job.runtime.Logger.Info("job ports %+v get file lock(%s) err:%+v. run %d times and takes %v. "+
				"will sleep %d second",
				job.params.Ports, lockFileName, err, runTimes, time.Since(startTime), int(sleepTime)/1000000000)

			time.Sleep(sleepTime)
		}
	}
	defer fl.ReleaseFileLock()

	err = job.UntarMedia()
	if err != nil {
		return
	}
	err = job.GetRealDataDir()
	if err != nil {
		return
	}
	err = job.InitInstanceDirs()
	if err != nil {
		return
	}
	err = job.StartAll()
	if err != nil {
		return
	}
	return job.newExporterConfig()
}

// UntarMedia 解压介质
func (job *RedisInstall) UntarMedia() (err error) {
	job.runtime.Logger.Info("begin to untar redis media")
	defer func() {
		if err != nil {
			job.runtime.Logger.Error("untar redis media fail")
		} else {
			job.runtime.Logger.Info("untar redis media success")
		}
	}()
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error("UntarMedia failed,err:%v", err)
		return
	}
	pkgBaseName := job.params.GePkgBaseName()
	job.RedisBinDir = filepath.Join(consts.UsrLocal, pkgBaseName)
	_, err = os.Stat(job.RedisBinDir)
	if err != nil && os.IsNotExist(err) {
		// 如果包不存在,则解压到 /usr/local 下
		pkgAbsPath := job.params.GetAbsolutePath()
		tarCmd := fmt.Sprintf("tar -zxf %s -C %s", pkgAbsPath, consts.UsrLocal)
		job.runtime.Logger.Info(tarCmd)
		_, err = util.RunBashCmd(tarCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
		util.LocalDirChownMysql(job.RedisBinDir)
	}
	redisSoftLink := filepath.Join(consts.UsrLocal, "redis")
	_, err = os.Stat(redisSoftLink)
	if err != nil && os.IsNotExist(err) {
		// 如果 /usr/local/redis 不存在,则创建软链接
		err = os.Symlink(job.RedisBinDir, redisSoftLink)
		if err != nil {
			err = fmt.Errorf("os.Symlink failed,err:%v,dir:%s,softLink:%s", err, job.RedisBinDir, redisSoftLink)
			job.runtime.Logger.Error(err.Error())
			return
		}
		job.runtime.Logger.Info("create soft link success,redisBinDir:%s,redisSoftLink:%s", job.RedisBinDir, redisSoftLink)
	}
	// 再次确认 /usr/local/redis 是指向 目标redis目录
	// 参数: /usr/loca/redis => 结果: /usr/local/redis-6.2.7
	realLink, err := filepath.EvalSymlinks(redisSoftLink)
	if err != nil {
		err = fmt.Errorf("filepath.EvalSymlinks failed,err:%v,redisSoftLink:%s", err, redisSoftLink)
		job.runtime.Logger.Error(err.Error())
		return
	}
	redisBaseName := filepath.Base(realLink)
	isAdditionalDeployAndMajorVersionSame, _ := job.IsAdditionalDeployAndMajorVersionSame(redisBaseName, pkgBaseName)
	if pkgBaseName != redisBaseName && isAdditionalDeployAndMajorVersionSame == false {
		// 不是追加部署,且大版本相同,则报错
		err = fmt.Errorf("%s 指向 %s 而不是 %s", redisSoftLink, redisBaseName, pkgBaseName)
		job.runtime.Logger.DPanic(err.Error())
		return
	}
	job.RedisBinDir = filepath.Join(redisSoftLink, "bin")
	util.LocalDirChownMysql(redisSoftLink)

	addEtcProfile := fmt.Sprintf(`
ret=$(grep -i %q /etc/profile)
if [[ -z $ret ]]
then
echo "export PATH=%s:\$PATH" >> /etc/profile
fi
`, job.RedisBinDir, job.RedisBinDir)
	_, err = util.RunBashCmd(addEtcProfile, "", nil, 10*time.Second)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info(fmt.Sprintf("UntarMedia success,redisBinDir:%s,redisSoftLink:%s", job.RedisBinDir,
		redisSoftLink))

	err = job.params.DbToolsPkg.Install()
	if err != nil {
		return err
	}
	if len(job.params.LoadModulesDetail) > 0 {
		err = job.params.RedisModulesPkg.UnTar()
		if err != nil {
			return err
		}
	}
	return nil
}

// IsAdditionalDeployAndMajorVersionSame 是否是追加部署,是否是大版本相同
// 以前系统上Redis很多6.2.7版本,现在打包的是 6.2.14版本
// 会导致无法追加部署。所以追加部署,只判断 大版本相同即可
func (job *RedisInstall) IsAdditionalDeployAndMajorVersionSame(currentVer, targetVer string) (ok bool, err error) {
	// 先判断是否是 追加部署,追加部署只在 主从版本上存在,所以直接判断 redis-server进程存在与否即可
	psCmd := "ps aux|grep 'redis-server'|grep -v grep"
	job.runtime.Logger.Info(psCmd)
	ret, _ := util.RunBashCmd(psCmd, "", nil, 10*time.Second)
	if ret == "" {
		// 判断没有 redis-server,说明不是追加部署,返回false
		return false, nil
	}
	// 判断 当前版本 和 目标版本 主版本是否相同
	return util.IsMajorVersionSame(targetVer, currentVer)
}

// GetRealDataDir 确认redis Data Dir,依次检查 /data1、/data、用户输入的dirs, 如果是挂载点则返回
func (job *RedisInstall) GetRealDataDir() (err error) {
	// dirs := make([]string, 0, len(job.params.DataDirs)+2)
	// dirs = append(dirs, consts.Data1Path)
	// dirs = append(dirs, consts.DataPath)
	// dirs = append(dirs, job.params.DataDirs...)
	// job.RealDataDir, err = util.FindFirstMountPoint(dirs...)
	// if err != nil {
	// 	job.runtime.Logger.Error("GetInstallDir failed,err:%v,dirs:%+v", err, dirs)
	// 	return
	// }
	job.RealDataDir = filepath.Join(consts.GetRedisDataDir(), "/redis")
	job.runtime.Logger.Info("GetRealDataDir success,dataDir:%s", job.RealDataDir)
	return nil
}

// InitInstanceDirs 初始化实例文件夹
func (job *RedisInstall) InitInstanceDirs() (err error) {
	job.runtime.Logger.Info("begin to init redis instances' dirs")
	defer func() {
		if err != nil {
			job.runtime.Logger.Error("init redis instances' dirs fail")
		} else {
			job.runtime.Logger.Info("init redis instances' dirs success")
		}
	}()
	var instDir string
	for _, port := range job.params.Ports {
		instDir = filepath.Join(job.RealDataDir, strconv.Itoa(port))
		var dirs []string
		if consts.IsRedisInstanceDbType(job.params.DbType) {
			dirs = append(dirs, filepath.Join(instDir, "data"))
		} else if consts.IsTendisplusInstanceDbType(job.params.DbType) {
			dirs = append(dirs, filepath.Join(instDir, "data", "log"))
			dirs = append(dirs, filepath.Join(instDir, "data", "db"))
			dirs = append(dirs, filepath.Join(instDir, "data", "dump"))
			dirs = append(dirs, filepath.Join(instDir, "data", "slowlog"))
		} else if consts.IsTendisSSDInstanceDbType(job.params.DbType) {
			dirs = append(dirs, filepath.Join(instDir, "data"))
			dirs = append(dirs, filepath.Join(instDir, "rbinlog"))
		} else {
			err = fmt.Errorf("unknown dbType(%s)", job.params.DbType)
			job.runtime.Logger.Error(err.Error())
			return
		}
		job.runtime.Logger.Info("MkDirAll %+v", dirs)
		err = util.MkDirsIfNotExists(dirs)
		if err != nil {
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	err = util.LocalDirChownMysql(job.RealDataDir)
	if err != nil {
		return err
	}
	err = report.CreateReportDir()
	if err != nil {
		return err
	}
	return nil
}

// IsRedisInstalled 检查redis实例已经安装
func (job *RedisInstall) IsRedisInstalled(port int) (installed bool, err error) {
	job.runtime.Logger.Info("begin to check whether redis %s:%d was installed",
		job.params.IP, port)

	instDir := filepath.Join(job.RealDataDir, strconv.Itoa(port))
	instConfFile := filepath.Join(instDir, "redis.conf")
	if util.FileExists(instConfFile) {
		grepCmd := fmt.Sprintf("grep -i requirepass %s |grep -vP '^#'||{ true; }", instConfFile)
		job.runtime.Logger.Info(grepCmd)
		grepRet, err := util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
		if err != nil {
			return false, err
		}
		if grepRet == "" || !strings.Contains(grepRet, job.params.Password) {
			err = fmt.Errorf("redis %s:%d configFile:%s exists,but 'requirepass' not match", job.params.IP, port, instConfFile)
			return false, err
		}
	}

	portIsUse, err := util.CheckPortIsInUse(job.params.IP, strconv.Itoa(port))
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return
	}
	if !portIsUse {
		// 端口没被占用
		return false, nil
	}
	// 端口已被使用
	redisAddr := job.params.IP + ":" + strconv.Itoa(port)
	redisCli, err := myredis.NewRedisClientWithTimeout(redisAddr, job.params.Password, 0,
		consts.TendisTypeRedisInstance, 5*time.Second)
	if err != nil {
		err = fmt.Errorf("%d is in used by other process", port)
		job.runtime.Logger.Error(err.Error())
		return false, err
	}
	defer redisCli.Close()
	// 检查是否为一个空实例
	dbSize, err := redisCli.DbSize()
	if err != nil {
		return false, err
	}
	if dbSize > 20 {
		// key个数大于20
		err = fmt.Errorf("redis:%s is in use,dbsize=%d", redisAddr, dbSize)
		job.runtime.Logger.Error(err.Error())
		return
	}
	if !consts.IsTendisplusInstanceDbType(job.params.DbType) {
		// 随机检查20个key
		randomRets := []string{}
		for i := 0; i < 20; i++ {
			k, err := redisCli.Randomkey()
			if err != nil {
				return false, err
			}
			if k != "" && !util.IsDbmSysKeys(k) {
				randomRets = append(randomRets, k)
			}
		}
		if len(randomRets) > 0 {
			err = fmt.Errorf("redis:%s is in use,exists keys:%+v", redisAddr, randomRets)
			job.runtime.Logger.Error(err.Error())
			return
		}
	}

	// 检查版本是否正确
	infoMap, err := redisCli.Info("server")
	if err != nil {
		return false, err
	}
	serverVer := infoMap["redis_version"]
	// 版本格式兼容tendisSSD的情况
	// tendisSSD 包名 redis-2.8.17-rocksdb-v1.2.20.tar.gz, 版本名(redis_version) 2.8.17-TRedis-v1.2.20
	serverVer = strings.ReplaceAll(serverVer, "TRedis", "rocksdb")
	pkgBaseName := job.params.GePkgBaseName()
	isAdditionalDeployAndMajorVersionSame, _ := job.IsAdditionalDeployAndMajorVersionSame(serverVer, pkgBaseName)
	if !strings.Contains(pkgBaseName, serverVer) && isAdditionalDeployAndMajorVersionSame == false {
		// 不是追加部署,且大版本相同,则报错
		err = fmt.Errorf("redis:%s installed but version(%s) not %s", redisAddr, serverVer, pkgBaseName)
		job.runtime.Logger.Error(err.Error())
		return
	}
	// redis实例已成功安装,且是一个空实例,且版本正确
	job.runtime.Logger.Info(fmt.Sprintf("redis(%s) install success,dbsize:%d,version:%s",
		redisAddr, dbSize, serverVer))
	return true, nil
}

// isModulesSoFileExists 判断module so文件是否存在
func (job *RedisInstall) isModulesSoFileExists() (err error) {
	if len(job.params.LoadModulesDetail) == 0 {
		job.runtime.Logger.Info("no module to load")
		return nil
	}
	// 确认module so文件存在
	soFile := ""
	for _, moduleItem := range job.params.LoadModulesDetail {
		soFile = filepath.Join(consts.RedisModulePath, moduleItem.SoFile)
		if !util.FileExists(soFile) {
			err = errors.New(fmt.Sprintf("module(%s) not exists", soFile))
			job.runtime.Logger.Error(err.Error())
			return err
		}
	}
	return nil
}

func (job *RedisInstall) getRedisConfTemplate() error {
	if job.RedisConfTemplate != "" {
		return nil
	}
	pkgBaseName := job.params.GePkgBaseName()
	sb := strings.Builder{}
	for key, value := range job.params.RedisConfConfigs {
		key = strings.TrimSpace(key)
		lower_key := strings.ToLower(key)
		value = strings.TrimSpace(value)
		if key == "loadmodule" {
			continue
		}
		if key == "repl-diskless-sync" &&
			strings.HasPrefix(pkgBaseName, "redis-2.8.17") {
			continue
		}
		if lower_key == "netiothreadnum" {
			value = strconv.Itoa(util.GetTendisplusNetIOThreadNum())
		} else if lower_key == "executorthreadnum" {
			value = strconv.Itoa(util.GetTendisplusExeThreadNum())
		} else if lower_key == "executorworkpoolsize" {
			value = strconv.Itoa(util.GetTendisplusExeWorkPoolSize())
		} else if lower_key == "rocks.max_background_jobs" {
			value = strconv.Itoa(util.GetTendisplusMaxBGJobs())
		} else if lower_key == "incrpushthreadnum" {
			value = strconv.Itoa(util.GetIncrPushThreadnum())
		} else if lower_key == "rocks.max_background_compactions" {
			value = strconv.Itoa(util.GetMaxBgCompactions())
		} else if lower_key == "migratesenderthreadnum" {
			value = strconv.Itoa(util.GetMigrateSenderThreadNum())
		} else if lower_key == "migratereceivethreadnum" {
			value = strconv.Itoa(util.GetMigrateReceiverThreadNum())
		} else if lower_key == "migrateclearthreadnum" {
			value = strconv.Itoa(util.GetMigrateClearTheadNum())
		}
		if value == "" {
			value = "\"\"" // 针对 save ""的情况
		}
		sb.WriteString(key + " " + value + "\n")
	}
	// 加载module
	soFile := ""
	for _, moduleItem := range job.params.LoadModulesDetail {
		if strings.Contains(moduleItem.SoFile, "libB2RedisModule") {
			// libB2RedisModule 相关module需要关闭 aof,否则会报错
			sb.WriteString("appendonly no\n")
		}
		soFile = filepath.Join(consts.RedisModulePath, moduleItem.SoFile)
		sb.WriteString("loadmodule " + soFile + "\n")
	}
	job.RedisConfTemplate = sb.String()
	return nil
}

// GenerateConfigFile 生成配置文件
func (job *RedisInstall) GenerateConfigFile(port int) (err error) {
	job.runtime.Logger.Info("begin to GenerateConfigFile,port:%d", port)
	err = job.isModulesSoFileExists()
	if err != nil {
		return err
	}
	err = job.getRedisConfTemplate()
	if err != nil {
		return err
	}

	clusterEnabled := "no"
	if consts.IsClusterDbType(job.params.DbType) {
		clusterEnabled = "yes"
	}
	instDir := filepath.Join(job.RealDataDir, strconv.Itoa(port))
	instConfFile := filepath.Join(instDir, "redis.conf")
	instBlockcache, err := util.GetTendisplusBlockcache(uint64(len(job.params.Ports)))
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	writeBufferSize, err := util.GetTendisplusWriteBufferSize(uint64(len(job.params.Ports)))
	if err != nil {
		job.runtime.Logger.Error(err.Error())
		return err
	}
	confData := job.RedisConfTemplate
	confData = strings.ReplaceAll(confData, "{{address}}", job.params.IP)
	confData = strings.ReplaceAll(confData, "{{port}}", strconv.Itoa(port))
	confData = strings.ReplaceAll(confData, "{{password}}", job.params.Password)
	confData = strings.ReplaceAll(confData, "{{redis_data_dir}}", instDir)
	confData = strings.ReplaceAll(confData, "{{databases}}", strconv.Itoa(job.params.Databases))
	confData = strings.ReplaceAll(confData, "{{cluster_enabled}}", clusterEnabled)
	confData = strings.ReplaceAll(confData, "{{maxmemory}}", "0")
	confData = strings.ReplaceAll(confData, "{{rocks_blockcachemb}}", strconv.FormatUint(instBlockcache, 10))
	confData = strings.ReplaceAll(confData, "{{rocks_write_buffer_size}}",
		strconv.FormatUint(writeBufferSize, 10))
	err = ioutil.WriteFile(instConfFile, []byte(confData), os.ModePerm)
	if err != nil {
		job.runtime.Logger.Error("ioutil.WriteFile failed,err:%v,config_file:%s,confData:%s", err, instConfFile, confData)
		return err
	}
	util.LocalDirChownMysql(job.RealDataDir)
	job.runtime.Logger.Info("GenerateConfigFile success,port:%d,configFile:%s", port, instConfFile)
	return nil
}
func (job *RedisInstall) newExporterConfig() (err error) {
	job.runtime.Logger.Info("begin to new exporter config file")
	err = util.MkDirsIfNotExists([]string{consts.ExporterConfDir})
	if err != nil {
		job.runtime.Logger.Error("newExporterConfig mkdirIfNotExists %s failed,err:%v", consts.ExporterConfDir, err)
		return err
	}
	for _, port := range job.params.Ports {
		err = common.CreateLocalExporterConfigFile(job.params.IP, port, consts.MetaRoleRedisMaster, job.params.Password)
		if err != nil {
			return err
		}
	}
	util.LocalDirChownMysql(consts.ExporterConfDir)
	return nil
}

func (job *RedisInstall) getRedisLogFile(port int) (logFile string) {
	instDir := filepath.Join(job.RealDataDir, strconv.Itoa(port))
	if consts.IsTendisplusInstanceDbType(job.params.DbType) {
		logFile = filepath.Join(instDir, "data/log/tendisplus.ERROR")
	} else {
		logFile = filepath.Join(instDir, "redis.log")
	}
	return
}

// StartAll 拉起所有redis实例
func (job *RedisInstall) StartAll() error {
	var installed bool
	var err error
	var addr string
	for _, port := range job.params.Ports {
		instLogFile := job.getRedisLogFile(port)
		startScript := filepath.Join(job.RedisBinDir, "start-redis.sh")
		addr = job.params.IP + ":" + strconv.Itoa(port)

		installed, err = job.IsRedisInstalled(port)
		if err != nil {
			return err
		}
		if installed == true {
			continue
		}
		err = job.GenerateConfigFile(port)
		if err != nil {
			return err
		}
		job.runtime.Logger.Info(fmt.Sprintf("su %s -c \"%s\"", consts.MysqlAaccount, startScript+"  "+strconv.Itoa(port)))
		_, err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", startScript + "  " + strconv.Itoa(port)}, "",
			nil, 10*time.Second)
		if err != nil {
			return err
		}

		maxRetryTimes := 20
		i := 0
		for {
			i++
			if i >= maxRetryTimes {
				break
			}
			installed, err = job.IsRedisInstalled(port)
			if err != nil {
				return err
			}
			if !installed {
				job.runtime.Logger.Info("%s not ready,sleep 2 seconds and retry...", addr)
				time.Sleep(2 * time.Second)
				continue
			}
			break
		}
		if err != nil {
			return err
		}
		if installed {
			// redis启动成功
			continue
		}
		// redis启动失败
		logData, err := util.RunBashCmd(fmt.Sprintf("tail -3 %s", instLogFile), "", nil, 10*time.Second)
		if err != nil {
			return err
		}
		err = fmt.Errorf("redis(%s:%d) startup failed,logData:%s", job.params.IP, port, logData)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// Retry times
func (job *RedisInstall) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisInstall) Rollback() error {
	return nil
}
