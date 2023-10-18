package atomredis

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
	"github.com/gofrs/flock"
)

// RedisInsKeyPatternJobParam 单台机器'key提取&删除'job参数
type RedisInsKeyPatternJobParam struct {
	common.DbToolsMediaPkg
	FileServer           util.FileServerInfo `json:"fileserver" validate:"required"`
	BkBizID              string              `json:"bk_biz_id" validate:"required"`
	Path                 string              `json:"path"`
	Domain               string              `json:"domain"`
	IP                   string              `json:"ip" validate:"required"`
	Ports                []int               `json:"ports"`
	StartPort            int                 `json:"start_port"` // 如果端口连续,则可直接指定起始端口和实例个数
	InstNum              int                 `json:"inst_num"`
	KeyWhiteRegex        string              `json:"key_white_regex"`
	KeyBlackRegex        string              `json:"key_black_regex"`
	IsKeysToBeDel        bool                `json:"is_keys_to_be_del"`
	DeleteRate           int                 `json:"delete_rate"`            // cache Redis删除速率,避免del 命令执行过快
	TendisplusDeleteRate int                 `json:"tendisplus_delete_rate"` // tendisplus删除速率,避免del 命令执行过快
	SsdDeleteRate        int                 `json:"ssd_delete_rate"`        // ssd删除速率,避免del 命令执行过快
}

// TendisKeysPattern key提取&删除
type TendisKeysPattern struct {
	saveDir string
	Err     error `json:"-"`
	params  RedisInsKeyPatternJobParam
	runtime *jobruntime.JobGenericRuntime
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*TendisKeysPattern)(nil)

// NewTendisKeysPattern  new
func NewTendisKeysPattern() jobruntime.JobRunner {
	return &TendisKeysPattern{}
}

// Init 初始化
func (job *TendisKeysPattern) Init(m *jobruntime.JobGenericRuntime) error {
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
			job.runtime.Logger.Error("TendisKeysPattern Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("TendisKeysPattern Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}
	// 白名单不能为空
	if job.params.KeyWhiteRegex == "" {
		err = fmt.Errorf("%s为空,白名单不能为空", job.params.KeyWhiteRegex)
		job.runtime.Logger.Error(err.Error())
		return err
	}

	// ports 和 inst_num 不能同时为空
	if len(job.params.Ports) == 0 && job.params.InstNum == 0 {
		err = fmt.Errorf("TendisKeysPattern ports(%+v) and inst_num(%d) is invalid", job.params.Ports, job.params.InstNum)
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

	return nil

}

// Name 原子任务名
func (job *TendisKeysPattern) Name() string {
	return "tendis_keyspattern"
}

// Run 执行
func (job *TendisKeysPattern) Run() (err error) {
	err = myredis.LocalRedisConnectTest(job.params.IP, job.params.Ports, "")
	if err != nil {
		return
	}
	saveDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak/get_keys_pattern")
	job.saveDir = saveDir
	// 解压key工具包介质
	err = job.UntarMedia()
	if err != nil {
		return
	}
	// 清理目录下15天以前的文件
	job.ClearFilesNDaysAgo(job.saveDir, 15)

	keyTasks := make([]*RedisInsKeyPatternTask, 0, len(job.params.Ports))
	for _, port := range job.params.Ports {
		password, err := myredis.GetPasswordFromLocalConfFile(port)
		if err != nil {
			return err
		}
		task, err := NewRedisInsKeyPatternTask(job.params.BkBizID, job.params.Domain, job.params.IP, port,
			password, saveDir, job.runtime, job.params.FileServer.URL, job.params.FileServer.Bucket,
			job.params.FileServer.Password, job.params.FileServer.Username, job.params.FileServer.Project,
			job.params.Path, job.params.KeyWhiteRegex, job.params.KeyBlackRegex,
			job.params.IsKeysToBeDel, job.params.DeleteRate, job.params.TendisplusDeleteRate, job.params.SsdDeleteRate, 0, 0)
		if err != nil {
			return err
		}
		task.newConnect()
		keyTasks = append(keyTasks, task)
	}

	chanKeyTasks := make(chan *RedisInsKeyPatternTask)
	workerLimit := job.SetWorkLimit(keyTasks)
	// 生产者
	go job.taskQueue(chanKeyTasks, keyTasks)
	wg := sync.WaitGroup{}
	wg.Add(workerLimit)
	for worker := 0; worker < workerLimit; worker++ {
		// 消费者
		go job.keysPatternTask(chanKeyTasks, &wg)
	}
	// 等待所有线程退出
	wg.Wait()

	if job.Err != nil {
		return job.Err
	}

	return nil
}

// Retry times
func (job *TendisKeysPattern) Retry() uint {
	return 2
}

// Rollback rollback
func (job *TendisKeysPattern) Rollback() error {
	return nil
}

// GetInsFullData 获取单实例全量数据
func (task *RedisInsTask) GetInsFullData() {

	if task.Err != nil {
		return
	}
	defer task.redisCli.Close()

	task.Err = task.redisCli.WaitForBackupFinish()
	if task.Err != nil {
		return
	}
	// 生成rdb文件
	task.RedisInsBgsave()
}

// RedisInsKeyPatternTask key提取子任务
type RedisInsKeyPatternTask struct {
	RedisInsTask
	FileServer           util.FileServerInfo `json:"fileserver" validate:"required"`
	Path                 string              `json:"path"`
	KeysFile             string              `json:"keysFile"`
	KeyWhiteRegex        string              `json:"keyWhiteRegex"` // 白
	KeyBlackRegex        string              `json:"keyBlackRegex"`
	ResultFile           string              `json:"resultFile"`
	RedisShakeTool       string              `json:"redisShakeTool"`
	LdbTendisTool        string              `json:"ldbTendisTool"`
	WithExpiredKeys      bool                `json:"withExpiredKeys"`
	SafeDelTool          string              `json:"safeDelTool"` // 执行安全删除的工具
	IsKeysToBeDel        bool                `json:"isKeysToBeDel"`
	DeleteRate           int                 `json:"deleteRate"`           // cache 删除速率,避免del 命令执行过快
	TendisplusDeleteRate int                 `json:"tendisplusDeleteRate"` // tendisplus 删除速率,避免del 命令执行过快
	SsdDeleteRate        int                 `json:"ssdDeleteRate"`        // ssd删除速率,避免del 命令执行过快
	MasterAddr           string              `json:"masterAddr"`
	MasterIP             string              `json:"masterIp"`
	MasterPort           string              `json:"masterPort"`
	MasterAuth           string              `json:"masterAuth"`
	SegStart             int                 `json:"segStart"` // 源实例所属segment start
	SegEnd               int                 `json:"segEnd"`   // 源实例所属segment end

}

// NewRedisInsKeyPatternTask new redis instance keypattern task
func NewRedisInsKeyPatternTask(
	bkBizID, domain, iP string, port int, insPassword, saveDir string,
	runtime *jobruntime.JobGenericRuntime, url, bucket, password, username, project string, path string,
	keyWhite, keyBlack string, iskeysToBeDel bool, deleteRate, tendisplusDeleteRate, ssdDeleteRate int,
	segStart, segEnd int) (task *RedisInsKeyPatternTask, err error) {
	task = &RedisInsKeyPatternTask{}
	t1, err := NewRedisInsTask(bkBizID, domain, iP, port, insPassword, saveDir, runtime)
	if err != nil {
		return task, err
	}
	task.RedisInsTask = *t1
	task.KeyWhiteRegex = keyWhite
	task.KeyBlackRegex = keyBlack
	task.IsKeysToBeDel = iskeysToBeDel
	task.DeleteRate = deleteRate
	task.TendisplusDeleteRate = tendisplusDeleteRate
	task.SsdDeleteRate = ssdDeleteRate
	task.FileServer.URL = url
	task.FileServer.Bucket = bucket
	task.FileServer.Password = password
	task.FileServer.Username = username
	task.FileServer.Project = project
	task.Path = path
	task.WithExpiredKeys = false
	task.SegStart = segStart
	task.SegEnd = segEnd
	return task, nil
}

// UntarMedia 解压key工具包介质
func (job *TendisKeysPattern) UntarMedia() (err error) {
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error("UntarMedis failed err:%v", err)
		return
	}
	err = job.CheckSaveDir()
	if err != nil {
		job.runtime.Logger.Error("检查key保存目录失败: err:%v", err)
		return err
	}

	// Install: 确保dbtools符合预期
	err = job.params.DbToolsMediaPkg.Install()
	if err != nil {
		job.runtime.Logger.Error("DbToolsPkg 初始化失败: err:%v", err)
		job.Err = err
		return err
	}

	// 复制dbtools/ldb_tendisplus,ldb_with_len.3.8, ldb_with_len.5.13
	// redis-shake redisSafeDeleteTool到get_keys_pattern
	cpCmd := fmt.Sprintf("cp  %s/ldb* %s/redis-shake %s/redisSafeDeleteTool %s", consts.DbToolsPath,
		consts.DbToolsPath, consts.DbToolsPath, job.saveDir)

	// // 这里复制所有的，是为了防止工具名变更，也可指定如上一行代码注释
	// cpCmd := fmt.Sprintf("cp  %s/* %s", consts.DbToolsPath, job.saveDir)
	_, err = util.RunBashCmd(cpCmd, "", nil, 100*time.Second)
	if err != nil {
		return
	}
	job.runtime.Logger.Info(cpCmd)

	return nil

}

// CheckSaveDir key分析本地数据目录
func (job *TendisKeysPattern) CheckSaveDir() (err error) {
	_, err = os.Stat(job.saveDir)
	if err != nil && os.IsNotExist(err) {
		mkCmd := fmt.Sprintf("mkdir -p %s ", job.saveDir)
		_, err = util.RunLocalCmd("bash", []string{"-c", mkCmd}, "", nil, 100*time.Second)
		if err != nil {
			err = fmt.Errorf("创建目录:%s失败,err:%v", job.saveDir, err)
			job.runtime.Logger.Error(err.Error())
			return err
		}
		util.LocalDirChownMysql(job.saveDir)
	} else if err != nil {
		err = fmt.Errorf("访问目录:%s 失败,err:%v", job.saveDir, err)
		job.runtime.Logger.Error(err.Error())
		return err

	}
	return nil
}

// SetWorkLimit 设置并发度
func (job *TendisKeysPattern) SetWorkLimit(keyTasks []*RedisInsKeyPatternTask) (workerLimit int) {
	// tendisplus 并发度3
	// tendis_ssd 并发度3
	// tendis_cache 根据数据量确认并发度
	// - 0 < dataSize <= 10GB,并发度4
	// - 10GB < dataSize <= 20GB,并发度3
	// - 20GB < dataSize <= 40GB,并发度2
	// - dataSize > 40GB,并发度1
	task01 := keyTasks[0]
	if task01.TendisType == consts.TendisTypeTendisplusInsance || task01.TendisType == consts.TendisTypeTendisSSDInsance {
		workerLimit = 3
	} else {
		var maxDataSize uint64 = 0
		for _, taskItem := range keyTasks {
			task01 := taskItem
			if task01.DataSize > maxDataSize {
				maxDataSize = task01.DataSize
			}
			msg := fmt.Sprintf("redis(%s:%d) dataSize:%dMB", task01.IP, task01.Port, task01.DataSize/1024/1024)
			job.runtime.Logger.Info(msg)
		}
		if maxDataSize <= 10*consts.GiByte {
			workerLimit = 4
		} else if maxDataSize <= 20*consts.GiByte {
			workerLimit = 3
		} else if maxDataSize <= 40*consts.GiByte {
			workerLimit = 2
		} else {
			workerLimit = 1
		}
	}
	msg := fmt.Sprintf("tendisType is:%s,goroutine workerLimit is: %d", task01.TendisType, workerLimit)
	job.runtime.Logger.Info(msg)
	return workerLimit
}

// taskQueue 提取key 任务队列
func (job *TendisKeysPattern) taskQueue(chanKeyTasks chan *RedisInsKeyPatternTask,
	keyTasks []*RedisInsKeyPatternTask) (err error) {
	for _, task := range keyTasks {
		keyTask := task
		chanKeyTasks <- keyTask
	}
	close(chanKeyTasks)
	job.runtime.Logger.Info("....add taskQueue finish...")
	return

}

// keysPatternTask 消费提取key 任务
func (job *TendisKeysPattern) keysPatternTask(chanKeyTasks chan *RedisInsKeyPatternTask,
	wg *sync.WaitGroup) (err error) {

	defer wg.Done()
	for keyTask := range chanKeyTasks {
		job.runtime.Logger.Info("....GetTendisKeys job...")
		// 获取key
		keyTask.GetTendisKeys()
		if keyTask.Err != nil {
			job.Err = fmt.Errorf("GetTendisKeys err:%v", keyTask.Err)
			return job.Err
		}

		if keyTask.TendisType == consts.TendisTypeTendisplusInsance {
			// 合并 kvstore keys临时文件
			keyTask.mergeTendisplusDbFile()
			if keyTask.Err != nil {
				return keyTask.Err
			}
		}

		if job.params.IsKeysToBeDel {
			keyTask.DelKeysRateLimitV2()
			if keyTask.Err != nil {
				job.Err = fmt.Errorf(" DelKeysRateLimitV2 err:%v", keyTask.Err)
				return job.Err
			}

		}

		// 上传keys文件
		keyTask.TransferToBkrepo()
		if keyTask.Err != nil {
			return keyTask.Err
		}

	}

	job.runtime.Logger.Info("....keysPatternTask  goroutine finish...")
	return

}

// ClearFilesNDaysAgo 清理目录下 N天前更新的文件
func (job *TendisKeysPattern) ClearFilesNDaysAgo(dir string, nDays int) {
	if dir == "" || dir == "/" {
		return
	}
	clearCmd := fmt.Sprintf(`cd %s && find ./ -mtime +%d -exec rm -f {} \;`, dir, nDays)
	job.runtime.Logger.Info("clear %d day cmd:%s", nDays, clearCmd)
	util.RunLocalCmd("bash", []string{"-c", clearCmd}, "", nil, 10*time.Minute)
}

// getSafeRegexPattern 安全获取正则
func (task *RedisInsKeyPatternTask) getSafeRegexPattern(keyRegex string) (shellGrepPattern string) {
	if keyRegex == "" {
		shellGrepPattern = ""
		return
	}
	if keyRegex == "*" || keyRegex == ".*" || keyRegex == "^.*$" {
		shellGrepPattern = ".*"
		return
	}
	scanner := bufio.NewScanner(strings.NewReader(keyRegex))
	for scanner.Scan() {
		tmpPattern := scanner.Text()
		if tmpPattern == "" {
			continue
		}
		regPartten := tmpPattern
		regPartten = strings.ReplaceAll(regPartten, "|", "\\|")
		regPartten = strings.ReplaceAll(regPartten, ".", "\\.")
		regPartten = strings.ReplaceAll(regPartten, "*", ".*")

		if shellGrepPattern == "" {
			if strings.HasPrefix(regPartten, "^") {
				shellGrepPattern = regPartten
			} else {
				shellGrepPattern = fmt.Sprintf("^%s", regPartten)
			}
		} else {
			if strings.HasPrefix(regPartten, "^") {
				shellGrepPattern = fmt.Sprintf("%s|%s", shellGrepPattern, regPartten)
			} else {
				shellGrepPattern = fmt.Sprintf("%s|^%s", shellGrepPattern, regPartten)
			}
		}
	}
	msg := fmt.Sprintf("trans input partten:[%s] to regex partten:[%s]", keyRegex, shellGrepPattern)
	task.runtime.Logger.Info(msg)
	if err := scanner.Err(); err != nil {
		task.Err = fmt.Errorf("getSafeRegexPattern scanner.Err:%v,inputPattern:%s", err, keyRegex)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	return shellGrepPattern
}

// setResultFile 设置keys文件名
func (task *RedisInsKeyPatternTask) setResultFile() {
	task.ResultFile = filepath.Join(task.SaveDir, fmt.Sprintf("%s.%s_%d.keys", task.BkBizID, task.IP, task.Port))
}

// GetRedisShakeBin 获取redis-shake工具
func (task *RedisInsKeyPatternTask) GetRedisShakeBin(fetchLatest bool) (bool, error) {
	if task.TendisType == "" {
		task.redisCli.GetTendisType()
		if task.Err != nil {
			return false, task.Err
		}
	}
	if task.TendisType != consts.TendisTypeRedisInstance {
		task.Err = fmt.Errorf("TendisType != consts.TendisTypeRedisInstance")
		return false, task.Err
	}
	shakeTool := "redis-shake"
	task.RedisShakeTool = filepath.Join(task.SaveDir, shakeTool)
	// flow 里下发到指定目录 ,检查下发是否成功
	_, err := os.Stat(task.RedisShakeTool)
	if err != nil && os.IsNotExist(err) {
		task.Err = fmt.Errorf("获取redis-shake失败,请检查是否下发成功:err:%v", err)
		task.runtime.Logger.Error(task.Err.Error())
		return false, task.Err
	}
	util.LocalDirChownMysql(task.RedisShakeTool)
	err = os.Chmod(task.RedisShakeTool, 0755)
	if err != nil {
		task.Err = fmt.Errorf("RedisShakeTool加可执行权限失败:err:%v", err)
		return false, task.Err
	}

	return true, nil
}

// GetLdbTendisTool 获取ldb_tendisplus工具
func (task *RedisInsKeyPatternTask) GetLdbTendisTool(fetchLatest bool) (bool, error) {

	if task.TendisType == "" {
		task.redisCli.GetTendisType()
		if task.Err != nil {
			return false, task.Err
		}
	}

	if task.TendisType != consts.TendisTypeTendisplusInsance {
		task.Err = fmt.Errorf("TendisType != consts.TendisTypeTendisplusInsance")
		return false, task.Err
	}
	ldbTendisTool := "ldb_tendisplus"
	task.LdbTendisTool = filepath.Join(task.SaveDir, ldbTendisTool)
	task.runtime.Logger.Info("Get ldb_tendisplus Tool")
	_, err := os.Stat(task.LdbTendisTool)
	if err != nil && os.IsNotExist(err) {
		task.Err = fmt.Errorf("ldb_tendisplus,请检查是否下发成功:err:%v", err)
		task.runtime.Logger.Error(task.Err.Error())
		return false, task.Err
	}
	util.LocalDirChownMysql(task.LdbTendisTool)
	err = os.Chmod(task.LdbTendisTool, 0755)
	if err != nil {
		task.Err = fmt.Errorf("LdbTendisTool加可执行权限失败:err:%v", err)
		return false, task.Err
	}
	task.runtime.Logger.Info("Get ldb_tendisplus Tool success")

	return true, nil
}

// tendisplusAllKeys 获取tendisplus keys
func (task *RedisInsKeyPatternTask) tendisplusAllKeys() {
	task.GetLdbTendisTool(false)
	if task.Err != nil {
		return
	}
	var kvstorecount string
	kvstorecount, task.Err = task.redisCli.GetKvstoreCount()
	if task.Err != nil {
		task.Err = fmt.Errorf("tendisplusAllKeys GetKvstoreCount Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	task.runtime.Logger.Info("kvstorecount:%s", kvstorecount)
	kvstorecounts, err := strconv.Atoi(kvstorecount)
	if err != nil {
		errMsg := fmt.Sprintf("%s:%d kvstorecount  string to int failed err:%v", task.IP, task.Port, task.Err)
		task.runtime.Logger.Error(errMsg)
	}
	for db := 0; db < kvstorecounts; db++ {
		task.getTendisPlusDBKeys(db)
		if task.Err != nil {
			errMsg := fmt.Sprintf("get %s_%d_%d keys failed,err:%v", task.IP, task.Port, db, task.Err)
			task.runtime.Logger.Error(errMsg)
			return
		}
		Msg := fmt.Sprintf("get %s_%d_%d keys success", task.IP, task.Port, db)
		task.runtime.Logger.Info(Msg)
		task.getTargetKeysByPartten(db)
		if task.Err != nil {
			errMsg := fmt.Sprintf("grep pattern from %s_%d_%d.keys failed,err:%v", task.IP, task.Port, db, task.Err)
			task.runtime.Logger.Error(errMsg)
			return
		}
		Msg = fmt.Sprintf("grep pattern from %s_%d_%d keys success", task.IP, task.Port, db)
		task.runtime.Logger.Info(Msg)

	}
}

// getTendisPlusDBKeys 获取tendisplus db keys
func (task *RedisInsKeyPatternTask) getTendisPlusDBKeys(db int) {
	task.KeysFile = filepath.Join(task.SaveDir, fmt.Sprintf("%s.%s_%d_%d.keys", task.BkBizID, task.IP, task.Port, db))
	getKeysCmd := fmt.Sprintf("%s --db=%s/%d tscan > %s", task.LdbTendisTool, task.DataDir, db, task.KeysFile)
	task.runtime.Logger.Info("tendisplus getkeys command:%s", getKeysCmd)

	maxTimes := 5
	var cmdRet string
	var err error
	for maxTimes > 0 {
		maxTimes--
		task.Err = nil
		cmdRet, err = util.RunLocalCmd("bash", []string{"-c", getKeysCmd}, "", nil, 24*time.Hour)
		if err != nil {
			task.Err = err
			task.runtime.Logger.Error(task.Err.Error())
			continue
		}
		if cmdRet != "" {
			task.Err = errors.New(cmdRet)
			task.runtime.Logger.Error(task.Err.Error())
			continue
		}

		msg := fmt.Sprintf("tendisplus db:%d AllKeys get keysFile:%s success", db, task.KeysFile)
		task.runtime.Logger.Info(msg)
		break
	}
	if task.Err != nil {
		msg := fmt.Sprintf("tendisplus db:%d AllKeys get :%s,err:%v", db, getKeysCmd, err)
		task.runtime.Logger.Error(msg)
		return
	}

}

// getTargetKeysByPartten 按正则匹配key
func (task *RedisInsKeyPatternTask) getTargetKeysByPartten(db int) {
	task.ResultFile = filepath.Join(task.SaveDir, fmt.Sprintf("result.%s.%s_%d_%d.keys", task.BkBizID, task.IP, task.Port,
		db))
	var grepExtra = ""
	grepPattern := task.getSafeRegexPattern(task.KeyWhiteRegex)
	if task.Err != nil {
		return
	}
	if grepPattern != "" && grepPattern != ".*" {
		grepExtra = fmt.Sprintf(` | { grep -E %q || true; }`, grepPattern)
	}
	grepPattern = task.getSafeRegexPattern(task.KeyBlackRegex)
	if task.Err != nil {
		return
	}

	// 过滤掉节点心跳检测数据
	masterHeartbeat := fmt.Sprintf("%s_%s:heartbeat", task.MasterIP, task.MasterPort)
	slaveHeartbeat := ""
	if task.MasterIP != task.IP {
		slaveHeartbeat = fmt.Sprintf("|^%s_%d:heartbeat", task.IP, task.Port)
	}
	DbhaAgent := fmt.Sprintf("dbha:agent:%s", task.MasterIP)
	if grepPattern == "" {
		grepPattern = fmt.Sprintf("^%s|^%s%s", masterHeartbeat, DbhaAgent, slaveHeartbeat)

	} else {
		grepPattern = fmt.Sprintf("%s|^%s|^%s%s", grepPattern, masterHeartbeat, DbhaAgent, slaveHeartbeat)

	}

	if grepPattern != "" && grepPattern != ".*" {
		grepExtra = fmt.Sprintf(` %s | { grep -vE %q || true; }`, grepExtra, grepPattern)
	}
	grepCmd := fmt.Sprintf(`awk '{ print $3}' %s %s > %s`, task.KeysFile, grepExtra, task.ResultFile)
	_, err := util.RunLocalCmd("bash", []string{"-c", grepCmd}, "", nil, 48*time.Hour)
	if err != nil {
		task.Err = fmt.Errorf("grepCmd:%s err:%v", grepCmd, err)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	task.runtime.Logger.Info("tendisplusAllKeys grepCmd:%s success", grepCmd)

}

// mergeTendisplusDbFile 合并节点dbkeys 并删除kvstore keys临时文件
func (task *RedisInsKeyPatternTask) mergeTendisplusDbFile() {
	task.runtime.Logger.Info("开始合并db key提取结果")
	mergeFile := filepath.Join(task.SaveDir, fmt.Sprintf("%s.%s_%d.keys", task.BkBizID, task.IP, task.Port))
	// 再次检查是否存在相同的keys文件，必须保证不存在，不然结果会累加
	_, err := os.Stat(mergeFile)
	if err == nil {
		err = os.Remove(mergeFile)
		if err != nil {
			errMsg := fmt.Sprintf("再次检查是否存在相同的keys文件且删除失败:%s", mergeFile)
			task.runtime.Logger.Error(errMsg)
		}

	}
	mergeCmd := fmt.Sprintf(`cd %s 
	flock -x -w 600 ./lock -c  'cat result.%s.%s_%d_* >> %s '`,
		task.SaveDir, task.BkBizID, task.IP, task.Port, mergeFile)
	_, err = util.RunLocalCmd("bash", []string{"-c", mergeCmd}, "", nil, 1*time.Hour)

	if err != nil {
		task.Err = fmt.Errorf("mergeCmd:%s err:%v", mergeCmd, err)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	msg := fmt.Sprintf("key db 提取结果合并命令:%s", mergeCmd)
	task.runtime.Logger.Info(msg)
	task.ResultFile = mergeFile
	task.ClearTmpKeysFile()
	task.ClearTmpResultFile()
	if task.Err != nil {
		return
	}

}

// getSSDLdbTool 获取SSD ldb工具
func (task *RedisInsKeyPatternTask) getSSDLdbTool(fetchLatest bool) (bool, error) {

	if task.TendisType == "" {
		task.redisCli.GetTendisType()
		if task.Err != nil {
			return false, task.Err
		}
	}

	if task.TendisType != consts.TendisTypeTendisSSDInsance {
		task.Err = fmt.Errorf("TendisType != consts.TendisTypeTendisSSDInsance")
		return false, task.Err
	}

	ldbTool := "ldb_tendisssd"
	ldbTool513 := "ldb_with_len.5.13"
	if task.Version == "" {
		// 获取 redis_version 以区分ssd版本差异，决定使用不同的ldb工具
		task.Version, task.Err = task.redisCli.GetTendisVersion()
		if task.Err != nil {
			task.Err = fmt.Errorf("getSSDLdbTool GetTendisVersion Err:%v", task.Err)
			task.runtime.Logger.Error(task.Err.Error())
			return false, task.Err
		}
	}
	task.runtime.Logger.Info("getSSDLdbTool GetTendisVersion:%s", task.Version)

	baseVersion, subVersion, err := util.VersionParse(task.Version)
	if err != nil {
		task.Err = err
		task.runtime.Logger.Error(task.Err.Error())
		return false, task.Err
	}
	msg := fmt.Sprintf("getSSDLdbTool tendis:%s#%d baseVersion:%d subVersion:%d", task.IP, task.Port, baseVersion,
		subVersion)
	task.runtime.Logger.Info(msg)
	if task.TendisType == consts.TendisTypeTendisSSDInsance && baseVersion == 2008017 && subVersion > 1002016 {
		if task.WithExpiredKeys == true {
			// 提取的key包含已过期的key
			ldbTool = filepath.Join(task.SaveDir, ldbTool513)
		} else {
			// 提取的key不包含已过期的key
			ldbTool = filepath.Join(task.SaveDir, ldbTool)
		}
	} else {
		// tendis ssd低版本
		// 此时使用ldb无法支持 --without_expired 参数
		task.WithExpiredKeys = true
	}

	_, err = os.Stat(ldbTool)
	if err != nil {
		task.Err = fmt.Errorf("%s %v", ldbTool, err)
		task.runtime.Logger.Error(task.Err.Error())
		return false, task.Err
	}

	err = os.Chmod(ldbTool, 0755)
	if err != nil {
		task.Err = fmt.Errorf("getSSDLdbTool ldbTool:%s 加可执行权限失败:err:%v", ldbTool, err)
		return false, task.Err
	}
	task.LdbTendisTool = ldbTool
	task.runtime.Logger.Info("getSSDLdbTool success,ldbTool:%s", task.LdbTendisTool)

	return true, nil
}

// tendisSSDAllKeys 获取tendisSSD  keys
func (task *RedisInsKeyPatternTask) tendisSSDAllKeys() {
	task.getSSDLdbTool(false)
	if task.Err != nil {
		return
	}
	task.KeysFile = filepath.Join(task.SaveDir, fmt.Sprintf("%s_%d.keys", task.IP, task.Port))
	// 设置最后的文件名格式
	task.setResultFile()
	if task.Err != nil {
		return
	}
	var getKeysCmd string
	rocksdbFile := filepath.Join(task.DataDir, "rocksdb")
	_, err := os.Stat(rocksdbFile)
	if os.IsNotExist(err) {
		task.runtime.Logger.Error("tendisSSDAllKeys", fmt.Sprintf("%s not exists", rocksdbFile))
		return
	}

	if task.WithExpiredKeys == false {
		segStart := ""
		segEnd := ""
		if task.SegStart >= 0 && task.SegEnd > 0 {
			segStart = fmt.Sprintf(" --start_segment=%d ", task.SegStart)
			segEnd = fmt.Sprintf(" --end_segment=%d ", task.SegEnd)
		}
		getKeysCmd = fmt.Sprintf(
			"export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/usr/local/redis/bin/deps;%s --db=%s --without_expired %s %s scan > %s",
			task.LdbTendisTool, rocksdbFile, segStart, segEnd, task.KeysFile)
	} else {
		getKeysCmd = fmt.Sprintf("export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/usr/local/redis/bin/deps;%s --db=%s scan > %s",
			task.LdbTendisTool, rocksdbFile, task.KeysFile)
	}
	task.runtime.Logger.Info("getKeysCmd command:%s", getKeysCmd)

	maxTimes := 5
	var cmdRet string
	for maxTimes > 0 {
		maxTimes--
		task.Err = nil
		cmdRet, err = util.RunLocalCmd("bash", []string{"-c", getKeysCmd}, "", nil, 24*time.Hour)
		if err != nil {
			task.Err = err
			task.runtime.Logger.Warn("tendisSSDAllKeys ldb fail,err:%v,sleep 60s and retry ...", task.Err)
			time.Sleep(1 * time.Minute)
			continue
		}
		if cmdRet != "" {
			task.Err = errors.New(cmdRet)
			task.runtime.Logger.Warn("tendisSSDAllKeys ldb fail,err:%v,sleep 60s and retry ...", task.Err)
			time.Sleep(1 * time.Minute)
			continue
		}
		task.runtime.Logger.Info("tendisSSDAllKeys get keysFile:%s success", task.KeysFile)
		break
	}
	if task.Err != nil {
		task.runtime.Logger.Error(task.Err.Error())
		return
	}

	var grepExtra string = ""
	grepPattern := task.getSafeRegexPattern(task.KeyWhiteRegex)
	if task.Err != nil {
		return
	}
	if grepPattern != "" && grepPattern != ".*" {
		grepExtra = fmt.Sprintf(` | { grep -E %q || true; }`, grepPattern)
	}
	grepPattern = task.getSafeRegexPattern(task.KeyBlackRegex)
	if task.Err != nil {
		return
	}
	if grepPattern != "" && grepPattern != ".*" {
		grepExtra = fmt.Sprintf(` %s | { grep -vE %q || true; }`, grepExtra, grepPattern)
	}

	grepCmd := fmt.Sprintf(`awk '{ print $3}' %s %s > %s`, task.KeysFile, grepExtra, task.ResultFile)
	task.runtime.Logger.Info("grepCommand:%s", grepCmd)

	cmdRet, err = util.RunLocalCmd("bash", []string{"-c", grepCmd}, "", nil, 48*time.Hour)
	if err != nil {
		task.Err = err
		return
	}
	task.runtime.Logger.Info("grepCommand:%s success", grepCmd)
	util.RunLocalCmd("bash", []string{"-c", fmt.Sprintf("chown -R mysql.mysql %s", task.SaveDir)}, "", nil, 10*time.Second)
}

// tendisCacheAllKeys 获取所有key
// NOCC:golint/fnsize(设计如此)
func (task *RedisInsKeyPatternTask) tendisCacheAllKeys() {
	task.GetRedisShakeBin(false)
	if task.Err != nil {
		return
	}

	value := `conf.version = 1
id = {{SHAKE_ID}}
log.level = info
log.file ={{LOG_FILE}}
pid_path={{PID_PATH}}
http_profile = {{HTTP_PROFIILE}}
system_profile = {{SYSTEM_PROFILE}}
parallel = 8
source.rdb.input =  {{RDB_FULL_PATH}}
source.rdb.start_segment={{START_SEGMENT}}
source.rdb.end_segment={{END_SEGMENT}}
filter.key.whitelist = {{KEY_WHITELIST}}
filter.key.blacklist = {{KEY_BLACKLIST}}
filter.db.whitelist = 0
filter.db.blacklist =
decode_only_print_keyname = true
decode_without_expired_keys = true
target.rdb.output = {{RESULT_FULL_PATH}}`
	templateFile := filepath.Join(task.SaveDir, fmt.Sprintf("shake.%d.conf", task.Port))
	shakeID := fmt.Sprintf("redis-shake-%d", task.Port)
	logFile := filepath.Join(task.SaveDir, fmt.Sprintf("shake.%d.log", task.Port))
	pidPath := filepath.Join(task.SaveDir, "pids")
	httpProfile := task.Port + 500
	systemProfile := task.Port + 5000
	rdbFullPath := fmt.Sprintf("%s/dump.rdb", task.DataDir)
	segStart := -1
	segEnd := -1
	if task.SegStart != 0 && task.SegEnd != 0 {
		segStart = task.SegStart
		segEnd = task.SegEnd
	}
	whitePattern := task.getSafeRegexPattern(task.KeyWhiteRegex)
	if whitePattern == ".*" {
		whitePattern = ""
	}
	blackPattern := task.getSafeRegexPattern(task.KeyBlackRegex)
	if blackPattern == ".*" {
		blackPattern = ""
	}
	task.setResultFile()
	if task.Err != nil {
		return
	}
	value = strings.ReplaceAll(value, "{{SHAKE_ID}}", shakeID)
	value = strings.ReplaceAll(value, "{{LOG_FILE}}", logFile)
	value = strings.ReplaceAll(value, "{{PID_PATH}}", pidPath)
	value = strings.ReplaceAll(value, "{{HTTP_PROFIILE}}", strconv.Itoa(httpProfile))
	value = strings.ReplaceAll(value, "{{SYSTEM_PROFILE}}", strconv.Itoa(systemProfile))
	value = strings.ReplaceAll(value, "{{RDB_FULL_PATH}}", rdbFullPath)
	value = strings.ReplaceAll(value, "{{START_SEGMENT}}", strconv.Itoa(segStart))
	value = strings.ReplaceAll(value, "{{END_SEGMENT}}", strconv.Itoa(segEnd))
	value = strings.ReplaceAll(value, "{{KEY_WHITELIST}}", whitePattern)
	value = strings.ReplaceAll(value, "{{KEY_BLACKLIST}}", blackPattern)
	value = strings.ReplaceAll(value, "{{RESULT_FULL_PATH}}", task.ResultFile)
	pidFile := filepath.Join(pidPath, shakeID+".pid")
	if _, err := os.Stat(pidFile); err == nil {
		task.clearPidFile(pidFile)
		task.runtime.Logger.Info("tendisCacheAllKeys: clearPidFile %s success", pidFile)
	}

	err := ioutil.WriteFile(templateFile, []byte(value), 0755)
	if err != nil {
		task.Err = fmt.Errorf("ioutil.WriteFile fail,file:%s,err:%v", templateFile, err)
		return
	}
	getKeyCmdNew := fmt.Sprintf("%s -conf=%s -type=decode", task.RedisShakeTool, templateFile)
	task.runtime.Logger.Info("getKey command:%s", getKeyCmdNew)

	var cmdRet string
	var msg string
	maxRetryTimes := 5
	for maxRetryTimes > 0 {
		maxRetryTimes--
		err = nil
		cmdRet, err = util.RunLocalCmd("bash", []string{"-c", getKeyCmdNew}, "", nil, 24*time.Hour)
		if err != nil && (strings.Contains(cmdRet, "address already in use") || strings.Contains(err.Error(),
			"address already in use")) {
			msg = fmt.Sprintf("command:%s port address already in use,retry...", getKeyCmdNew)
			task.runtime.Logger.Error(msg)
			value = strings.ReplaceAll(value, fmt.Sprintf("http_profile = %d", httpProfile), fmt.Sprintf("http_profile = %d",
				httpProfile+500))
			value = strings.ReplaceAll(value, fmt.Sprintf("system_profile = %d", systemProfile),
				fmt.Sprintf("system_profile = %d", systemProfile+500))
			httpProfile += 500
			systemProfile += 500
			ioutil.WriteFile(templateFile, []byte(value), 0755)
			continue
		} else if err != nil {
			msg = fmt.Sprintf("command:%s err:%v,retry...", getKeyCmdNew, err)
			task.runtime.Logger.Error(msg)

			time.Sleep(5 * time.Second)
			continue
		}
		break
	}
	if err != nil {
		task.Err = fmt.Errorf("command:%s failed,err:%v,cmdRet:%s", getKeyCmdNew, err, cmdRet)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	task.runtime.Logger.Info("tendisCacheAllKeys :run success command:%s", getKeyCmdNew)
	task.ResultFile = task.ResultFile + ".0"
	return

}

// clearPidFile 删除本地redis-shake pid文件
func (task *RedisInsKeyPatternTask) clearPidFile(pidFile string) {
	pidFile = strings.TrimSpace(pidFile)
	if pidFile == "" {
		return
	}
	if strings.Contains(pidFile, "shake") == false {
		// 如果pidFile 为空,则下面命令非常危险
		return
	}
	rmCmd := fmt.Sprintf("cd  %s && rm -rf %s 2>/dev/null", filepath.Dir(pidFile), filepath.Base(pidFile))
	task.runtime.Logger.Info(rmCmd)

	util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 10*time.Minute)
}

// GetTendisKeys 获取tendis(cache/tendisplus/tendisSSD)的keys文件
func (task *RedisInsKeyPatternTask) GetTendisKeys() {
	// 先获取锁,然后获取key
	lockFile := filepath.Join(task.SaveDir, fmt.Sprintf("lock.%s.%d", task.IP, task.Port))

	msg := fmt.Sprintf("try to get filelock:%s,addr:%s", lockFile, task.Addr())
	task.runtime.Logger.Info(msg)

	flock := flock.New(lockFile)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Hour)
	defer cancel()
	locked, err := flock.TryLockContext(ctx, 10*time.Second)
	if err != nil {
		task.Err = fmt.Errorf("try to get filelock fail,err:%v,addr:%s", err, task.Addr())
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	if locked == false {
		return
	}
	defer flock.Unlock()

	msg = fmt.Sprintf("try to get filelock:%s success,starting getTendisKeys,addr:%s", lockFile, task.Addr())
	task.runtime.Logger.Info(msg)

	task.GetMasterData()
	if task.Err != nil {
		return
	}

	// 如果key模式(白名单)中所有key都要求精确匹配,则无需去提取
	if task.IsAllKeyNamesInWhiteRegex() {
		task.getKeysFromRegex()
		return
	}

	if task.TendisType == consts.TendisTypeRedisInstance {
		task.GetInsFullData()
		if task.Err != nil {
			return
		}
		task.tendisCacheAllKeys()
	} else if task.TendisType == consts.TendisTypeTendisplusInsance {
		task.tendisplusAllKeys()
	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
		task.tendisSSDAllKeys()
	} else {
		task.Err = fmt.Errorf("unknown db type:%s,ip:%s,port:%d", task.TendisType, task.IP, task.Port)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
}

// getKeysFromRegex 根据正则获取key
func (task *RedisInsKeyPatternTask) getKeysFromRegex() {
	task.setResultFile()
	file, err := os.OpenFile(task.ResultFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0755)
	if err != nil {
		task.Err = fmt.Errorf("getKeysFromRegex os.OpenFile fail,err:%v,resultFile:%s", err, task.ResultFile)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	datawriter := bufio.NewWriter(file)
	defer file.Close()
	defer datawriter.Flush()

	scanner := bufio.NewScanner(strings.NewReader(task.KeyWhiteRegex))
	for scanner.Scan() {
		tmpPattern := scanner.Text()
		if tmpPattern == "" {
			continue
		}
		tmpPattern = strings.TrimPrefix(tmpPattern, "^")
		tmpPattern = strings.TrimSuffix(tmpPattern, "$")
		tmpPattern = strings.TrimSpace(tmpPattern)
		if tmpPattern == "" {
			continue
		}
		datawriter.WriteString(tmpPattern + "\n")
	}
	if err := scanner.Err(); err != nil {
		task.Err = fmt.Errorf("getKeysFromRegex scanner.Err:%v,KeyWhiteRegex:%s", err, task.KeyWhiteRegex)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
}

// IsAllKeyNamesInWhiteRegex 是否所有key名都已在 keyWhiteRegex 中,也就是 keyWhiteRegex中每一行都是 ^$包裹的,如 ^hello$、^world$
func (task *RedisInsKeyPatternTask) IsAllKeyNamesInWhiteRegex() bool {
	lines := strings.Split(task.KeyWhiteRegex, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		if !strings.HasPrefix(line, "^") {
			return false
		}
		if !strings.HasSuffix(line, "$") {
			return false
		}
	}
	return true
}

// TransferToBkrepo 上传keys文件到蓝盾制品库
func (task *RedisInsKeyPatternTask) TransferToBkrepo() {

	filepath := task.ResultFile
	str1 := strings.Split(filepath, "/")
	filename := str1[len(str1)-1]
	targetURL := fmt.Sprintf(task.FileServer.URL + "/generic/" + task.FileServer.Project + "/" + task.FileServer.Bucket +
		task.Path + "/" + filename)
	response, err := util.UploadFile(filepath, targetURL, task.FileServer.Username, task.FileServer.Password)
	if err != nil {
		err = fmt.Errorf("上传文件 %s 到 %s 失败:%v", filepath, targetURL, err)
		task.runtime.Logger.Error(err.Error())
		task.Err = err
	}
	bodyBytes, err := ioutil.ReadAll(response.Body)
	if err != nil {
		task.runtime.Logger.Error(err.Error())
		task.Err = err
	}
	resmsg := fmt.Sprintf("response  %s", bodyBytes)
	task.runtime.Logger.Info(resmsg)

}

// ClearTmpKeysFile 删除本地keys file
func (task *RedisInsKeyPatternTask) ClearTmpKeysFile() {
	if strings.Contains(task.KeysFile, task.IP) == false {
		return
	}
	rmCmd := fmt.Sprintf("cd %s && rm result.%s.%s_%d_*", task.SaveDir,
		task.BkBizID, task.IP, task.Port)
	task.runtime.Logger.Info("ClearKeysFile: %s", rmCmd)
	_, err := util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 10*time.Minute)
	if err != nil {
		err = fmt.Errorf("删除本地keys file失败,err:%v", err)
		task.runtime.Logger.Error(err.Error())
		task.Err = err
		return
	}

}

// ClearTmpResultFile 删除本地result file
func (task *RedisInsKeyPatternTask) ClearTmpResultFile() {
	if strings.Contains(task.ResultFile, task.IP) == false {
		return
	}
	rmCmd := fmt.Sprintf("cd %s && rm %s.%s_%d_*", task.SaveDir,
		task.BkBizID, task.IP, task.Port)
	task.runtime.Logger.Info("ClearResultFile: %s", rmCmd)
	_, err := util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 10*time.Minute)
	if err != nil {
		err = fmt.Errorf("删除本地result file失败,err:%v", err)
		task.runtime.Logger.Error(err.Error())
		task.Err = err
		return
	}
}

// RedisInsTask redis 原子任务
type RedisInsTask struct {
	BkBizID    string               `json:"bk_biz_id"`
	Domain     string               `json:"domain"`
	IP         string               `json:"ip"`
	Port       int                  `json:"port"`
	Password   string               `json:"password"`
	TendisType string               `json:"tendis_type"`
	Version    string               `json:"version"` // 区分ssd版本差异，需要使用对应的ldb工具
	Role       string               `json:"role"`
	DataDir    string               `json:"data_dir"`
	DataSize   uint64               `json:"data_size"` // 设置并发度
	SaveDir    string               `json:"save_dir"`
	redisCli   *myredis.RedisClient `json:"-"` // NOCC:vet/vet(设计如此)
	runtime    *jobruntime.JobGenericRuntime
	Err        error `json:"-"`
}

// NewRedisInsTask new
func NewRedisInsTask(bkBizID, domain, ip string, port int, password, saveDir string,
	runtime *jobruntime.JobGenericRuntime) (task *RedisInsTask, err error) {
	return &RedisInsTask{
		BkBizID:  bkBizID,
		Domain:   domain,
		IP:       ip,
		Port:     port,
		Password: password,
		SaveDir:  saveDir,
		runtime:  runtime,
	}, nil

}

// Addr string
func (task *RedisInsTask) Addr() string {
	return task.IP + ":" + strconv.Itoa(task.Port)
}

// newConnect 获取节点相关信息
func (task *RedisInsTask) newConnect() error {
	task.redisCli, task.Err = myredis.NewRedisClient(task.Addr(), task.Password, 0, consts.TendisTypeRedisInstance)
	if task.Err != nil {
		task.Err = fmt.Errorf("newConnect NewRedisClient Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return task.Err
	}
	task.Role, task.Err = task.redisCli.GetRole()
	if task.Err != nil {
		task.Err = fmt.Errorf("newConnect GetRole Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return task.Err
	}
	task.DataDir, task.Err = task.redisCli.GetDir()
	if task.Err != nil {
		task.Err = fmt.Errorf("newConnect GetDir Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return task.Err
	}
	task.TendisType, task.Err = task.redisCli.GetTendisType()
	if task.Err != nil {
		task.Err = fmt.Errorf("newConnect GetTendisType Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return task.Err
	}
	// 获取 redis_version 以区分ssd版本差异，决定使用不同的ldb工具
	task.Version, task.Err = task.redisCli.GetTendisVersion()
	if task.Err != nil {
		task.Err = fmt.Errorf("newConnect GetTendisVersion Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return task.Err
	}

	// 获取数据量大小
	if task.TendisType == consts.TendisTypeRedisInstance {
		task.DataSize, task.Err = task.redisCli.RedisInstanceDataSize()
	} else if task.TendisType == consts.TendisTypeTendisplusInsance {
		task.DataSize, task.Err = task.redisCli.TendisplusDataSize()
	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
		task.DataSize, task.Err = task.redisCli.TendisSSDDataSize()
	}
	if task.Err != nil {
		task.Err = fmt.Errorf("newConnect  Err:%v", task.Err)
		task.runtime.Logger.Error(task.Err.Error())
		return task.Err
	}
	return nil
}

// RedisInsBgsave 执行bgsave，并等待完成
func (task *RedisInsTask) RedisInsBgsave() {
	nowtime := time.Now().Local().Format(consts.FilenameTimeLayout)
	mes := fmt.Sprintf("%s-redis-%s-%s-%d-%s.rdb",
		task.BkBizID, task.Role, task.IP, task.Port, nowtime)
	task.runtime.Logger.Info(mes)
	task.Err = task.redisCli.BgSaveAndWaitForFinish()
	if task.Err != nil {
		err := fmt.Sprintf("执行bgsave失败:err:%v", task.Err)
		task.runtime.Logger.Error(err)
	}
}

// ConnRedis 连接redis
func (task *RedisInsTask) ConnRedis() {
	redisAddr := fmt.Sprintf("%s:%d", task.IP, task.Port)
	task.redisCli, task.Err = myredis.NewRedisClient(redisAddr, task.Password, 0, consts.TendisTypeRedisInstance)
	if task.Err != nil {
		return
	}
	msg := fmt.Sprintf("%s:%d 连接正常", task.IP, task.Port)
	task.runtime.Logger.Info(msg)
}

// DisconneRedis 与redis断开连接
func (task *RedisInsTask) DisconneRedis() {
	if task.redisCli != nil {
		task.redisCli.Close()
	}
	msg := fmt.Sprintf("%s:%d 断开连接", task.IP, task.Port)
	task.runtime.Logger.Info(msg)
}

// GetMasterData 获取master登录信息
func (task *RedisInsKeyPatternTask) GetMasterData() {

	msg := fmt.Sprintf("redis:%s#%d get master data ...", task.IP, task.Port)
	task.runtime.Logger.Info(msg)
	task.ConnRedis()
	if task.Err != nil {
		return
	}

	replInfo, err := task.redisCli.Info("replication")
	if err != nil {
		task.Err = err
		return
	}

	role, _ := replInfo["role"]
	if role == consts.RedisSlaveRole {
		task.MasterAddr = fmt.Sprintf("%s:%s", replInfo["master_host"], replInfo["master_port"])
		confData, err1 := task.redisCli.ConfigGet("masterauth")
		if err != nil {
			task.Err = err1
			return
		}
		task.MasterAuth = confData["masterauth"]
		task.MasterIP = replInfo["master_host"]
		task.MasterPort = replInfo["master_port"]
	} else {
		task.MasterAddr = fmt.Sprintf("%s:%d", task.IP, task.Port)
		task.MasterAuth = task.Password
		task.MasterIP = task.IP
		task.MasterPort = strconv.Itoa(task.Port)
	}

	// msg = fmt.Sprintf("redisMaster:%s masterAuth:%s", task.MasterAddr, task.MasterAuth)
	msg = fmt.Sprintf("redisMaster:%s masterAuth:xxxxxx", task.MasterAddr)
	task.runtime.Logger.Info(msg)

	masterCli, err := myredis.NewRedisClient(task.MasterAddr, task.MasterAuth, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		task.Err = err
		return
	}
	defer masterCli.Close()

	return
}

// GetRedisSafeDelTool 获取安全删除key的工具
func (task *RedisInsKeyPatternTask) GetRedisSafeDelTool() (bool, error) {

	remoteSafeDelTool := "redisSafeDeleteTool"
	task.SafeDelTool = filepath.Join(task.SaveDir, remoteSafeDelTool)
	task.runtime.Logger.Info("Get redisSafeDeleteTool")
	_, err := os.Stat(task.SafeDelTool)
	if err != nil && os.IsNotExist(err) {
		task.Err = fmt.Errorf("获取redisSafeDeleteTool失败,请检查是否下发成功:err:%v", err)
		task.runtime.Logger.Error(task.Err.Error())
		return false, task.Err
	}
	util.LocalDirChownMysql(task.SafeDelTool)
	err = os.Chmod(task.SafeDelTool, 0755)
	if err != nil {
		task.Err = fmt.Errorf(" redisSafeDeleteTool 加可执行权限失败:err:%v", err)
		return false, task.Err
	}
	task.runtime.Logger.Info("Get redisSafeDeleteTool  success")

	return true, nil
}

// DelKeysRateLimitV2 对redis key执行安全删除
// NOCC:golint/fnsize(设计如此)
func (task *RedisInsKeyPatternTask) DelKeysRateLimitV2() {
	if task.IsKeysToBeDel == false {
		return
	}
	msg := fmt.Sprintf("redis:%s#%d start delete keys ...", task.IP, task.Port)
	task.runtime.Logger.Info(msg)

	task.GetMasterData()
	if task.Err != nil {
		return
	}
	task.GetRedisSafeDelTool()
	if task.Err != nil {
		return
	}

	fileData, err := os.Stat(task.ResultFile)
	if err != nil {
		task.Err = fmt.Errorf("redis:%s#%d keysPattern resultFile:%s os.stat fail,err:%v", task.IP, task.Port,
			task.ResultFile, err)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	if fileData.Size() == 0 {
		msg = fmt.Sprintf("redis:%s#%d keysPattern resultFile:%s size==%d,skip delKeys", task.IP, task.Port, task.ResultFile,
			fileData.Size())
		task.runtime.Logger.Info(msg)
		return
	}

	keyFile, err := os.Open(task.ResultFile)
	if err != nil {
		task.Err = fmt.Errorf("DelKeysRateLimit open %s fail,err:%v", task.ResultFile, err)
		task.runtime.Logger.Error(task.Err.Error())
		return
	}
	defer keyFile.Close()

	// tendisplus/tendisSSD 与 cache 删除默认速率不同
	// 这里只需要添加ssd 删除速率逻辑就好：因为都是通过工具在文件里去删除和存储类型没关系
	delRateLimit := 10000
	if task.TendisType == consts.TendisTypeTendisplusInsance {
		if task.TendisplusDeleteRate >= 10 {
			delRateLimit = task.TendisplusDeleteRate
		} else {
			delRateLimit = 3000
		}
	} else if task.TendisType == consts.TendisTypeRedisInstance {
		if task.DeleteRate >= 10 {
			delRateLimit = task.DeleteRate
		} else {
			delRateLimit = 10000
		}
	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
		if task.SsdDeleteRate >= 10 {
			delRateLimit = task.SsdDeleteRate
		} else {
			delRateLimit = 3000
		}
	}

	var errBuffer bytes.Buffer
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	bigKeyThread := 1000 // 如果hash,hlen>1000,则算big key
	threadCnt := 30
	subScanCount := 100 // hscan 中count 个数

	delCmd := fmt.Sprintf(
		// NOCC:tosa/linelength(设计如此)
		`%s bykeysfile --dbtype=standalone --redis-addr=%s --redis-password=%s --keys-file=%s --big-key-threashold=%d --del-rate-limit=%d --thread-cnt=%d --sub-scan-count=%d --without-config-cmd`,
		task.SafeDelTool, task.MasterAddr, task.MasterAuth, task.ResultFile, bigKeyThread, delRateLimit, threadCnt,
		subScanCount)
	logCmd := fmt.Sprintf(
		// NOCC:tosa/linelength(设计如此)
		`%s bykeysfile --dbtype=standalone --redis-addr=%s --redis-password=xxxxx --keys-file=%s --big-key-threashold=%d --del-rate-limit=%d --thread-cnt=%d --sub-scan-count=%d --without-config-cmd`,
		task.SafeDelTool, task.MasterAddr, task.ResultFile, bigKeyThread, delRateLimit, threadCnt, subScanCount)
	task.runtime.Logger.Info(logCmd)

	cmd := exec.CommandContext(ctx, "bash", "-c", delCmd)
	stdout, _ := cmd.StdoutPipe()
	cmd.Stderr = &errBuffer

	if err = cmd.Start(); err != nil {
		err = fmt.Errorf("DelKeysRateLimitV2 cmd.Start fail,err:%v", err)
		task.runtime.Logger.Error(err.Error())
		task.Err = err
		return
	}

	scanner := bufio.NewScanner(stdout)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		// 不断打印进度
		m := scanner.Text()
		if strings.Contains(m, `"level":"error"`) == true {
			err = errors.New(m)
			task.runtime.Logger.Info(m)
			continue
		}
		m = m + ";" + task.redisCli.Addr
		task.runtime.Logger.Info(m)
	}
	if err != nil {
		task.Err = err
		return
	}

	if err = cmd.Wait(); err != nil {
		err = fmt.Errorf("DelKeysRateLimitV2 cmd.Wait fail,err:%v", err)
		task.runtime.Logger.Error(err.Error())
		task.Err = err
		return
	}
	errStr := errBuffer.String()
	errStr = strings.TrimSpace(errStr)
	if len(errStr) > 0 {
		err = fmt.Errorf("DelKeysRateLimitV2 fail,err:%s", errStr)
		task.runtime.Logger.Error(err.Error())
		task.Err = err
		return
	}
}
