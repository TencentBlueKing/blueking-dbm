package atomredis

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
	"github.com/gofrs/flock"
	"github.com/panjf2000/ants/v2"
)

// PortAndSegment redis port & segment range
type PortAndSegment struct {
	Port         int `json:"port"`
	SegmentStart int `json:"segment_start"`
	SegmentEnd   int `json:"segment_end"`
}

// RedisDtsDataCheckAndRpaireParams 数据校验与修复参数
type RedisDtsDataCheckAndRpaireParams struct {
	common.DbToolsMediaPkg
	BkBizID     string `json:"bk_biz_id" validate:"required"`
	DtsCopyType string `json:"dts_copy_type" validate:"required"`
	// 如果本机是源redis集群的一部分,如 redis_master/redis_slave,则 ip 为本机ip;
	// 否则ip不是本机ip(针对迁移用户自建redis到dbm的情况,数据校验会下发到目的集群 proxy上执行, ip为用户自建redis_ip, 本机ip为目的集群proxy_ip)
	SrcRedisIP              string           `json:"src_redis_ip" validate:"required"`
	SrcRedisPortSegmentList []PortAndSegment `json:"src_redis_port_segmentlist" validate:"required"`
	SrcHashTag              bool             `json:"src_hash_tag"` // 源redis 是否开启 hash tag
	// redis password 而非 proxy password
	// 需用户传递 redis password原因是: 存在迁移用户自建redis到dbm的场景.
	// 此时数据校验任务 无法跑在自建的redis机器上,无法本地获取redis password
	SrcRedisPassword string `json:"src_redis_password" validate:"required"`
	// 源redis 域名 or proxy ip等,如果源redis是一个proxy+redis主从,这里就是集群域名 or proxy ip
	SrcClusterAddr     string `json:"src_cluster_addr" validate:"required"`
	DstClusterAddr     string `json:"dst_cluster_addr" validate:"required"`
	DstClusterPassword string `json:"dst_cluster_password" validate:"required"`
	KeyWhiteRegex      string `json:"key_white_regex" validate:"required"`
	KeyBlackRegex      string `json:"key_black_regex"`
	// Concurrency 并发度(同时对多少个redis实例做数据校验/修复),不传或<=0时使用默认值(2)
	// 运行过程中可通过并发度控制文件动态调整,见 getConcurrencyCtrlFile
	Concurrency int `json:"concurrency"`
}

// defaultDtsDataCheckRepairConcurrency 数据校验/修复默认并发度
const defaultDtsDataCheckRepairConcurrency = 2

// concurrencyCtrlFilePollInterval 并发度控制文件轮询间隔
const concurrencyCtrlFilePollInterval = 5 * time.Second

// GetConcurrency 获取并发度,未传或非法时使用默认值
func (params *RedisDtsDataCheckAndRpaireParams) GetConcurrency() int {
	if params.Concurrency <= 0 {
		return defaultDtsDataCheckRepairConcurrency
	}
	return params.Concurrency
}

// RedisDtsDataCheck dts 数据校验
type RedisDtsDataCheck struct {
	atomJobName    string
	saveDir        string
	dataCheckTool  string
	dataRepairTool string
	params         RedisDtsDataCheckAndRpaireParams
	runtime        *jobruntime.JobGenericRuntime
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisDtsDataCheck)(nil)

// NewRedisDtsDataCheck new
func NewRedisDtsDataCheck() jobruntime.JobRunner {
	return &RedisDtsDataCheck{}
}

// Init 初始化
func (job *RedisDtsDataCheck) Init(m *jobruntime.JobGenericRuntime) error {
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
	// ports 和 inst_num 不能同时为空
	if len(job.params.SrcRedisPortSegmentList) == 0 {
		err = fmt.Errorf("%s PortSegmentList(%+v) is invalid", job.Name(), job.params.SrcRedisPortSegmentList)
		job.runtime.Logger.Error(err.Error())
		return err
	}
	return nil
}

// 为何这里 要用这种方式 返回Name()?
// 因为 RedisDtsDataRepair 继承自 RedisDtsDataCheck, 两者Init()是相同的
// 只有这样  Init()中 job.Name() 方法才会返回正确的名字

// Name 原子任务名
func (job *RedisDtsDataCheck) Name() string {
	if job.atomJobName == "" {
		job.atomJobName = "redis_dts_datacheck"
	}
	return job.atomJobName
}

// Run 执行
func (job *RedisDtsDataCheck) Run() (err error) {
	// 1. 测试redis是否可连接
	err = job.TestConnectable()
	if err != nil {
		return
	}
	// 2. 获取工具
	err = job.GetTools()
	if err != nil {
		return
	}

	// 3. 并发提取与校验,并发度默认2,可通过参数concurrency传入,运行中可通过并发度控制文件动态调整
	taskList, err := job.runTasksWithDynamicConcurrency(func(task *RedisInsDtsDataCheckAndRepairTask) {
		task.KeyPatternAndDataCheck()
	})
	if err != nil {
		return err
	}

	var totalDiffKeysCnt uint64 = 0
	for _, tmp := range taskList {
		task := tmp
		if task.Err != nil {
			return task.Err
		}
		totalDiffKeysCnt += task.DiffKeysCnt
	}
	if totalDiffKeysCnt > 0 {
		err = fmt.Errorf("RedisDtsDataCheck totalDiffKeysCnt:%d", totalDiffKeysCnt)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.runtime.Logger.Info("RedisDtsDataCheck success totalDiffKeysCnt:%d", totalDiffKeysCnt)
	return
}

// getConcurrencyCtrlFile 并发度控制文件路径,文件内容为一个正整数。
// 运行中修改该文件(如 echo 4 > file),新并发度会在一个轮询周期内生效。
// 调大立即放行等待中的实例;调小不会中断已在运行的实例,仅约束后续待启动的实例。
func (job *RedisDtsDataCheck) getConcurrencyCtrlFile() string {
	safe := func(s string) string {
		return strings.Map(func(r rune) rune {
			if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '.' || r == '-' {
				return r
			}
			return '_'
		}, s)
	}
	basename := fmt.Sprintf("%s_concurrency.%s.%s.%s", job.Name(), safe(job.params.BkBizID),
		safe(job.params.SrcClusterAddr), safe(job.params.SrcRedisIP))
	return filepath.Join(job.saveDir, basename)
}

// watchConcurrencyCtrlFile 周期性读取并发度控制文件,值合法且与当前不同则动态调整协程池大小
func (job *RedisDtsDataCheck) watchConcurrencyCtrlFile(ctx context.Context, pool *ants.PoolWithFunc,
	ctrlFile string, maxConcurrency int) {
	ticker := time.NewTicker(concurrencyCtrlFilePollInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
		content, err := os.ReadFile(ctrlFile)
		if err != nil {
			// 文件不存在或读取失败,保持当前并发度
			continue
		}
		newVal, err := strconv.Atoi(strings.TrimSpace(string(content)))
		if err != nil || newVal <= 0 {
			job.runtime.Logger.Warn("concurrency ctrl file(%s) content invalid,ignore,content:%q",
				ctrlFile, strings.TrimSpace(string(content)))
			continue
		}
		if newVal > maxConcurrency {
			newVal = maxConcurrency
		}
		oldVal := pool.Cap()
		if newVal == oldVal {
			continue
		}
		pool.Tune(newVal)
		job.runtime.Logger.Info("%s concurrency changed from %d to %d,ctrlFile:%s",
			job.Name(), oldVal, newVal, ctrlFile)
	}
}

// runTasksWithDynamicConcurrency 按并发度对 SrcRedisPortSegmentList 中的每个实例执行 taskFn,
// 并发度可通过并发度控制文件在运行时动态调整。返回所有成功创建的task(含执行结果)。
func (job *RedisDtsDataCheck) runTasksWithDynamicConcurrency(taskFn func(task *RedisInsDtsDataCheckAndRepairTask)) (
	taskList []*RedisInsDtsDataCheckAndRepairTask, err error) {
	var wg sync.WaitGroup
	taskList = make([]*RedisInsDtsDataCheckAndRepairTask, 0, len(job.params.SrcRedisPortSegmentList))
	concurrency := job.params.GetConcurrency()
	pool, err := ants.NewPoolWithFunc(concurrency, func(i interface{}) {
		defer wg.Done()
		taskFn(i.(*RedisInsDtsDataCheckAndRepairTask))
	})
	if err != nil {
		job.runtime.Logger.Error("%s Run NewPoolWithFunc failed,err:%v", job.Name(), err)
		return nil, err
	}
	defer pool.Release()

	// 写入初始并发度,方便使用者发现并修改
	ctrlFile := job.getConcurrencyCtrlFile()
	if werr := os.WriteFile(ctrlFile, []byte(strconv.Itoa(concurrency)+"\n"), 0644); werr != nil {
		job.runtime.Logger.Warn("write concurrency ctrl file(%s) failed,err:%v", ctrlFile, werr)
	} else {
		job.runtime.Logger.Info("%s concurrency:%d,modify ctrlFile to change it at runtime:%s",
			job.Name(), concurrency, ctrlFile)
	}
	// 并发度上限为实例数,再大没有意义
	maxConcurrency := len(job.params.SrcRedisPortSegmentList)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go job.watchConcurrencyCtrlFile(ctx, pool, ctrlFile, maxConcurrency)

	for _, portItem := range job.params.SrcRedisPortSegmentList {
		task, terr := NewRedisInsDtsDataCheckAndRepairTask(job.params.SrcRedisIP, portItem, job)
		if terr != nil {
			job.runtime.Logger.Error("%s NewRedisInsDtsDataCheckAndRepairTask failed,port:%d,err:%v",
				job.Name(), portItem.Port, terr)
			continue
		}
		taskList = append(taskList, task)
		wg.Add(1)
		// 池满时 Invoke 会阻塞,直到有空闲槽位或并发度被调大
		if ierr := pool.Invoke(task); ierr != nil {
			wg.Done()
			task.Err = fmt.Errorf("pool.Invoke failed,err:%v,addr:%s", ierr, task.getSrcRedisAddr())
			job.runtime.Logger.Error("%v", task.Err)
		}
	}
	// 等待所有task执行完毕
	wg.Wait()
	return taskList, nil
}

func (job *RedisDtsDataCheck) getSaveDir() {
	job.saveDir = filepath.Join(consts.GetRedisBackupDir(), "dbbak/get_keys_pattern")
	util.MkDirsIfNotExists([]string{job.saveDir})
	util.LocalDirChownMysql(job.saveDir)
}

// TestConnectable 测试redis是否可连接
func (job *RedisDtsDataCheck) TestConnectable() (err error) {
	// 源redis可连接
	ports := make([]int, 0, len(job.params.SrcRedisPortSegmentList))
	for _, v := range job.params.SrcRedisPortSegmentList {
		ports = append(ports, v.Port)
	}
	err = myredis.LocalRedisConnectTest(job.params.SrcRedisIP, ports, job.params.SrcRedisPassword)
	if err != nil {
		job.runtime.Logger.Error("redis_dts_datacheck TestConnectable failed,err:%v", err)
		return
	}
	job.runtime.Logger.Info("redis_dts_datacheck TestConnectable success,ip:%s,ports:%+v", job.params.SrcRedisIP, ports)

	// 目的redis可连接
	cli01, err := myredis.NewRedisClientWithRetry(job.params.DstClusterAddr, job.params.DstClusterPassword, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if err != nil {
		return err
	}
	cli01.Close()
	return
}

// CheckDtsType 检查dtstype是否合法
func (job *RedisDtsDataCheck) CheckDtsType() (err error) {
	if job.params.DtsCopyType == consts.DtsTypeOneAppDiffCluster ||
		job.params.DtsCopyType == consts.DtsTypeDiffAppDiffCluster ||
		job.params.DtsCopyType == consts.DtsTypeSyncToOtherSystem ||
		job.params.DtsCopyType == consts.DtsTypeUserBuiltToDbm {
		return
	}
	err = fmt.Errorf("redis_dts_datacheck CheckDtsType failed, DtsType(%s) is invalid,must be [%s,%s,%s,%s]",
		job.params.DtsCopyType,
		consts.DtsTypeOneAppDiffCluster, consts.DtsTypeDiffAppDiffCluster,
		consts.DtsTypeSyncToOtherSystem, consts.DtsTypeUserBuiltToDbm)
	job.runtime.Logger.Error(err.Error())
	return
}

// GetTools 获取数据校验相关的工具
func (job *RedisDtsDataCheck) GetTools() (err error) {
	job.getSaveDir()
	err = job.params.Check()
	if err != nil {
		job.runtime.Logger.Error("GetTools DbToolsMediaPkg check fail,err:%v", err)
		return
	}
	err = job.params.DbToolsMediaPkg.Install()
	if err != nil {
		job.runtime.Logger.Error("GetTools DbToolsMediaPkg install fail,err:%v", err)
		return
	}
	// 这一部分和提取key保持一致
	// 复制dbtools/ldb_tendisplus,ldb_with_len.3.8, ldb_with_len.5.13
	// redis-shake redisSafeDeleteTool到get_keys_pattern
	cpCmd := fmt.Sprintf("cp  %s/ldb* %s/redis-shake %s/redis-shake-v4 %s/redisSafeDeleteTool %s", consts.DbToolsPath,
		consts.DbToolsPath, consts.DbToolsPath, consts.DbToolsPath, job.saveDir)
	job.runtime.Logger.Info(cpCmd)
	_, err = util.RunBashCmd(cpCmd, "", nil, 100*time.Second)
	if err != nil {
		return
	}
	// 因为tendisplus 底层 rocksdb 引擎会做升级,提取key必须依赖每个版本本身自带的ldb工具
	ldbTendisPath := filepath.Join(consts.UsrLocal, "redis", "bin", "ldb_tendis")
	ldbTendplusPath := filepath.Join(job.saveDir, "ldb_tendisplus")
	if util.FileExists(ldbTendisPath) {
		cpCmd = fmt.Sprintf("cp %s %s", ldbTendisPath, ldbTendplusPath)
		job.runtime.Logger.Info(cpCmd)
		_, err = util.RunBashCmd(cpCmd, "", nil, 1*time.Minute)
		if err != nil {
			return
		}
	}
	if !util.FileExists(consts.TendisDataCheckBin) {
		err = fmt.Errorf("%s not exists", consts.TendisDataCheckBin)
		job.runtime.Logger.Error(err.Error())
		return
	}
	job.dataCheckTool = consts.TendisDataCheckBin
	job.dataRepairTool = consts.RedisDiffKeysRepairerBin
	return nil
}

// Retry times
func (job *RedisDtsDataCheck) Retry() uint {
	return 2
}

// Rollback rollback
func (job *RedisDtsDataCheck) Rollback() error {
	return nil
}

// RedisInsDtsDataCheckAndRepairTask redis实例数据校验与数据修复task
type RedisInsDtsDataCheckAndRepairTask struct {
	keyPatternTask *RedisInsKeyPatternTask
	datacheckJob   *RedisDtsDataCheck
	DiffKeysCnt    uint64 `json:"diffKeysCnt"`
	HotKeysCnt     uint64 `json:"hotKeysCnt"`
	Err            error  `json:"err"`
}

// NewRedisInsDtsDataCheckAndRepairTask new
func NewRedisInsDtsDataCheckAndRepairTask(ip string, portAndSeg PortAndSegment, job *RedisDtsDataCheck) (
	task *RedisInsDtsDataCheckAndRepairTask, err error) {
	task = &RedisInsDtsDataCheckAndRepairTask{}
	task.datacheckJob = job
	task.keyPatternTask, err = NewRedisInsKeyPatternTask(
		job.params.BkBizID,
		job.params.SrcClusterAddr,
		ip,
		portAndSeg.Port,
		job.params.SrcRedisPassword,
		job.saveDir,
		job.runtime,
		"", "", "", "", "", "", // FileServer相关参数不需要
		job.params.KeyWhiteRegex, job.params.KeyBlackRegex,
		false, 0, 0, 0, // key删除相关参数不需要
		portAndSeg.SegmentStart, portAndSeg.SegmentEnd, nil)
	return
}

func (task *RedisInsDtsDataCheckAndRepairTask) getSaveDir() string {
	return task.datacheckJob.saveDir
}

func (task *RedisInsDtsDataCheckAndRepairTask) getSrcRedisAddr() string {
	return task.keyPatternTask.IP + ":" + strconv.Itoa(task.keyPatternTask.Port)
}

func (task *RedisInsDtsDataCheckAndRepairTask) getSrcRedisPassword() string {
	return task.datacheckJob.params.SrcRedisPassword
}

func (task *RedisInsDtsDataCheckAndRepairTask) getDstRedisAddr() string {
	return task.datacheckJob.params.DstClusterAddr
}

func (task *RedisInsDtsDataCheckAndRepairTask) getDstRedisPassword() string {
	return task.datacheckJob.params.DstClusterPassword
}

func (task *RedisInsDtsDataCheckAndRepairTask) getLogger() *logger.Logger {
	return task.datacheckJob.runtime.Logger
}

func (task *RedisInsDtsDataCheckAndRepairTask) getDataCheckDiffKeysFile() string {
	basename := fmt.Sprintf("dts_datacheck_diff_keys_%s_%d", task.keyPatternTask.IP, task.keyPatternTask.Port)
	return filepath.Join(task.getSaveDir(), basename)
}

func (task *RedisInsDtsDataCheckAndRepairTask) getRepairHotKeysFile() string {
	basename := fmt.Sprintf("dts_repair_hot_keys_%s_%d", task.keyPatternTask.IP, task.keyPatternTask.Port)
	return filepath.Join(task.getSaveDir(), basename)
}

func (task *RedisInsDtsDataCheckAndRepairTask) isClusterEnabled() (enabled bool) {
	var cli01 *myredis.RedisClient
	cli01, task.Err = myredis.NewRedisClientWithRetry(task.getSrcRedisAddr(), task.keyPatternTask.Password, 0,
		consts.TendisTypeRedisInstance, 10*time.Second)
	if task.Err != nil {
		return false
	}
	defer cli01.Close()
	enabled, task.Err = cli01.IsClusterEnabled()
	return
}

// tryFileLock 尝试获取文件锁,确保单个redis同一时间只有一个进程在进行数据校验
func (task *RedisInsDtsDataCheckAndRepairTask) tryFileLock(lockFile string, timeout time.Duration) (locked bool,
	flockP *flock.Flock) {
	msg := fmt.Sprintf("try to get filelock:%s,addr:%s", lockFile, task.getSrcRedisAddr())
	task.getLogger().Info(msg)

	flockP = flock.New(lockFile)
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	locked, task.Err = flockP.TryLockContext(ctx, 10*time.Second)
	if task.Err != nil {
		task.Err = fmt.Errorf("try to get filelock fail,err:%v,addr:%s", task.Err, task.getSrcRedisAddr())
		task.getLogger().Error(task.Err.Error())
		return false, flockP
	}
	if !locked {
		return false, flockP
	}
	locked = true
	return locked, flockP
}

func (task *RedisInsDtsDataCheckAndRepairTask) getDataCheckRet() {
	// 获取不一致key信息
	var msg string
	var diffFileStat os.FileInfo
	var headText string
	diffFileStat, task.Err = os.Stat(task.getDataCheckDiffKeysFile())
	if task.Err != nil && os.IsNotExist(task.Err) == true {
		// 没有不一致的key
		msg = fmt.Sprintf("srcAddr:%s dstAddr:%s dts data check success no diff keys",
			task.getSrcRedisAddr(), task.getDstRedisAddr())
		task.getLogger().Info(msg)
		return
	} else if task.Err != nil {
		task.Err = fmt.Errorf("diffKeysFile:%s os.stat fail,err:%v", task.getDataCheckDiffKeysFile(), task.Err)
		task.getLogger().Error(task.Err.Error())
		return
	}
	if diffFileStat.Size() == 0 {
		msg := fmt.Sprintf("srcAddr:%s dstAddr:%s dts data check success no diff keys", task.getSrcRedisAddr(),
			task.getDstRedisAddr())
		task.getLogger().Info(msg)
		return
	}
	task.DiffKeysCnt, task.Err = util.FileLineCounter(task.getDataCheckDiffKeysFile())
	if task.Err != nil {
		return
	}
	if task.DiffKeysCnt == 0 {
		msg := fmt.Sprintf("srcAddr:%s dstAddr:%s dts data check success,%d diff keys",
			task.getSrcRedisAddr(), task.getDstRedisAddr(), task.DiffKeysCnt)
		task.getLogger().Info(msg)
		return
	}

	var predix string = fmt.Sprintf("srcRedisAddr:%s,dstRedisAddr:%s,dts data check fail,diff keys for example:",
		task.getSrcRedisAddr(), task.getDstRedisAddr())
	if task.DiffKeysCnt <= 20 {
		predix = "all diffKeys:"
		predix = fmt.Sprintf("srcRedisAddr:%s,dstRedisAddr:%s,dts data check fail,all diffKeys:",
			task.getSrcRedisAddr(), task.getDstRedisAddr())
	}

	// 打印前20个不一致的key
	headCmd := fmt.Sprintf("head -20 %s", task.getDataCheckDiffKeysFile())
	task.getLogger().Info(headCmd)
	headText, task.Err = util.RunBashCmd(headCmd, "", nil, 10*time.Second)
	if task.Err != nil {
		return
	}
	headLines := strings.ReplaceAll(headText, "\n", ",")
	headLines = strings.ReplaceAll(headLines, "\r", ",")
	task.getLogger().Info(predix + headLines)
}

func (task *RedisInsDtsDataCheckAndRepairTask) getDataRepairRet() {
	var msg string
	hotFileStat, err := os.Stat(task.getRepairHotKeysFile())
	if err != nil && os.IsNotExist(err) {
		// 没有hotKey
		msg = fmt.Sprintf("all keys repaired successfully,srcAddr:%s,dstAddr:%s", task.getSrcRedisAddr(),
			task.getDstRedisAddr())
		task.getLogger().Info(msg)
		return
	} else if err != nil {
		task.Err = fmt.Errorf("hotKeysFile:%s os.stat fail,err:%v", task.getRepairHotKeysFile(), err)
		task.getLogger().Info(msg)
		return
	}
	if hotFileStat.Size() == 0 {
		msg = fmt.Sprintf("all keys repaired successfully,srcAddr:%s,dstAddr:%s", task.getSrcRedisAddr(),
			task.getDstRedisAddr())
		task.getLogger().Info(msg)
		return
	}
	task.HotKeysCnt, err = util.FileLineCounter(task.getRepairHotKeysFile())
	if err != nil {
		task.Err = err
		task.getLogger().Error(task.Err.Error())
		return
	}
	msg = fmt.Sprintf("%d hot keys cannot be repaired,srcRedisAddr:%s", task.HotKeysCnt, task.getSrcRedisAddr())
	task.getLogger().Info(msg)
	return
}

// RunCmdAndWatchLog 执行命令并不断打印命令日志
func (task *RedisInsDtsDataCheckAndRepairTask) RunCmdAndWatchLog(myCmd, logCmd string) {
	var errBuffer bytes.Buffer
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cmd := exec.CommandContext(ctx, "bash", "-c", myCmd)
	stdout, _ := cmd.StdoutPipe()
	cmd.Stderr = &errBuffer

	if task.Err = cmd.Start(); task.Err != nil {
		task.Err = fmt.Errorf("RedisInsDtsDataCheckAndRepairTask cmd.Start fail,err:%v,cmd:%s", task.Err, logCmd)
		task.getLogger().Error(task.Err.Error())
		return
	}

	scanner := bufio.NewScanner(stdout)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		// 不断打印进度
		line := scanner.Text()
		if strings.Contains(line, `"level":"error"`) == true {
			task.Err = errors.New(line)
			task.getLogger().Error(task.Err.Error())
			continue
		}
		line = line + ";" + task.getSrcRedisAddr()
		task.getLogger().Info(line)
	}
	task.Err = scanner.Err()
	if task.Err != nil {
		task.getLogger().Error(task.Err.Error())
		return
	}

	if task.Err = cmd.Wait(); task.Err != nil {
		task.Err = fmt.Errorf("RedisInsDtsDataCheckAndRepairTask cmd.Wait fail,err:%v", task.Err)
		task.getLogger().Error(task.Err.Error())
		return
	}
	errStr := errBuffer.String()
	errStr = strings.TrimSpace(errStr)
	if len(errStr) > 0 {
		task.Err = fmt.Errorf("RedisInsDtsDataCheckAndRepairTask fail,err:%s", errStr)
		task.getLogger().Error(task.Err.Error())
		return
	}
}

// KeyPatternAndDataCheck key提取和数据校验
func (task *RedisInsDtsDataCheckAndRepairTask) KeyPatternAndDataCheck() {
	var extraOptsBuilder strings.Builder
	var checkMode string
	var locked bool
	var flockP *flock.Flock
	clusterEnabled := task.isClusterEnabled()
	if task.Err != nil {
		return
	}
	if clusterEnabled {
		extraOptsBuilder.WriteString(" --is-src-cluster-replicate ")
	}

	// 尝试获取文件锁,确保单个redis同一时间只有一个进程在进行数据校验
	lockFile := filepath.Join(task.getSaveDir(), fmt.Sprintf("lock_dtsdatacheck.%s.%d",
		task.keyPatternTask.IP, task.keyPatternTask.Port))
	locked, flockP = task.tryFileLock(lockFile, 24*time.Hour)
	if task.Err != nil {
		return
	}
	if !locked {
		return
	}
	defer flockP.Unlock()

	// 源redis 属于dbm管理,则执行key提取,而后执行数据校验
	if consts.IsDtsTypeSrcClusterBelongDbm(task.datacheckJob.params.DtsCopyType) {
		checkMode = consts.DtsDataCheckByKeysFileMode
		// 获取key
		task.keyPatternTask.newConnect()
		if task.keyPatternTask.Err != nil {
			task.Err = task.keyPatternTask.Err
			return
		}
		task.keyPatternTask.GetTendisKeys()
		if task.keyPatternTask.Err != nil {
			task.Err = task.keyPatternTask.Err
			return
		}
		if task.keyPatternTask.TendisType == consts.TendisTypeTendisplusInsance {
			// 合并 kvstore keys临时文件
			task.keyPatternTask.mergeTendisplusDbFile()
			if task.keyPatternTask.Err != nil {
				task.Err = task.keyPatternTask.Err
				return
			}
		}
		extraOptsBuilder.WriteString(" --keys-file=" + task.keyPatternTask.ResultFile + " --thread-cnt=200 ")
	} else {
		// 源redis 属于用户自建,则通过scan方式获取key,而后执行数据校验
		checkMode = consts.DtsDataCheckByScanMode
		extraOptsBuilder.WriteString(fmt.Sprintf(" --match-pattern=%q --scan-count=20000  --thread-cnt=200 ",
			task.datacheckJob.params.KeyWhiteRegex))
	}
	// 数据校验
	dataCheckCmd := fmt.Sprintf(
		`cd %s && %s %s --src-addr=%s --src-password="%s" --dst-addr=%s --dst-password="%s" --result-file=%s --ticker=120 %s`,
		task.datacheckJob.saveDir, task.datacheckJob.dataCheckTool, checkMode,
		task.getSrcRedisAddr(), task.getSrcRedisPassword(),
		task.getDstRedisAddr(), task.getDstRedisPassword(),
		task.getDataCheckDiffKeysFile(), extraOptsBuilder.String())
	logCmd := fmt.Sprintf(
		`cd %s && %s %s --src-addr=%s --src-password="xxxx" --dst-addr=%s --dst-password="xxxx" --result-file=%s --ticker=120 %s`,
		task.datacheckJob.saveDir, task.datacheckJob.dataCheckTool, checkMode,
		task.getSrcRedisAddr(), task.getDstRedisAddr(),
		task.getDataCheckDiffKeysFile(), extraOptsBuilder.String())
	task.getLogger().Info(logCmd)

	task.RunCmdAndWatchLog(dataCheckCmd, logCmd)
	if task.Err != nil {
		return
	}
	// 数据校验结果
	task.getDataCheckRet()
	return
}

// RunDataRepair 执行数据修复
func (task *RedisInsDtsDataCheckAndRepairTask) RunDataRepair() {
	var diffKeysCnt uint64
	var locked bool
	var flockP *flock.Flock
	if !util.FileExists(task.getDataCheckDiffKeysFile()) {
		task.getLogger().Info("diff keys file not exists,skip data repair,file:%s", task.getDataCheckDiffKeysFile())
		return
	}
	diffKeysCnt, task.Err = util.FileLineCounter(task.getDataCheckDiffKeysFile())
	if task.Err != nil {
		task.getLogger().Error("FileLineCounter fail,err:%v,file:%s", task.Err, task.getDataCheckDiffKeysFile())
		return
	}
	if diffKeysCnt == 0 {
		task.getLogger().Info("diff keys file is empty,skip data repair,file:%s", task.getDataCheckDiffKeysFile())
		return
	}

	// 尝试获取文件锁,确保单个redis同一时间只有一个进程在进行数据修复
	lockFile := filepath.Join(task.getSaveDir(), fmt.Sprintf("lock_dtsdatarepair.%s.%d",
		task.keyPatternTask.IP, task.keyPatternTask.Port))
	locked, flockP = task.tryFileLock(lockFile, 5*time.Hour)
	if task.Err != nil {
		return
	}
	if !locked {
		return
	}
	defer flockP.Unlock()

	var extraOptsBuilder strings.Builder
	clusterEnabled := task.isClusterEnabled()
	if task.Err != nil {
		return
	}
	if clusterEnabled {
		extraOptsBuilder.WriteString(" --is-src-cluster-replicate ")
	}

	repairCmd := fmt.Sprintf(
		`cd %s && %s --src-addr=%s --src-password="%s" \
		--dest-addr=%s --dest-password="%s"  --diff-keys-file=%s --hot-keys-file=%s %s`,
		task.getSaveDir(), task.datacheckJob.dataRepairTool,
		task.getSrcRedisAddr(), task.getSrcRedisPassword(),
		task.getDstRedisAddr(), task.getDstRedisPassword(),
		task.getDataCheckDiffKeysFile(), task.getRepairHotKeysFile(),
		extraOptsBuilder.String())
	logCmd := fmt.Sprintf(
		`cd %s && %s --src-addr=%s --src-password="xxxx" \
		--dest-addr=%s --dest-password="xxxx"  --diff-keys-file=%s --hot-keys-file=%s %s`,
		task.getSaveDir(), task.datacheckJob.dataRepairTool,
		task.getSrcRedisAddr(), task.getDstRedisAddr(),
		task.getDataCheckDiffKeysFile(), task.getRepairHotKeysFile(),
		extraOptsBuilder.String())

	task.getLogger().Info(logCmd)
	task.RunCmdAndWatchLog(repairCmd, logCmd)
	if task.Err != nil {
		return
	}
	task.getDataRepairRet()
	return
}
