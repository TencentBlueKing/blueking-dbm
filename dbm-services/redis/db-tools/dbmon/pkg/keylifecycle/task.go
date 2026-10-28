package keylifecycle

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"

	"github.com/shirou/gopsutil/v3/mem"
)

// 给个默认值
var MemUsedPercent = 70

// tempKeysFilePattern 临时 keys 文件通配符, 如 v.30000.keys / v.30000.3.keys
const tempKeysFilePattern = "v.*.keys"

// Task 任务内容
type Task struct {
	statServers []Instance

	lockFile  string
	logFile   string
	errFile   string
	magicFile string
	basicDir  string

	conf      *config.ConfRedisKeyLifeCycle
	HotKeyRp  report.Reporter
	BigKeyRp  report.Reporter
	KeyModeRp report.Reporter
	KeyLifeRp report.Reporter

	// tempKeysFiles 本轮分析过程中产生的临时 keys 文件(v.*.keys),任意退出路径统一清理
	tempKeysFiles []string
}

// NewKeyStatTask new a task
func NewKeyStatTask(servers []Instance, conf *config.ConfRedisKeyLifeCycle,
	hkRp report.Reporter, bkRp report.Reporter, kmRp report.Reporter, klRp report.Reporter) *Task {

	return &Task{
		statServers: servers,
		conf:        conf,
		HotKeyRp:    hkRp,
		BigKeyRp:    bkRp,
		KeyModeRp:   kmRp,
		KeyLifeRp:   klRp,
		logFile:     "tendis.keystat.log",
		errFile:     "tendis.keystat.err",
		lockFile:    "tendis.keystat.lock",
		magicFile:   "tendis.lifecycle.magic.done",
		basicDir:    fmt.Sprintf("%s/redis", consts.GetRedisDataDir()),
	}
}

// RunStat Main Entry
func (t *Task) RunStat() error {
	if err := os.Chdir(t.conf.StatDir); err != nil {
		mylog.Logger.Error(fmt.Sprintf("chdir failed :%+v", err))
		return err
	}
	path, _ := os.Getwd()
	mylog.Logger.Info(fmt.Sprintf("current work dir is %s instances:%+v", path, t.statServers))

	t.rotateFile(t.logFile)
	t.rotateFile(t.errFile)
	doneChan := make(chan struct{}, 1)
	util.LockFileOnStart(t.lockFile, doneChan)
	defer func() { doneChan <- struct{}{} }()

	// 兜底清理上次分析异常退出(进程被杀等)遗留的临时 keys 文件;此时已持有独占锁,清扫安全
	t.sweepStaleKeysFiles()
	// 无论本轮分析以何种方式退出(正常结束/出错返回/跳过实例),都清理产生的临时 keys 文件
	defer t.cleanTempKeysFiles()

	rstHash := map[string]interface{}{}
	cmdVer := fmt.Sprintf("%s version| grep build_date | awk '{print $3}'", consts.TendisKeyLifecycleBin)
	r1, _ := util.RunBashCmd(cmdVer, "", nil, time.Second)
	rstHash["tool_version"] = strings.TrimSuffix(r1, "\n")

	gStartTime := time.Now().Unix()
	for _, server := range t.statServers {
		if t.waitOrIgnore(server) {
			continue
		}

		t.setBasicVals(rstHash, server)
		if server.Role == "master" { // 热key统计入口
			if !t.conf.HotKeyConf.Enabled() {
				// 开关关闭时不写magic标记,重新启用后下次触发即可生效
				mylog.Logger.Info(fmt.Sprintf("hotkey analyse disabled by config, skip %s", server.Addr))
				continue
			}
			if exceed, qps := t.hotKeyQpsExceed(server); exceed {
				// QPS超阈值不写magic标记,下次触发(QPS降下来后)即可正常分析
				mylog.Logger.Info(fmt.Sprintf("hotkey analyse skipped, %s qps:%d exceed threshold:%d",
					server.Addr, qps, t.conf.HotKeyConf.QpsThreshold))
				continue
			}
			st := time.Now().Unix()
			rstHash["data_type"] = "tendis_hotkeys"
			rstHash["stime"] = time.Now().Format("2006-01-02 15:04:05")
			f, err := t.hotKeyWithMonitor(server)
			if err != nil {
				mylog.Logger.Warn(fmt.Sprintf("get hot keys failed %s:%+v", server.Addr, err))
				continue
			}
			rstHash["etime"] = time.Now().Format("2006-01-02 15:04:05")
			rstHash["check_cost"] = time.Now().Unix() - st
			err = t.sendAndReport(t.HotKeyRp, f)
			mylog.Logger.Warn(fmt.Sprintf("role master , do hot key analyse done.. :%s:%+v", server.Addr, err))
		} else if server.Role == "slave" { // 大key统计入口
			if !t.conf.BigKeyConf.Enabled() {
				// 开关关闭时不写magic标记,重新启用后下次触发即可生效
				mylog.Logger.Info(fmt.Sprintf("bigkey/keymode analyse disabled by config, skip %s", server.Addr))
				continue
			}
			st := time.Now().Unix()
			rstHash["stime"] = time.Now().Format("2006-01-02 15:04:05")
			statReports, dbsize, _, err := t.bigKeySmartStat(server)
			if err != nil {
				mylog.Logger.Warn(fmt.Sprintf("get big keys failed %s:%+v", server.Addr, err))
				continue
			}
			rstHash["etime"] = time.Now().Format("2006-01-02 15:04:05")
			rstHash["check_cost"] = time.Now().Unix() - st
			rstHash["keys_total"] = dbsize

			rstHash["data_type"] = "tendis_bigkeys"
			err = t.sendBigKeyReport(t.BigKeyRp, statReports)
			mylog.Logger.Warn(fmt.Sprintf("role slave , do big key analyse done.. :%s:%+v", server.Addr, err))

			rstHash["data_type"] = "tendis_keymod"
			err = t.sendKeyModeReport(t.KeyModeRp, statReports)
			mylog.Logger.Warn(fmt.Sprintf("role slave , do big key analyse done.. :%s:%+v", server.Addr, err))
		} else {
			mylog.Logger.Error(fmt.Sprintf("unkown server role %s:%s", server.Addr, server.Role))
		}
		statDetail, _ := json.Marshal(rstHash)
		t.KeyLifeRp.AddRecord(string(statDetail), false)
		fh, _ := os.OpenFile(t.magicFile, os.O_APPEND|os.O_WRONLY, 0644)
		write := bufio.NewWriter(fh)
		if _, err := write.WriteString(fmt.Sprintf("%s %d\n", rstHash["data_type"], server.Port)); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("append magic file failed %s:%+v", t.magicFile, err))
		} else {
			write.Flush()
		}
		fh.Close()
	}

	mylog.Logger.Info(fmt.Sprintf("keylifecycle total cost :%d", time.Now().Unix()-gStartTime))
	return nil
}

func (t *Task) setBasicVals(rstHash map[string]interface{}, server Instance) {
	rstHash["ip"] = server.IP
	rstHash["port"] = server.Port
	rstHash["domain"] = server.Domain
	rstHash["app"] = server.App
	rstHash["role"] = server.Role

	if strings.Contains(server.Version, "tendisplus") {
		rstHash["redis_type"] = "tendis_plus"
	} else if strings.Contains(server.Version, "TRedis") {
		rstHash["redis_type"] = "tendis_ssd"
	} else {
		rstHash["redis_type"] = "tendis_cache"
	}
}

func (t *Task) rotateFile(f string) {
	for i := 1; i < 2; i++ {
		oldFile := fmt.Sprintf("%d.%s", i, f)
		os.Rename(f, oldFile)
	}
}

// addTempKeysFile 登记分析过程中产生的临时 keys 文件, 确保任意退出路径都能被清理
func (t *Task) addTempKeysFile(fname string) {
	t.tempKeysFiles = append(t.tempKeysFiles, fname)
}

// cleanTempKeysFiles 清理本轮分析登记的临时 keys 文件.
// 文件若已被 statRawKeysFileDetail 正常删除则忽略; 剩余的(出错/跳过路径遗留)在此统一兜底删除
func (t *Task) cleanTempKeysFiles() {
	for _, f := range t.tempKeysFiles {
		if err := os.Remove(f); err != nil {
			if os.IsNotExist(err) {
				continue
			}
			mylog.Logger.Warn(fmt.Sprintf("remove temp keys file %s failed:%+v", f, err))
			continue
		}
		mylog.Logger.Info(fmt.Sprintf("remove temp keys file %s success", f))
	}
	t.tempKeysFiles = nil
}

// sweepStaleKeysFiles 清理历史遗留的临时 keys 文件(v.*.keys).
// 上次分析异常退出(进程被杀、panic 后未走完 defer 等)未能正常清理时, 由本轮启动时兜底清理
func (t *Task) sweepStaleKeysFiles() {
	matches, err := filepath.Glob(tempKeysFilePattern)
	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("glob temp keys files(%s) failed:%+v", tempKeysFilePattern, err))
		return
	}
	for _, f := range matches {
		if err := os.Remove(f); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("remove stale temp keys file %s failed:%+v", f, err))
			continue
		}
		mylog.Logger.Info(fmt.Sprintf("remove stale temp keys file %s success", f))
	}
}

// hotKeyQpsExceed 检查实例QPS是否超过热key分析阈值
// 返回 exceed=true 时应跳过热key分析(保护高负载实例); 阈值未配置时由配置加载补默认10000,
// 此处 <=0 不检查仅作为兜底保护; INFO获取失败视为超限跳过(实例可能正高负载),只影响当天分析
func (t *Task) hotKeyQpsExceed(server Instance) (exceed bool, qps int64) {
	threshold := t.conf.HotKeyConf.QpsThreshold
	if threshold <= 0 {
		return false, 0
	}
	info, err := server.Cli.Info("stats")
	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("hotkey qps check failed %s:%+v, skip analyse for safety", server.Addr, err))
		return true, 0
	}
	qpsStr := strings.TrimSpace(info["instantaneous_ops_per_sec"])
	if qpsStr == "" {
		mylog.Logger.Warn(fmt.Sprintf("hotkey qps check failed %s: info stats no instantaneous_ops_per_sec", server.Addr))
		return true, 0
	}
	qps, err = strconv.ParseInt(qpsStr, 10, 64)
	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("hotkey qps check failed %s: parse qps %q err:%+v", server.Addr, qpsStr, err))
		return true, 0
	}
	return qps > threshold, qps
}

// hotKeyWithMonitor 热key 分析
func (t *Task) hotKeyWithMonitor(server Instance) (string, error) {
	hkfile := fmt.Sprintf("tendis.keystat.hotkeys.%d.info", server.Port)
	t.rotateFile(hkfile)

	mylog.Logger.Info(fmt.Sprintf("do hot key analyse : %s", server.Addr))
	hkCmd := fmt.Sprintf("%s hotkeys -A %s -S %s -a '%s' -D %s --raw -o %s > %s 2>&1",
		consts.TendisKeyLifecycleBin, server.App, server.Addr, server.Password, server.Domain, t.logFile, hkfile)
	hkCmdLog := fmt.Sprintf("%s hotkeys -A %s -S %s -a '%s' -D %s --raw -o %s > %s 2>&1",
		consts.TendisKeyLifecycleBin, server.App, server.Addr, "xxxxx", server.Domain, t.logFile, hkfile)

	mylog.Logger.Info(fmt.Sprintf("exec cmd : %s", hkCmdLog))
	r1, r2 := util.RunBashCmd(hkCmd, "", nil, time.Second*(time.Duration(t.conf.HotKeyConf.Duration+10)))
	mylog.Logger.Info(fmt.Sprintf("tools executed with result %s:%s:%s", server.Addr, r1, r2))

	return hkfile, nil
}

// statReport 一次 key 统计分析产出的报告文件
type statReport struct {
	bkFile string // bigkey 报告文件
	kmFile string // keymode 报告文件
	db     int    // tendisplus kvstore 编号；-1 表示实例维度（非 kvstore 维度）
}

// bigKeySmartStat big / mode 入口
// tendisplus 按 kvstore 维度分析，每个 kvstore 独立产出报告文件；其余类型返回实例级报告文件
func (t *Task) bigKeySmartStat(server Instance) (statReports []statReport, dbsize, step int64, err error) {
	if strings.Contains(server.Version, "TRedis") {
		bkfile := fmt.Sprintf("tendis.keystat.bigkeys.%d.info", server.Port)
		kmfile := fmt.Sprintf("tendis.keystat.keymode.%d.info", server.Port)
		t.rotateFile(bkfile)
		t.rotateFile(kmfile)
		dbsize, step, err = t.bigAndMode4TendisSSD(server, bkfile, kmfile)
		return []statReport{{bkFile: bkfile, kmFile: kmfile, db: -1}}, dbsize, step, err
	} else if strings.Contains(server.Version, "-rocksdb-") {
		return t.bigAndMode4TendisPlus(server)
	}

	bkfile := fmt.Sprintf("tendis.keystat.bigkeys.%d.info", server.Port)
	kmfile := fmt.Sprintf("tendis.keystat.keymode.%d.info", server.Port)
	t.rotateFile(bkfile)
	t.rotateFile(kmfile)

	var useFastRdbStat bool
	osMem, _ := mem.VirtualMemory()
	if t.conf.BigKeyConf.MemMaxUsage != 0 {
		MemUsedPercent = t.conf.BigKeyConf.MemMaxUsage
	}
	if t.conf.BigKeyConf.UseRdb && osMem.UsedPercent < float64(MemUsedPercent) {
		useFastRdbStat = true
	}
	mylog.Logger.Info(fmt.Sprintf("do stats keys %s: use Rdb: (config_rdb:%+v,mem_current:%+v) Mem:%+v",
		server.Addr, t.conf.BigKeyConf.UseRdb, useFastRdbStat, osMem))

	if useFastRdbStat {
		// 如果RDB save 正在跑（不是我自己触发的，那么需要等等)
		dbsize, step, err = t.bigKeyWithRdb4Cache(server, bkfile, kmfile)
	} else {
		// 如果AOF 不存在， 那么还的使用 RDB 来统计
		dbsize, step, err = t.bigKeyWithAof4Cache(server, bkfile, kmfile)
	}
	return []statReport{{bkFile: bkfile, kmFile: kmfile, db: -1}}, dbsize, step, err
}

// bigKeyWithRdb4Cache  -- 大key & key 模式分析
func (t *Task) bigKeyWithRdb4Cache(server Instance, bkfile, kmfile string) (int64, int64, error) {
	if err := server.Cli.BgSaveAndWaitForFinish(); err != nil {
		return 0, 0, err
	}

	allkeys := fmt.Sprintf("v.%d.keys", server.Port)
	t.addTempKeysFile(allkeys)
	cmdKeys := fmt.Sprintf("%s rdbstat -f %s/%d/data/dump.rdb > %s 2>&1",
		consts.TendisKeyLifecycleBin, t.basicDir, server.Port, allkeys)
	mylog.Logger.Info(fmt.Sprintf("do parse keys %s:%s", server.Addr, cmdKeys))
	if _, err := util.RunBashCmd(cmdKeys, "", nil, time.Hour); err != nil {
		return 0, 0, err
	}
	return t.statRawKeysFileDetail(allkeys, bkfile, kmfile, server)
}

func (t *Task) bigKeyWithAof4Cache(server Instance, bkfile, kmfile string) (int64, int64, error) {
	if err := server.Cli.BgRewriteAOFAndWaitForDone(); err != nil {
		mylog.Logger.Warn(fmt.Sprintf("aof rewrite failed :%+v", err))
		return 0, 0, err
	}

	allkeys := fmt.Sprintf("v.%d.keys", server.Port)
	t.addTempKeysFile(allkeys)
	cmdKeys := fmt.Sprintf("%s parseaof -f %s/%d/data/appendonly.aof > %s 2>&1",
		consts.TendisKeyLifecycleBin, t.basicDir, server.Port, allkeys)
	mylog.Logger.Info(fmt.Sprintf("do parse keys %s:%s", server.Addr, cmdKeys))
	if _, err := util.RunBashCmd(cmdKeys, "", nil, time.Hour); err != nil {
		return 0, 0, err
	}

	dbsize, err := server.Cli.DbSize()
	if err != nil {
		return 0, 0, err
	}

	step, slptime, sample, confidence, adjfactor := getStatToolParams(dbsize)
	cmdExec := fmt.Sprintf(
		"cat %s | %s keystat --stdin --raw -B %s -M %s -o %s -S %s -a '%s' -A %s -D %s "+
			"--step %d --keymodetop 30 --samples %d --confidence %d --adjfactor %d --duration %d > %s 2>&1",
		allkeys, consts.TendisKeyLifecycleBin, bkfile, kmfile, t.logFile,
		server.Addr, server.Password, server.App, server.Domain,
		step, sample, confidence, adjfactor, slptime, t.errFile)
	cmdExecLog := fmt.Sprintf(
		"cat %s | %s keystat --stdin --raw -B %s -M %s -o %s -S %s -a '%s' -A %s -D %s "+
			"--step %d --keymodetop 30 --samples %d --confidence %d --adjfactor %d --duration %d > %s 2>&1",
		allkeys, consts.TendisKeyLifecycleBin, bkfile, kmfile, t.logFile,
		server.Addr, "xxxx", server.App, server.Domain,
		step, sample, confidence, adjfactor, slptime, t.errFile)
	mylog.Logger.Info(fmt.Sprintf("do stats keys %s:%s", server.Addr, cmdExecLog))
	_, err = util.RunBashCmd(cmdExec, "", nil, time.Second*time.Duration(t.conf.BigKeyConf.Duration))
	if er1 := os.Remove(allkeys); er1 != nil {
		mylog.Logger.Warn(fmt.Sprintf("remove keys file err %s:+%v", allkeys, er1))
	}
	return dbsize, step, err
}

// bigAndMode4TendisSSD for tendis ssd
func (t *Task) bigAndMode4TendisSSD(server Instance, bkfile, kmfile string) (int64, int64, error) {
	ldbTool := consts.LdbWithV38Bin
	if _, smallVer := tendisSSDVersion2Int(server.Version); smallVer >= 1021700 {
		ldbTool = consts.LdbWithV513Bin
	}

	rockkeys := fmt.Sprintf("v.%d.keys", server.Port)
	t.addTempKeysFile(rockkeys)
	exportStr := "export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/usr/local/redis/bin/deps &&"
	cmdScan := fmt.Sprintf("%s %s --db=%s/%d/data/rocksdb/ scan > %s 2>&1",
		exportStr, ldbTool, t.basicDir, server.Port, rockkeys)
	if _, err := util.RunBashCmd(cmdScan, "", nil, time.Hour); err != nil {
		mylog.Logger.Warn(fmt.Sprintf("exec cmd: %s failed: %+v", cmdScan, err))
	}
	return t.statRawKeysFileDetail(rockkeys, bkfile, kmfile, server)
}

// bigAndMode4TendisPlus tendisplus 大key/keymode 统计
// 按 kvstore 维度分析：每个 kvstore（独立 rocksdb）单独 tscan 导出 keys、单独执行 keystat，
// 各自产出独立的 bigkeys/keymode 报告文件，不再将整个实例的 key 合并成一份后统一分析
func (t *Task) bigAndMode4TendisPlus(server Instance) (statReports []statReport, dbsize, step int64, err error) {
	kvstoreCount, err := server.Cli.GetKvstoreCount()
	if err != nil {
		return nil, 0, 0, err
	}
	mylog.Logger.Info(fmt.Sprintf("tendisplus %s kvstorecount:%d, do stat by each kvstore",
		server.Addr, kvstoreCount))

	statReports = make([]statReport, 0, kvstoreCount)
	dbsize = 0
	for db := 0; db < kvstoreCount; db++ {
		rocksdir := fmt.Sprintf("%s/%d/data/db/%d/", t.basicDir, server.Port, db)
		rockkeys := fmt.Sprintf("v.%d.%d.keys", server.Port, db)
		t.addTempKeysFile(rockkeys)
		cmdScan := fmt.Sprintf("%s --db=%s tscan > %s 2>&1", consts.LdbTendisplusBin, rocksdir, rockkeys)
		mylog.Logger.Info(fmt.Sprintf("do scan sst keys %s kvstore:%d: %s", server.Addr, db, cmdScan))
		if _, scanErr := util.RunBashCmd(cmdScan, "", nil, time.Hour); scanErr != nil {
			mylog.Logger.Warn(fmt.Sprintf("exec cmd: %s failed: %+v, skip kvstore:%d", cmdScan, scanErr, db))
			continue
		}

		bkfile := fmt.Sprintf("tendis.keystat.bigkeys.%d.%d.info", server.Port, db)
		kmfile := fmt.Sprintf("tendis.keystat.keymode.%d.%d.info", server.Port, db)
		t.rotateFile(bkfile)
		t.rotateFile(kmfile)

		keyLines, dbStep, statErr := t.statRawKeysFileDetail(rockkeys, bkfile, kmfile, server)
		if statErr != nil {
			return nil, 0, 0, statErr
		}
		dbsize += keyLines
		step = dbStep
		statReports = append(statReports, statReport{bkFile: bkfile, kmFile: kmfile, db: db})
	}
	return statReports, dbsize, step, nil
}

func (t *Task) statRawKeysFileDetail(keysFile string, bkFile string, kmFile string, server Instance) (int64, int64,
	error) {
	var err error
	keyLines, _ := util.GetFileLines(keysFile)
	step, slptime, sample, confidence, adjfactor := getStatToolParams(keyLines)

	cmdExec := fmt.Sprintf(
		"cat %s | %s keystat --ssd --stdin --raw -B %s -M %s -o %s -S %s -a '%s' -A %s -D %s "+
			"--step %d --keymodetop 30 --samples %d --confidence %d --adjfactor %d --duration %d > %s 2>&1",
		keysFile, consts.TendisKeyLifecycleBin, bkFile, kmFile, t.logFile,
		server.Addr, server.Password, server.App, server.Domain,
		step, sample, confidence, adjfactor, slptime, t.errFile)
	cmdExecLog := fmt.Sprintf(
		"cat %s | %s keystat --ssd --stdin --raw -B %s -M %s -o %s -S %s -a '%s' -A %s -D %s "+
			"--step %d --keymodetop 30 --samples %d --confidence %d --adjfactor %d --duration %d > %s 2>&1",
		keysFile, consts.TendisKeyLifecycleBin, bkFile, kmFile, t.logFile,
		server.Addr, "xxxx", server.App, server.Domain,
		step, sample, confidence, adjfactor, slptime, t.errFile)
	mylog.Logger.Info(fmt.Sprintf("do stats keys %s:%s", server.Addr, cmdExecLog))
	_, err = util.RunBashCmd(cmdExec, "", nil, time.Second*time.Duration(t.conf.BigKeyConf.Duration))
	if er1 := os.Remove(keysFile); er1 != nil {
		mylog.Logger.Warn(fmt.Sprintf("remove keys file err %s:+%v", keysFile, er1))
	}
	return keyLines, step, err
}

func (t *Task) waitOrIgnore(server Instance) bool {
	// 1.  waitDisk
	var diskOk bool
	for i := 0; i < 100; i++ {
		usage, _ := util.GetLocalDirDiskUsg(t.conf.StatDir)
		// {TotalSize:105620869120 UsedSize:8513855488 AvailSize:92688084992 UsageRatio:8}
		mylog.Logger.Info(fmt.Sprintf("current dir %s usage :%+v (max:%d%%)",
			t.conf.StatDir, usage, t.conf.BigKeyConf.DiskMaxUsage))
		if usage.UsageRatio < t.conf.BigKeyConf.DiskMaxUsage {
			diskOk = true
			break
		}
		time.Sleep(time.Minute)
	}
	if !diskOk {
		mylog.Logger.Warn(fmt.Sprintf("current disk not enough , byebye (great than:%d%%)", t.conf.BigKeyConf.DiskMaxUsage))
		return true
	}
	// 2.  check aleary stated .
	fh, err := os.Open(t.magicFile)
	if os.IsNotExist(err) {
		ioutil.WriteFile(t.magicFile, []byte(fmt.Sprintf("MAGIC_%s", time.Now().Format("20060102"))), 0644)
		return false
	}
	ct, err := ioutil.ReadAll(fh)
	if err != nil {
		mylog.Logger.Warn(fmt.Sprintf("read magic file %s err :%+v", t.magicFile, err))
		return false
	}

	lines := strings.Split(string(ct), "\n")
	for i := 0; i < len(lines); i++ {
		if i == 0 {
			if !strings.Contains(lines[i], "MAGIC_") {
				ioutil.WriteFile(t.magicFile, []byte(fmt.Sprintf("MAGIC_%s\n", time.Now().Format("20060102"))), 0644)
				mylog.Logger.Warn(fmt.Sprintf("bad magic file format first line not magic :%s", lines[i]))
				return false
			}
			if !strings.Contains(lines[i], fmt.Sprintf("MAGIC_%s", time.Now().Format("20060102"))) {
				ioutil.WriteFile(t.magicFile, []byte(fmt.Sprintf("MAGIC_%s", time.Now().Format("20060102"))), 0644)
				mylog.Logger.Warn(fmt.Sprintf("stats not today  :%s", lines[i]))
				return false
			}
		}
		words := strings.Split(lines[i], " ")
		if words[0] == strconv.Itoa(server.Port) {
			return true
		}
	}
	return false
}

func (t *Task) sendAndReport(ctp report.Reporter, fname string) error {
	if ctp == nil {
		return fmt.Errorf("report nil, ignore report :%s", fname)
	}

	fh, err := os.Open(fname)
	if err != nil {
		return err
	}
	defer fh.Close()

	reader := bufio.NewReader(fh)
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
		if err := ctp.AddRecord(string(line), true); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("add to reporter failed:%+v", err))
		}
	}
	return nil
}

// keyModeSamplesMax keymode 记录 samples 字段聚合后保留的最大样本数
const keyModeSamplesMax = 3

// splitKvstoreReports 按是否 kvstore 维度(tendisplus)拆分报告
func splitKvstoreReports(statReports []statReport) (kvReports, instReports []statReport) {
	for _, rpt := range statReports {
		if rpt.db >= 0 {
			kvReports = append(kvReports, rpt)
		} else {
			instReports = append(instReports, rpt)
		}
	}
	return
}

// sendBigKeyReport 上报大key统计报告
// tendisplus: 各 kvstore 的报告先聚合为实例维度,再统一写入上报文件;
// 其余类型: 报告文件直接透传写入
func (t *Task) sendBigKeyReport(rp report.Reporter, statReports []statReport) error {
	kvReports, instReports := splitKvstoreReports(statReports)
	for _, rpt := range instReports {
		if err := t.sendAndReport(rp, rpt.bkFile); err != nil {
			return err
		}
	}
	if len(kvReports) == 0 {
		return nil
	}
	return t.aggBigKeysByInstance(rp, kvReports)
}

// sendKeyModeReport 上报 key模式统计报告
// tendisplus: 各 kvstore 的报告先聚合为实例维度,再统一写入上报文件;
// 其余类型: 报告文件直接透传写入
func (t *Task) sendKeyModeReport(rp report.Reporter, statReports []statReport) error {
	kvReports, instReports := splitKvstoreReports(statReports)
	for _, rpt := range instReports {
		if err := t.sendAndReport(rp, rpt.kmFile); err != nil {
			return err
		}
	}
	if len(kvReports) == 0 {
		return nil
	}
	return t.aggKeyModeByInstance(rp, kvReports)
}

// aggBigKeysByInstance 将 tendisplus 各 kvstore 的大key榜单聚合为实例维度后统一写入:
// 按 sortby 维度分组,合并所有 kvstore 的记录,按 valsize 降序重排并重编 top_idx,截取每个维度的 topN.
// 同一个 key 只存在于一个 kvstore 中,且实例 topN 的大key必然也在其所属 kvstore 的 topN 内,
// 因此聚合结果即为实例维度的真实 topN; 记录中保留 db 字段标识大key所在的 kvstore.
func (t *Task) aggBigKeysByInstance(rp report.Reporter, reports []statReport) error {
	if rp == nil {
		return fmt.Errorf("report nil, ignore bigkeys aggregate report")
	}
	type bigKeyEntry struct {
		record map[string]interface{}
		valsz  float64
	}
	groups := make(map[string][]bigKeyEntry) // sortby -> 记录列表
	topLimit := make(map[string]int)         // sortby -> 单个 kvstore 报告中该维度的记录数(取最大)
	baseIdx := make(map[string]int)          // sortby -> top_idx 起始值(兼容 0/1 起始编号)

	for _, rpt := range reports {
		records, err := readReportLines(rpt.bkFile)
		if err != nil {
			return err
		}
		cntBySortby := make(map[string]int)
		for _, m := range records {
			sortby, _ := m["sortby"].(string)
			cntBySortby[sortby]++
			idx := int(toFloat(m["top_idx"]))
			if b, ok := baseIdx[sortby]; !ok || idx < b {
				baseIdx[sortby] = idx
			}
			m["db"] = rpt.db
			groups[sortby] = append(groups[sortby], bigKeyEntry{record: m, valsz: toFloat(m["valsize"])})
		}
		for sortby, cnt := range cntBySortby {
			if cnt > topLimit[sortby] {
				topLimit[sortby] = cnt
			}
		}
	}

	for sortby, entries := range groups {
		sort.SliceStable(entries, func(i, j int) bool { return entries[i].valsz > entries[j].valsz })
		if limit := topLimit[sortby]; limit > 0 && len(entries) > limit {
			entries = entries[:limit]
		}
		mylog.Logger.Info(fmt.Sprintf("bigkeys aggregate by instance, sortby:%s, records:%d", sortby, len(entries)))
		for i := range entries {
			entries[i].record["top_idx"] = baseIdx[sortby] + i
			if err := addRecordJSON(rp, entries[i].record); err != nil {
				mylog.Logger.Warn(fmt.Sprintf("add to reporter failed:%+v", err))
			}
		}
	}
	return nil
}

// aggKeyModeByInstance 将 tendisplus 各 kvstore 的 key模式统计聚合为实例维度后统一写入:
// 按 (key_type, partten) 合并: count/keys_expired/keys_nottl 累加, avg_fileds/avg_valsize 按 count 加权平均,
// max_fileds/max_valsize 取最大, sample_raito 取最大, samples 去重合并,
// 最后按 count 降序重排并重编 top_idx, 截取 topN.
// 注: partten 至少需进入某个 kvstore 的 topN 才会被聚合到, 结果为实例维度的近似 topN
func (t *Task) aggKeyModeByInstance(rp report.Reporter, reports []statReport) error {
	if rp == nil {
		return fmt.Errorf("report nil, ignore keymode aggregate report")
	}
	type keyModAgg struct {
		record      map[string]interface{}
		count       float64
		keysExpired float64
		keysNottl   float64
		sumCntFlds  float64
		sumCntVal   float64
		maxFileds   float64
		maxValsz    float64
		sampleRaito float64
		samples     []string
		sampleSet   map[string]struct{}
	}
	aggs := make(map[string]*keyModAgg)
	var order []string // 保持首次出现顺序,保证排序稳定
	var topLimit, baseIdx int
	baseIdxSet := false

	for _, rpt := range reports {
		records, err := readReportLines(rpt.kmFile)
		if err != nil {
			return err
		}
		for _, m := range records {
			gkey := fmt.Sprintf("%v\x00%v", m["key_type"], m["partten"])
			agg, ok := aggs[gkey]
			if !ok {
				// 以首次出现的记录为基础,保留 addr/app/domain 等实例级字段
				agg = &keyModAgg{record: m, sampleSet: make(map[string]struct{})}
				aggs[gkey] = agg
				order = append(order, gkey)
			}
			c := toFloat(m["count"])
			agg.count += c
			agg.keysExpired += toFloat(m["keys_expired"])
			agg.keysNottl += toFloat(m["keys_nottl"])
			agg.sumCntFlds += c * toFloat(m["avg_fileds"])
			agg.sumCntVal += c * toFloat(m["avg_valsize"])
			if v := toFloat(m["max_fileds"]); v > agg.maxFileds {
				agg.maxFileds = v
			}
			if v := toFloat(m["max_valsize"]); v > agg.maxValsz {
				agg.maxValsz = v
			}
			if v := toFloat(m["sample_raito"]); v > agg.sampleRaito {
				agg.sampleRaito = v
			}
			for _, s := range toStringSlice(m["samples"]) {
				if _, ok := agg.sampleSet[s]; ok {
					continue
				}
				agg.sampleSet[s] = struct{}{}
				if len(agg.samples) < keyModeSamplesMax {
					agg.samples = append(agg.samples, s)
				}
			}
			// @timestamp 保留最新
			if ts, _ := m["@timestamp"].(string); ts != "" {
				if old, _ := agg.record["@timestamp"].(string); ts > old {
					agg.record["@timestamp"] = ts
				}
			}
			if idx := int(toFloat(m["top_idx"])); !baseIdxSet || idx < baseIdx {
				baseIdx = idx
				baseIdxSet = true
			}
		}
		if len(records) > topLimit {
			topLimit = len(records)
		}
	}

	entries := make([]*keyModAgg, 0, len(order))
	for _, gkey := range order {
		entries = append(entries, aggs[gkey])
	}
	sort.SliceStable(entries, func(i, j int) bool { return entries[i].count > entries[j].count })
	if topLimit > 0 && len(entries) > topLimit {
		entries = entries[:topLimit]
	}
	mylog.Logger.Info(fmt.Sprintf("keymode aggregate by instance, patterns:%d", len(entries)))

	for i, e := range entries {
		e.record["count"] = int64(e.count)
		e.record["keys_expired"] = int64(e.keysExpired)
		e.record["keys_nottl"] = int64(e.keysNottl)
		if e.count > 0 {
			e.record["avg_fileds"] = int64(e.sumCntFlds / e.count)
			e.record["avg_valsize"] = int64(e.sumCntVal / e.count)
		}
		e.record["max_fileds"] = int64(e.maxFileds)
		e.record["max_valsize"] = int64(e.maxValsz)
		e.record["sample_raito"] = e.sampleRaito
		e.record["samples"] = e.samples
		e.record["top_idx"] = baseIdx + i
		if err := addRecordJSON(rp, e.record); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("add to reporter failed:%+v", err))
		}
	}
	return nil
}

// readReportLines 逐行读取报告文件并解析为 JSON 对象, 非 JSON 行跳过
func readReportLines(fname string) ([]map[string]interface{}, error) {
	fh, err := os.Open(fname)
	if err != nil {
		return nil, err
	}
	defer fh.Close()

	var records []map[string]interface{}
	reader := bufio.NewReader(fh)
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				break
			}
			return nil, err
		}
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		var m map[string]interface{}
		if err := json.Unmarshal([]byte(trimmed), &m); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("skip non-json line in %s", fname))
			continue
		}
		records = append(records, m)
	}
	return records, nil
}

// addRecordJSON 将记录序列化为 JSON 行写入上报者
func addRecordJSON(rp report.Reporter, record map[string]interface{}) error {
	line, err := json.Marshal(record)
	if err != nil {
		return err
	}
	return rp.AddRecord(string(line)+"\n", true)
}

// toFloat 宽松数值转换
func toFloat(v interface{}) float64 {
	switch x := v.(type) {
	case float64:
		return x
	case int:
		return float64(x)
	case int64:
		return float64(x)
	case json.Number:
		f, _ := x.Float64()
		return f
	case string:
		f, _ := strconv.ParseFloat(x, 64)
		return f
	default:
		return 0
	}
}

// toStringSlice 宽松字符串切片转换
func toStringSlice(v interface{}) []string {
	switch x := v.(type) {
	case []string:
		return x
	case []interface{}:
		ret := make([]string, 0, len(x))
		for _, item := range x {
			if s, ok := item.(string); ok {
				ret = append(ret, s)
			}
		}
		return ret
	default:
		return nil
	}
}
