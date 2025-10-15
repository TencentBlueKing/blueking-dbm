package atomsys

import (
	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/keystat_report"
	"dbm-services/redis/db-tools/dbactuator/pkg/redisinfo"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-playground/validator/v10"
)

const keySplitterReportName = "key-splitter.report"
const keySplitterRankReportName = "rank-key-splitter.report"

type KeyStatIns struct {
	ShardName   string `json:"shard_name"`
	Addr        string `json:"addr" validate:"required"`
	SlaveAddr   string `json:"slave_addr"` // slave addr, if not set, use addr
	StartBucket int    `json:"start_bucket" validate:"required"`
	EndBucket   int    `json:"end_bucket" validate:"required"`
}

func (ins *KeyStatIns) IpPort() (string, int, error) {
	ip, port, err := net.SplitHostPort(ins.Addr)
	if err != nil {
		return "", 0, err
	}
	portInt, err := strconv.Atoi(port)
	if err != nil {
		return "", 0, err
	}
	return ip, portInt, nil
}
func getRdbName(ins KeyStatIns) string {
	ip, port, err := ins.IpPort()
	if err != nil {
		return ""
	}
	return fmt.Sprintf("%s.%d.rdb", ip, port)
}

// AnalysisHotkeyParams AnalysisHotkey参数
type KeyStatParams struct {
	RedisPassword   string       `json:"redis_password" validate:"required"`
	InsList         []KeyStatIns `json:"ins_list"`
	RecordId        int          `json:"record_id" validate:"required"`
	ApiServer       string       `json:"api_server" validate:"required"`
	BkCloudId       int          `json:"bk_cloud_id"`
	DbCloudToken    string       `json:"db_cloud_token" validate:"required"`
	ExecIp          string       `json:"exec_ip" validate:"required"`
	CheckInterval   int          `json:"check_interval" validate:"required,min=1"` // 检查间隔时间，单位：秒
	ClusterId       int64        `json:"cluster_id" validate:"required"`
	ClusterShardNum int64        `json:"cluster_shard_num" validate:"required"`
}

// HotkeyAnalysis  结构体
type KeyStat struct {
	runtime       *jobruntime.JobGenericRuntime
	params        *KeyStatParams
	reportStatus  *keystat_report.KeyStatRecord
	atimeRequired bool
	startTime     time.Time
}

// NewKeyStat new a key stat job
func NewKeyStat() jobruntime.JobRunner {
	return &KeyStat{
		startTime: time.Now(),
	}
}

const KeyStatReportItemUrl = "/apis/proxypass/upsert_keystat_report_item/"
const KeyStatRankReportUrl = "/apis/proxypass/upsert_keystat_rank_item/"
const KeyStatReportStatusUrl = "/apis/proxypass/update_keystat_report_record/"
const KeySplitter = "/data/dbbak/keystat/key-splitter"
const RedisCli = "/data/dbbak/keystat/redis-cli"

func (job *KeyStat) useLocalPlayLoadFile() (payload string, err error) {
	fileName := job.Name() + ".payload"
	_, err = os.Stat(fileName)
	if err != nil {
		return "", err
	}
	payloadStr, err := os.ReadFile(fileName)
	if err != nil {
		return "", err
	}
	payload = string(payloadStr)
	job.runtime.Logger.Info("useLocalPlayLoadFile from local file %s, payload:%s", fileName, payload)
	return payload, nil
}

// Init 初始化
func (job *KeyStat) Init(m *jobruntime.JobGenericRuntime) error {
	job.runtime = m
	var err error
	if s, err := job.useLocalPlayLoadFile(); err == nil {
		job.runtime.PayloadDecoded = s
	}
	err = json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params)
	if err != nil {
		job.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}

	// 参数有效性检查
	validate := validator.New()
	err = validate.Struct(job.params)
	if err != nil {
		if _, ok := err.(*validator.InvalidValidationError); ok {
			job.runtime.Logger.Error("RedisCapturer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
		for _, err := range err.(validator.ValidationErrors) {
			job.runtime.Logger.Error("RedisCapturer Init params validate failed,err:%v,params:%+v",
				err, job.params)
			return err
		}
	}

	job.reportStatus = &keystat_report.KeyStatRecord{
		RecordId: job.params.RecordId,
		Status:   statusReady,
		ExecIp:   job.params.ExecIp,
	}

	// check redis-cli and key-splitter is exist
	if _, err := os.Stat(RedisCli); os.IsNotExist(err) {
		job.runtime.Logger.Error("redis-cli %s not found, err:%s", RedisCli, err)
		return err
	}
	if _, err := os.Stat(KeySplitter); os.IsNotExist(err) {
		job.runtime.Logger.Error("key-splitter %s not found, err:%s", KeySplitter, err)
		return err
	}

	return nil
}

// Run 运行监听请求任务
func (job *KeyStat) Run() (err error) {
	err = job.updateReportStatus(statusRunning, nil)
	if err != nil {
		job.runtime.Logger.Error("update report status failed, err:%s", err)
		// return err
	}
	job.runtime.Logger.Info("update report status success, status:%s", statusRunning)
	// 1. 创建工作目录
	workDir := filepath.Join(consts.GetRedisBackupDir(), "dbbak/keystat", job.runtime.UID)
	util.MkDirsIfNotExists([]string{workDir})
	util.LocalDirChownMysql(workDir)
	job.runtime.Logger.Info("KeyStat Run, workDir:%s", workDir)
	// 1.0 get version
	versionInfo, err := job.getRedisVersion()
	if err != nil {
		job.runtime.Logger.Error("getRedisVersion failed, err:%s", err)
		return err
	}

	if versionInfo.Major >= 6 {
		job.runtime.Logger.Info("redis version >= 6, version:%s, will check atime", versionInfo.Str)
		job.atimeRequired = true
	} else {
		job.runtime.Logger.Info("redis version < 6, version:%s, will not check atime", versionInfo.Str)
		job.atimeRequired = false
	}

	// 1.1 check redis load

	if err = job.checkRedisLoad(time.Duration(job.params.CheckInterval) * time.Second); err != nil {
		job.runtime.Logger.Error("checkRedisLoad failed, err:%s", err)
		return err
	}

	// 2. safe dump rdb to workDir if not exists
	err = job.safeDumpRdb(workDir)
	if err != nil {
		job.runtime.Logger.Error("safeDumpRdb failed, err:%s", err)
		return err
	}

	// 3. do key stat if report file not exists
	err = job.doKeyStat(workDir)
	if err != nil {
		job.runtime.Logger.Error("doKeyStat failed, err:%s", err)
		return err
	}

	// 4. upload report. report server 会处理重复的记录
	err = job.uploadReport(workDir)
	if err != nil {
		job.runtime.Logger.Error("uploadReport failed, err:%s", err)
		return err
	}
	return nil
}

func (job *KeyStat) getRedisVersion() (*redisinfo.RedisVersion, error) {
	// 1. get redis info
	infoMap, err := job.getRedisInfo(consts.RedisMasterRole)
	if err != nil {
		job.runtime.Logger.Error("getRedisInfo failed, err:%s", err)
		return nil, err
	}
	var versionInfo *redisinfo.RedisVersion
	for addr, info := range infoMap {
		ver, err := redisinfo.ParseRedisVersion(info.Server.RedisVersion)
		if err != nil {
			job.runtime.Logger.Error("parse redis version failed, host %s, err:%s, version:%s", addr, err, info.Server.RedisVersion)
			return nil, err
		}
		if versionInfo == nil || versionInfo.Compare(ver) > 0 {
			versionInfo = ver
		}
	}
	return versionInfo, nil
}

const maxInstUsedRatio = 0.95

func (job *KeyStat) checkRedisLoad(timeout time.Duration) (err error) {
	rdbRole := consts.RedisSlaveRole
	if job.atimeRequired {
		rdbRole = consts.RedisMasterRole
	}

	info1, err := job.getRedisInfo(rdbRole)
	if err != nil {
		job.runtime.Logger.Error("getRedisInfo failed, err:%s", err)
		return err
	}
	time.Sleep(timeout)
	info2, err := job.getRedisInfo(rdbRole)
	if err != nil {
		job.runtime.Logger.Error("getRedisInfo failed, err:%s", err)
		return err
	}
	if len(info1) != len(info2) {
		return errors.New("redis load is not stable")
	}

	for addr, v1 := range info1 {
		v2, ok := info2[addr]
		if !ok {
			return errors.New("redis load is not stable")
		}

		// node 内存. 暂不检查

		if v2.Memory.Maxmemory == 0 {
			return fmt.Errorf("node %s redis memory maxmemory is 0", addr)
		}

		// redis memory 使用率 gt 95%
		usedRatio := float64(v2.Memory.UsedMemory) / float64(v2.Memory.Maxmemory)
		if usedRatio > maxInstUsedRatio {
			return fmt.Errorf("node %s redis memory used ratio %0.2f%% gt %0.2f%%, please scale out first to avoid data loss",
				addr, usedRatio*100, maxInstUsedRatio*100)
		}

		// repl offset
		// 写入量不能大于50%的分片空闲内存
		// 每秒写入量不能大于 4M
		// 如果无法获得分片空闲内存，则每秒写入量不能大于 100k/s
		instFreeMem := int64(v1.Memory.Maxmemory - v1.Memory.UsedMemory)
		offSet := v2.Replication.MasterReplOffset - v1.Replication.MasterReplOffset
		if instFreeMem > 0 {
			if float64(offSet)/timeout.Seconds() > 1024*1024*2 {
				return fmt.Errorf("addr %s ReplOffset is %0.2fMB/s, gt 2MB/s, please scale out or reduce repl offset to avoid data loss",
					addr, float64(offSet)/timeout.Seconds()/1024/1024)
			}
		} else {
			// 每秒写入量不能大于100k/s
			if float64(offSet)/timeout.Seconds() > 1024*200 {
				return fmt.Errorf("addr %s ReplOffset gt 200KB/s, %d, please try again later", addr, offSet)
			}
		}
	}
	return nil
}

// getRedisInfo 获取redis info. 并行执行，返回map[string]*redisinfo.Info
func (job *KeyStat) getRedisInfo(role string) (redisInfo map[string]*redisinfo.Info, err error) {
	redisInfo = make(map[string]*redisinfo.Info)
	commandIn := make([]redisinfo.RedisCommandIn, 0)
	for _, ins := range job.params.InsList {
		switch role {
		case consts.RedisMasterRole:
			if ins.Addr == "" {
				job.runtime.Logger.Error("getRedisInfo failed, addr is empty, role:%s", role)
				return nil, errors.New("addr is empty")
			}
			commandIn = append(commandIn, redisinfo.RedisCommandIn{
				Host: ins.Addr,
				Pass: job.params.RedisPassword,
				Cmd:  []string{"info"},
			})
		case consts.RedisSlaveRole:
			if ins.SlaveAddr == "" {
				job.runtime.Logger.Error("getRedisInfo failed, slave addr is empty, role:%s", role)
				return nil, errors.New("slave addr is empty")
			}
			commandIn = append(commandIn, redisinfo.RedisCommandIn{
				Host: ins.SlaveAddr,
				Pass: job.params.RedisPassword,
				Cmd:  []string{"info"},
			})
		default:
			return nil, fmt.Errorf("invalid role: %s, must be master or slave", role)
		}
	}
	outs, err := redisinfo.ExecRedisCommandConcurrency(commandIn, 10)
	if err != nil {
		job.runtime.Logger.Error("getRedisInfo failed, err:%s", err)
		return nil, err
	}
	errs := make([]error, 0)
	for _, out := range outs {
		if out.Err != nil {
			job.runtime.Logger.Error("getRedisInfo failed, err:%s", out.Err)
			errs = append(errs, out.Err)
			continue
		}
		info, err := redisinfo.Parse(out.Out.(string))
		if err != nil {
			job.runtime.Logger.Error("parse info failed, err:%s, out:%s", err, out.Out)
			errs = append(errs, err)
			continue
		}
		redisInfo[out.Host] = &info
	}
	return redisInfo, errors.Join(errs...)
}

func (job *KeyStat) safeDumpRdb(workDir string) (err error) {
	// 1. 获取redis实例
	groupByIp := make(map[string][]KeyStatIns)
	ins := job.params.InsList
	rdbTotalCount := 0
	toDumpCount := 0
	toSkipCount := 0
	for i := range ins {
		rdbTotalCount++
		job.runtime.Logger.Info("safeDumpRdb, addr:%s, startBucket:%d, endBucket:%d",
			ins[i].Addr, ins[i].StartBucket, ins[i].EndBucket)
		ip, _, err := ins[i].IpPort()
		if err != nil {
			job.runtime.Logger.Error("safeDumpRdb, addr:%s, err:%s", ins[i].Addr, err)
			return err
		}

		// 如果文件已经存在，则不进行dump
		rdbName := getRdbName(ins[i])
		rdbPath := filepath.Join(workDir, rdbName)
		if _, err := os.Stat(rdbPath); err == nil {
			job.runtime.Logger.Info("safeDumpRdb, rdbPath:%s already exists, continue", rdbPath)
			toSkipCount++
			continue
		}

		// 按IP分组，同一个IP的实例串行dump
		if _, ok := groupByIp[ip]; !ok {
			groupByIp[ip] = make([]KeyStatIns, 0)
		}
		groupByIp[ip] = append(groupByIp[ip], ins[i])
		toDumpCount++
	}

	job.runtime.Logger.Info("safeDumpRdb, toDumpCount:%d, toSkipCount:%d, rdbTotalCount:%d",
		toDumpCount, toSkipCount, rdbTotalCount)

	if toDumpCount > 0 {
		wg := sync.WaitGroup{}
		errChan := make(chan error, len(groupByIp))
		wg.Add(len(groupByIp))
		for ip := range groupByIp {
			// 按IP并发dump rdb.
			go func(wg *sync.WaitGroup, ip string, insList []KeyStatIns) {
				defer wg.Done()
				job.runtime.Logger.Info("safeDumpRdb, ip:%s, insList:%+v", ip, insList)
				for _, ins := range insList {
					err := job.safeDumpRdbOne(workDir, ins, job.params.RedisPassword)
					if err != nil {
						job.runtime.Logger.Error("safeDumpRdbOne failed, err:%s", err)
						errChan <- fmt.Errorf("ip %s dump rdb failed: %w", ip, err)
						return
					}
				}
			}(&wg, ip, groupByIp[ip])
		}
		wg.Wait()
		close(errChan)

		// 收集所有错误
		var dumpErrors []error
		for e := range errChan {
			dumpErrors = append(dumpErrors, e)
		}
		if len(dumpErrors) > 0 {
			job.runtime.Logger.Error("safeDumpRdb has %d errors", len(dumpErrors))
			return errors.Join(dumpErrors...)
		}
	}
	job.runtime.Logger.Info("safeDumpRdb success, %d rdb dumped, %d rdb skipped", toDumpCount, toSkipCount)
	return nil
}

// safeDumpRdbOne dump rdb to workDir
func (job *KeyStat) safeDumpRdbOne(workDir string, ins KeyStatIns, pwd string) (err error) {
	job.runtime.Logger.Info("safeDumpRdbOne, addr:%s, startBucket:%d, endBucket:%d",
		ins.Addr, ins.StartBucket, ins.EndBucket)
	rdbName := getRdbName(ins)
	rdbPath := filepath.Join(workDir, rdbName)
	ip, port, err := ins.IpPort()
	if err != nil {
		job.runtime.Logger.Error("safeDumpRdbOne failed, err:%s", err)
		return err
	}
	cmd := mycmd.New(RedisCli, "-h", ip, "-p", port, "-a", mycmd.Password(pwd), "--rdb", rdbPath)
	// rdb 导出时间
	result, err := cmd.Run(1 * time.Hour)
	if err != nil {
		job.runtime.Logger.Error("safeDumpRdbOne failed, err:%s, out:%s, stderr:%s", err, result.GetStdout(), result.GetStderr())
		return err
	}
	rdbSize, err := os.Stat(rdbPath)
	if err != nil {
		job.runtime.Logger.Error("safeDumpRdbOne failed, err:%s", err)
		return err
	}
	job.runtime.Logger.Info("safeDumpRdbOne success, rdbPath:%s, rdbSize:%d", rdbPath, rdbSize.Size())
	return nil
}

func (job *KeyStat) doKeyStat(workDir string) (err error) {
	// 1. get rdb file nameList
	rdbFileName := []string{}
	for _, i := range job.params.InsList {
		rdbFileName = append(rdbFileName, getRdbName(i))
	}
	err = os.Chdir(workDir)
	if err != nil {
		job.runtime.Logger.Error("s.Chdir failed, err:%s", err)
		return err
	}

	reportSize, _ := util.GetFileSize(filepath.Join(workDir, keySplitterReportName))
	rankReportSize, _ := util.GetFileSize(filepath.Join(workDir, keySplitterRankReportName))
	if reportSize > 0 && rankReportSize > 0 {
		job.runtime.Logger.Info("doKeyStat, reportFile:%s, rankReportFile:%s already exists, skip to Exec KeySplitter",
			keySplitterReportName, keySplitterRankReportName)
		return nil
	}

	keyStatCmd := mycmd.New(
		KeySplitter,
		"-rdb", strings.Join(rdbFileName, ","),
		"-pidFile", filepath.Join(workDir, "key-splitter.pid"),
		"-logFile", filepath.Join(workDir, "key-splitter.log"),
		"-logLevel", "info",
		"-reportFile", filepath.Join(workDir, keySplitterReportName),
	)

	cmdLine := keyStatCmd.GetCmdLine2(true)
	job.runtime.Logger.Info("workDir:%s, keyStatCmd: %s", workDir, cmdLine)

	result, err := keyStatCmd.Run(3600 * 24 * time.Hour)
	if err != nil {
		job.runtime.Logger.Error("keyStatCmd failed, err:%v, stderr:%q", err, result.GetStderr())
		return err
	}

	job.runtime.Logger.Info("keyStatCmd success")

	return nil
}

func (job *KeyStat) uploadReport(workDir string) (err error) {
	// check report file
	reportFile := filepath.Join(workDir, keySplitterReportName)
	rankReportFile := filepath.Join(workDir, keySplitterRankReportName)
	stat, err := os.Stat(reportFile)
	if err != nil {
		job.runtime.Logger.Error("uploadReport failed, err:%s", err)
		return err
	}
	rankStat, err := os.Stat(rankReportFile)
	if err != nil {
		job.runtime.Logger.Error("uploadReport failed, err:%s", err)
		return err
	}
	reportSize := stat.Size()
	rankReportSize := rankStat.Size()
	job.runtime.Logger.Info("reportFile:%s, fileSize:%d", reportFile, reportSize)
	job.runtime.Logger.Info("rankReportFile:%s, fileSize:%d", rankReportFile, rankReportSize)

	if reportSize == 0 {
		return errors.New("reportFile is empty")
	} else if rankReportSize == 0 {
		return errors.New("rankReportFile is empty")
	}

	reportRows, rankRows, err := keystat_report.LoadReport(reportFile, rankReportFile)
	if err != nil {
		return err
	}
	// 获取global rank.
	globalRank, e := rankRows["global"]
	if !e {
		return errors.New("get global rank failed")
	} else {
		for i := range globalRank.KeyList {
			globalRank.KeyList[i].RecordId = job.params.RecordId
		}
	}

	// 计算内存占比
	memTotal := int64(0)
	for i := range reportRows {
		memTotal += reportRows[i].MemUsedBytes
	}
	if memTotal == 0 {
		return errors.New("memTotal is 0, no data to report")
	}
	for i := range reportRows {
		reportRows[i].RecordId = job.params.RecordId
		reportRows[i].MemUsedPct =
			// 保留2位小数，乘以10000，再除以100，得到2位小数
			math.Floor((float64(reportRows[i].MemUsedBytes)/float64(memTotal))*10000) / 100
	}

	// 发送报告到DB.
	err = job.sendReportToDB(reportRows, globalRank.KeyList)
	if err != nil {
		job.runtime.Logger.Error("sendReportToDB failed, err:%s", err)
		job.updateReportStatus(statusFailed, map[string]any{
			"analysis_time": int(time.Since(job.startTime).Seconds()),
		})
		return err
	} else {
		job.updateReportStatus(statusSuccess, map[string]any{
			"analysis_time": int(time.Since(job.startTime).Seconds()),
		})
	}

	job.runtime.Logger.Info("upload report success")
	return nil
}

/*
class StateType(str, StructuredEnum):
    CREATED = EnumField("CREATED", _("创建态"))
    READY = EnumField("READY", _("准备态"))
    RUNNING = EnumField("RUNNING", _("运行态"))
    SUSPENDED = EnumField("SUSPENDED", _("暂停态"))
    BLOCKED = EnumField("BLOCKED", _("闭塞态"))
    FINISHED = EnumField("FINISHED", _("完成态"))
    FAILED = EnumField("FAILED", _("失败态"))
    REVOKED = EnumField("REVOKED", _("取消态"))
    EXPIRED = EnumField("EXPIRED", _("已过期"))
*/

const statusReady = "READY"
const statusRunning = "RUNNING"
const statusSuccess = "FINISHED"
const statusFailed = "FAILED"

// updateReportStatus 更新报告状态. 可添加其他参数，如分析时间、分析进度等.
func (job *KeyStat) updateReportStatus(status string, params map[string]any) error {
	cli, err := util.NewClient(job.params.ApiServer, job.params.DbCloudToken, job.params.BkCloudId)
	if err != nil {
		return err
	}
	if params == nil {
		params = make(map[string]any)
	}
	params["record_id"] = job.params.RecordId
	params["status"] = status
	params["update_at"] = time.Now()
	ret, err := cli.Do(http.MethodPost, KeyStatReportStatusUrl, params)
	if err != nil {
		return err
	}
	job.runtime.Logger.Info("update report status success, message:%s, code:%d, data:%s",
		ret.Message, ret.Code, string(ret.Data))
	if ret.Code != 0 {
		return errors.New(ret.Message)
	}
	return nil
}

// sendReportToDB 发送报告到SaasApi
func (job *KeyStat) sendReportToDB(
	reportRows []keystat_report.KeyStatReportItem,
	rankRows []keystat_report.KeyStatRankItem) error {

	cli, err := util.NewClient(job.params.ApiServer, job.params.DbCloudToken, job.params.BkCloudId)
	if err != nil {
		return err
	}

	// 2. upload key report.
	ret, err := cli.Do(http.MethodPost, KeyStatReportItemUrl, map[string]any{
		"keystat_report_item": reportRows,
		"record_id":           job.params.RecordId,
		"truncate":            true,
	})
	if err != nil {
		return errors.New("upload key report failed, err:" + err.Error())
	}
	job.runtime.Logger.Info("upload key report success, ret:%+v", ret)

	// 3. upload rank report.
	ret, err = cli.Do(http.MethodPost, KeyStatRankReportUrl, map[string]any{
		"keystat_rank_item": rankRows,
		"record_id":         job.params.RecordId,
		"truncate":          true,
	})
	if err != nil {
		return errors.New("upload rank report failed, err:" + err.Error())
	}
	job.runtime.Logger.Info("upload rank report success, ret:%+v", ret)

	return nil
}

// Name 原子任务名
func (job *KeyStat) Name() string {
	return "keystat"
}

// Retry times
func (job *KeyStat) Retry() uint {
	return 2
}

// Rollback rollback
func (job *KeyStat) Rollback() error {
	return nil
}
