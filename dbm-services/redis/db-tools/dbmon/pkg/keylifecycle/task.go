package keylifecycle

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
)

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
			st := time.Now().Unix()
			rstHash["stime"] = time.Now().Format("2006-01-02 15:04:05")
			fbig, fmod, dbsize, _, err := t.bigKeySmartStat(server)
			if err != nil {
				mylog.Logger.Warn(fmt.Sprintf("get big keys failed %s:%+v", server.Addr, err))
				continue
			}
			rstHash["etime"] = time.Now().Format("2006-01-02 15:04:05")
			rstHash["check_cost"] = time.Now().Unix() - st
			rstHash["keys_total"] = dbsize

			rstHash["data_type"] = "tendis_bigkeys"
			err = t.sendAndReport(t.BigKeyRp, fbig)
			mylog.Logger.Warn(fmt.Sprintf("role slave , do big key analyse done.. :%s:%+v", server.Addr, err))

			rstHash["data_type"] = "tendis_keymod"
			err = t.sendAndReport(t.KeyModeRp, fmod)
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

// hotKeyWithMonitor 热key 分析
func (t *Task) hotKeyWithMonitor(server Instance) (string, error) {
	hkfile := fmt.Sprintf("tendis.keystat.hotkeys.%d.info", server.Port)
	t.rotateFile(hkfile)

	mylog.Logger.Info(fmt.Sprintf("do hot key analyse : %s", server.Addr))
	hkCmd := fmt.Sprintf("%s hotkeys -A %s -S %s -a %s -D %s --raw -o %s > %s 2>&1",
		consts.TendisKeyLifecycleBin, server.App, server.Addr, server.Password, server.Domain, t.logFile, hkfile)

	mylog.Logger.Info(fmt.Sprintf("exec cmd : %s", hkCmd))
	r1, r2 := util.RunBashCmd(hkCmd, "", nil, time.Second*(time.Duration(t.conf.HotKeyConf.Duration+10)))
	mylog.Logger.Info(fmt.Sprintf("tools executed with result %s:%s:%s", server.Addr, r1, r2))

	return hkfile, nil
}

// bigKeySmartStat big / mode 入口
func (t *Task) bigKeySmartStat(server Instance) (string, string, int64, int64, error) {
	bkfile := fmt.Sprintf("tendis.keystat.bigkeys.%d.info", server.Port)
	kmfile := fmt.Sprintf("tendis.keystat.keymode.%d.info", server.Port)
	t.rotateFile(bkfile)
	t.rotateFile(kmfile)
	var dbsize, step int64
	var err error

	if strings.Contains(server.Version, "TRedis") {
		dbsize, step, err = t.bigAndMode4TendisSSD(server, bkfile, kmfile)
	} else if strings.Contains(server.Version, "-rocksdb-") {
		dbsize, step, err = t.bigAndMode4TendisPlus(server, bkfile, kmfile)
	} else {
		if !util.FileExists(fmt.Sprintf("%s/redis/%d/data/appendonly.aof", t.basicDir, server.Port)) &&
			t.conf.BigKeyConf.UseRdb {
			// 如果RDB save 正在跑（不是我自己触发的，那么需要等等)
			dbsize, step, err = t.bigKeyWithRdb4Cache(server, bkfile, kmfile)
		} else {
			// 如果AOF 不存在， 那么还的使用 RDB 来统计
			dbsize, step, err = t.bigKeyWithAof4Cache(server, bkfile, kmfile)
		}
	}
	return bkfile, kmfile, dbsize, step, err
}

// bigKeyWithRdb4Cache  -- 大key & key 模式分析
func (t *Task) bigKeyWithRdb4Cache(server Instance, bkfile, kmfile string) (int64, int64, error) {
	if err := server.Cli.BgSaveAndWaitForFinish(); err != nil {
		return 0, 0, err
	}

	allkeys := fmt.Sprintf("v.%d.keys", server.Port)
	cmdKeys := fmt.Sprintf("%s rdbstat -f %s/%d/data/dump.rdb > %s 2>&1",
		consts.TendisKeyLifecycleBin, t.basicDir, server.Port, allkeys)
	if _, err := util.RunBashCmd(cmdKeys, "", nil, time.Hour); err != nil {
		return 0, 0, err
	}
	return t.statRawKeysFileDetail(allkeys, bkfile, kmfile, server)
}

func (t *Task) bigKeyWithAof4Cache(server Instance, bkfile, kmfile string) (int64, int64, error) {
	if err := server.Cli.BgRewriteAOFAndWaitForDone(); err != nil {
		return 0, 0, err
	}

	allkeys := fmt.Sprintf("v.%d.keys", server.Port)
	cmdKeys := fmt.Sprintf("%s parseaof -f %s/%d/data/appendonly.aof > %s 2>&1",
		consts.TendisKeyLifecycleBin, t.basicDir, server.Port, allkeys)
	if _, err := util.RunBashCmd(cmdKeys, "", nil, time.Hour); err != nil {
		return 0, 0, err
	}

	dbsize, err := server.Cli.DbSize()
	if err != nil {
		return 0, 0, err
	}

	step, slptime, sample, confidence, adjfactor := getStatToolParams(dbsize)
	cmdExec := fmt.Sprintf(
		"cat %s | %s keystat --stdin --raw -B %s -M %s -o %s -S %s -a %s -A %s -D %s "+
			"--step %d --keymodetop 100 --samples %d --confidence %d --adjfactor %d --duration %d > %s 2>&1",
		allkeys, consts.TendisKeyLifecycleBin, bkfile, kmfile, t.logFile,
		server.Addr, server.Password, server.App, server.Domain,
		step, sample, confidence, adjfactor, slptime, t.errFile)
	mylog.Logger.Info(fmt.Sprintf("do stats keys %s:%s", server.Addr, cmdExec))
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
	exportStr := "export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/usr/local/redis/bin/deps &&"
	cmdScan := fmt.Sprintf("%s %s --db=%s/%d/data/rocksdb/ scan > %s 2>&1",
		exportStr, ldbTool, t.basicDir, server.Port, rockkeys)
	if _, err := util.RunBashCmd(cmdScan, "", nil, time.Hour); err != nil {
		mylog.Logger.Warn(fmt.Sprintf("exec cmd: %s failed: %+v", cmdScan, err))
	}
	return t.statRawKeysFileDetail(rockkeys, bkfile, kmfile, server)
}

// bigAndMode4TendisPlus  -- here will do something
func (t *Task) bigAndMode4TendisPlus(server Instance, bkfile, kmfile string) (int64, int64, error) {
	kvstore, err := server.Cli.GetKvstoreCount()
	if err != nil {
		return 0, 0, err
	}

	rockkeys := fmt.Sprintf("v.%d.keys", server.Port)
	for db := 0; db < kvstore; db++ {
		rocksdir := fmt.Sprintf("%s/%d/data/db/%d/", t.basicDir, server.Port, db)
		cmdScan := fmt.Sprintf("%s --db=%s tscan >> %s 2>&1", consts.LdbTendisplusBin, rocksdir, rockkeys)
		mylog.Logger.Info(fmt.Sprintf("do scan sst keys %s :%d: %s", server.Addr, db, cmdScan))
		if _, err := util.RunBashCmd(cmdScan, "", nil, time.Hour); err != nil {
			mylog.Logger.Warn(fmt.Sprintf("exec cmd: %s failed: %+v", cmdScan, err))
		}
	}
	return t.statRawKeysFileDetail(rockkeys, bkfile, kmfile, server)
}

func (t *Task) statRawKeysFileDetail(keysFile string, bkFile string, kmFile string, server Instance) (int64, int64,
	error) {
	var err error
	keyLines, _ := util.GetFileLines(keysFile)
	step, slptime, sample, confidence, adjfactor := getStatToolParams(keyLines)

	cmdExec := fmt.Sprintf(
		"cat %s | %s keystat --ssd --stdin --raw -B %s -M %s -o %s -S %s -a %s -A %s -D %s "+
			"--step %d --keymodetop 100 --samples %d --confidence %d --adjfactor %d --duration %d > %s 2>&1",
		keysFile, consts.TendisKeyLifecycleBin, bkFile, kmFile, t.logFile,
		server.Addr, server.Password, server.App, server.Domain,
		step, sample, confidence, adjfactor, slptime, t.errFile)
	mylog.Logger.Info(fmt.Sprintf("do stats keys %s:%s", server.Addr, cmdExec))
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
				ioutil.WriteFile(t.magicFile, []byte(fmt.Sprintf("MAGIC_%s", time.Now().Format("20060102"))), 0644)
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
