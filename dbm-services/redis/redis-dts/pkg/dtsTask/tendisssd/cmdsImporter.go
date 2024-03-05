package tendisssd

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/redis/redis-dts/models/mysql/tendisdb"
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/dtsTask"
	"dbm-services/redis/redis-dts/util"

	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// CmdsImporterTask 命令导入task
type CmdsImporterTask struct {
	dtsTask.FatherTask
	DelFiles               []string   `json:"delFiles"`
	OutputFiles            []string   `json:"outputFiles"`
	ListFiles              []string   `json:"listFiles"`
	ExpireFiles            []string   `json:"expireFiles"`
	ImportLogDir           string     `json:"importLogDir"`
	DstProxyAddrs          []string   `json:"dstProxyAddrs"`
	DstProxyIterIdx        int32      `json:"dstProxyIterIdx"`
	DtsProxyMut            sync.Mutex `json:"-"` // 更新DstProxyAddrs时上锁
	DtsProxyLastUpdatetime time.Time  `json:"-"` // 最后更新DstProxyAddrs的时间
}

// TaskType task类型
func (task *CmdsImporterTask) TaskType() string {
	return constvar.CmdsImporterTaskType
}

// NextTask 下一个task类型
func (task *CmdsImporterTask) NextTask() string {
	return constvar.MakeSyncTaskType
}

// NewCmdsImporterTask 新建一个命令导入task
func NewCmdsImporterTask(row *tendisdb.TbTendisDTSTask) *CmdsImporterTask {
	return &CmdsImporterTask{
		FatherTask: dtsTask.NewFatherTask(row),
	}
}

// ImporterItem 命令导入项(为并发执行导入)
type ImporterItem struct {
	RedisClient   string            `json:"redisClient"`
	SQLFile       string            `json:"sqlFile"`
	DstPassword   string            `json:"dstPassword"`
	LogFile       string            `json:"logFile"`
	IgnoreErrlist []string          `json:"ignoreErrLsit"`
	ErrFile       string            `json:"errFile"`
	Err           error             `json:"err"`
	task          *CmdsImporterTask `json:"-"`
	Logger        *zap.Logger       `json:"-"`
}

// ToString ..
func (item *ImporterItem) ToString() string {
	ret, _ := json.Marshal(item)
	return string(ret)
}

// MaxRetryTimes 获取最大重试次数
func (item *ImporterItem) MaxRetryTimes() int {
	ret := viper.GetInt("importMaxRetryTimes")
	if ret <= 0 {
		ret = 5
	} else if ret >= 10 {
		ret = 10
	}
	return ret
}

// RetryAble 能否重复导入
func (item *ImporterItem) RetryAble() bool {
	if constvar.ListKeyFileReg.MatchString(item.SQLFile) {
		return false
	}
	return true
}

// IsWrongTypeErr ..
func (item *ImporterItem) IsWrongTypeErr(errData string) bool {
	errData = strings.TrimSpace(errData)
	lines := strings.Split(errData, "\n")
	for _, line01 := range lines {
		if strings.Contains(line01, constvar.WrongTypeOperationErr) == false {
			return false
		}
	}
	item.IgnoreErrlist = append(item.IgnoreErrlist, constvar.WrongTypeOperationErr)
	return true
}

// ErrorAbleToBeIgnored 能够忽略的错误
func (item *ImporterItem) ErrorAbleToBeIgnored(errData string) bool {
	return item.IsWrongTypeErr(errData)
}

// RunTask 执行导入task
func (item *ImporterItem) RunTask(task *CmdsImporterTask) {
	supPipeImport := task.IsSupportPipeImport()
	importTimeout := task.ImportTimeout()
	cmdTimeout := importTimeout + 60

	item.Logger.Info("开始执行导入...", zap.String("params", item.ToString()))
	maxRetryTimes := item.MaxRetryTimes()
	times := 0
	retryAble := item.RetryAble()
	dtsAddr := item.task.NextDstProxyAddr(false)
	for {
		times++
		importCmd := []string{"-c"}
		var grepStdoutCmd string
		list01 := strings.Split(dtsAddr, ":")
		if len(list01) != 2 {
			item.Logger.Error("DstAddr format not correct", zap.String("dstAddr", dtsAddr))
			item.Err = fmt.Errorf("DstAddr:%s format not corret", dtsAddr)
			return
		}
		dstIP := list01[0]
		dstPort := list01[1]
		if supPipeImport == true {
			importCmd = append(importCmd, fmt.Sprintf(
				"%s --no-auth-warning -h %s -p %s -a %s --pipe --pipe-timeout %d < %s 1>%s 2>%s",
				item.RedisClient, dstIP, dstPort, item.DstPassword, importTimeout, item.SQLFile, item.LogFile, item.ErrFile))
			grepStdoutCmd = fmt.Sprintf("grep -i 'errors' %s | { grep -v 'errors: 0' || true; } ", item.LogFile)
		} else {
			importCmd = append(importCmd, fmt.Sprintf("%s --no-auth-warning -h %s -p %s -a %s < %s 1>%s 2>%s",
				item.RedisClient, dstIP, dstPort, item.DstPassword, item.SQLFile, item.LogFile, item.ErrFile))
			grepStdoutCmd = fmt.Sprintf("grep -i 'Err' %s | { grep -v 'invalid DB index' || true; }", item.LogFile)
		}
		item.Logger.Info(fmt.Sprintf("第%d次导入文件,导入命令:%s", times, importCmd))
		_, item.Err = util.RunLocalCmd("bash", importCmd, "", nil, time.Duration(cmdTimeout)*time.Second, item.Logger)
		if item.Err != nil {
			errBytes, _ := ioutil.ReadFile(item.ErrFile)
			errStr := strings.TrimSpace(string(errBytes))
			if item.ErrorAbleToBeIgnored(errStr) == true {
				// 可忽略的错误
				item.Err = nil
				return
			}
			if retryAble && times <= maxRetryTimes {
				dtsAddr = item.task.NextDstProxyAddr(true)
				item.Logger.Error("导入出错,retry...", zap.Error(item.Err), zap.String("params", item.ToString()))
				continue
			}
			item.Logger.Error("导入出错", zap.Error(item.Err), zap.String("params", item.ToString()))
			return
		}
		grepRet, _ := util.RunLocalCmd("bash",
			[]string{"-c", grepStdoutCmd}, "", nil, 30*time.Second, item.Logger)
		if grepRet != "" && retryAble && times <= maxRetryTimes {
			item.Err = fmt.Errorf("import file:%s some error occur,pls check logfile:%s", item.SQLFile, item.LogFile)
			item.Logger.Error(item.Err.Error())
			dtsAddr = item.task.NextDstProxyAddr(true)
			continue
		} else if grepRet != "" {
			item.Err = fmt.Errorf("import file:%s some error occur,pls check logfile:%s", item.SQLFile, item.LogFile)
			item.Logger.Error(item.Err.Error())
			return
		}
		// 是否发生错误
		errBytes, _ := ioutil.ReadFile(item.ErrFile)
		errStr := strings.TrimSpace(string(errBytes))
		if errStr != "" {
			if item.ErrorAbleToBeIgnored(errStr) == true {
				return
			}
			if retryAble == true && times <= maxRetryTimes {
				item.Err = fmt.Errorf("import file:%s some error occur,pls check errfile:%s", item.SQLFile, item.ErrFile)
				item.Logger.Error(item.Err.Error())
				dtsAddr = item.task.NextDstProxyAddr(true)
				continue
			}
			item.Err = fmt.Errorf("import file:%s some error occur,pls check errfile:%s", item.SQLFile, item.ErrFile)
			item.Logger.Error(item.Err.Error())
			return
		}
		break
	}
}

// LookupDstRedisProxyAddrs ..
// 如果 task.RowData.DstCluster 是由 domain:port组成,则通过 net.lookup 得到其 task.DstProxyAddrs;
// 否则 task.DstProxyAddrs = []string{task.RowData.DstCluster}
func (task *CmdsImporterTask) LookupDstRedisProxyAddrs() {
	task.DtsProxyMut.Lock()
	defer task.DtsProxyMut.Unlock()

	task.DstProxyAddrs, task.Err = util.LookupDbDNSIPs(task.RowData.DstCluster)
	if task.Err != nil {
		task.Logger.Error(task.Err.Error())
		return
	}
	task.DtsProxyLastUpdatetime = time.Now().Local()
}

// NextDstProxyAddr 依次轮训 DstProxyAddrs
func (task *CmdsImporterTask) NextDstProxyAddr(refreshDns bool) string {
	if len(task.DstProxyAddrs) == 0 {
		return task.RowData.DstCluster
	}
	if refreshDns && time.Now().Local().Sub(task.DtsProxyLastUpdatetime).Seconds() > 10 {
		// 如果最近10秒内更新过 task.DstProxyAddrs,则不再次更新
		task.LookupDstRedisProxyAddrs()
		if task.Err != nil {
			// 如果发生错误,则直接返回 DtsServer addr
			task.Err = nil
			return task.RowData.DtsServer
		}
	}
	// 轮训 task.DstProxyAddrs
	if len(task.DstProxyAddrs) == 1 {
		return task.DstProxyAddrs[0]
	}
	idx := int(atomic.LoadInt32(&task.DstProxyIterIdx)) % len(task.DstProxyAddrs)
	targetAddr := task.DstProxyAddrs[idx]
	atomic.AddInt32(&task.DstProxyIterIdx, 1)
	return targetAddr
}

// NewImporterItem 单个文件导入
func (task *CmdsImporterTask) NewImporterItem(redisCli, keysFile, dstPasswd string) (item ImporterItem, err error) {
	baseName := filepath.Base(keysFile)
	importLogDir := task.getimportLogDir()
	item = ImporterItem{
		RedisClient: redisCli,
		SQLFile:     keysFile,
		task:        task,
		DstPassword: dstPasswd,
		LogFile:     filepath.Join(importLogDir, baseName+".log"),
		ErrFile:     filepath.Join(importLogDir, baseName+".err"),
		Logger:      task.Logger,
	}
	return
}

func (task *CmdsImporterTask) parallelImportV2(importTasks []*ImporterItem, concurrency int) ([]*ImporterItem, error) {
	wg := sync.WaitGroup{}

	if len(importTasks) == 0 {
		return importTasks, nil
	}

	if concurrency <= 0 {
		importTasks[0].Logger.Warn(fmt.Sprintf("parallelImportV2 concurrency:%d <= 0,now concurrency=1", concurrency))
		concurrency = 1
	}
	genChan := make(chan *ImporterItem)
	retChan := make(chan *ImporterItem)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	currentIndex := 0
	totalCnt := len(importTasks)
	ticker := time.NewTicker(600 * time.Second) // 每10分钟打印一次进度

	for worker := 0; worker < concurrency; worker++ {
		wg.Add(1)
		go func() {
			defer wg.Done()

			for importGo := range genChan {
				importGo.RunTask(task)
				select {
				case retChan <- importGo:
				case <-ctx.Done():
					return
				}
			}
		}()
	}
	go func() {
		defer close(genChan)

		for _, task01 := range importTasks {
			taskItem := task01
			select {
			case genChan <- taskItem:
			case <-ctx.Done():
				return
			}
		}
	}()

	go func() {
		wg.Wait()
		close(retChan)
	}()

	go func() {
		tick01 := time.NewTicker(10 * time.Second)
		ok01 := false
		for {
			select {
			case <-tick01.C:
				ok01 = true
				row01, err := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
				if err != nil {
					break
				}
				if row01 == nil {
					task.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", task.RowData.ID, row01)
					break
				}
				if row01.SyncOperate == constvar.RedisForceKillTaskTodo {
					// 用户选择强制终止,则终止所有导入
					task.SetSyncOperate(constvar.RedisForceKillTaskSuccess)
					task.Err = fmt.Errorf("%s...", constvar.RedisForceKillTaskSuccess)
					cancel()
					ok01 = false
					break
				}
			case <-ctx.Done():
				ok01 = false
				break
			}
			if !ok01 {
				break
			}
		}
	}()

	var retItem *ImporterItem
	errList := []string{}
	ignoreErrMap := make(map[string]bool) // 忽略的错误类型去重
	ignoreErrList := []string{}
	ok := false
	for {
		currentIndex++
		select {
		case retItem, ok = <-retChan:
			if !ok {
				break
			}
			if retItem.Err != nil {
				errList = append(errList, retItem.Err.Error())
				cancel() // 发生错误,及时退出
				ok = false
				break
			}
			for _, igErr := range retItem.IgnoreErrlist {
				ignoreErrMap[igErr] = true
			}
		case <-ticker.C:
			task.UpdateDbAndLogLocal("[%d/%d] import progress...", currentIndex, totalCnt)
			ok = true
			break
		case <-ctx.Done():
			ok = false
			break
		}
		if !ok {
			break
		}
	}
	for igErr := range ignoreErrMap {
		ignoreErrList = append(ignoreErrList, igErr)
	}
	task.SaveIgnoreErrs(ignoreErrList)

	if len(errList) > 0 {
		return importTasks, fmt.Errorf("import output fail fail")
	}
	return importTasks, nil
}

// SyncImport 同步导入
func (task *CmdsImporterTask) SyncImport(importTasks []*ImporterItem) ([]*ImporterItem, error) {
	currentIndex := 0
	totalCnt := len(importTasks)
	ignoreErrMap := make(map[string]bool) // 忽略的错误类型去重
	ignoreErrList := []string{}
	for _, import01 := range importTasks {
		importItem := import01
		task.Logger.Info(fmt.Sprintf("SyncImport====>%s", importItem.SQLFile))
	}
	for _, import01 := range importTasks {
		importItem := import01
		currentIndex++
		importItem.RunTask(task)
		if importItem.Err != nil {
			return importTasks, importItem.Err
		}
		for _, igErr := range importItem.IgnoreErrlist {
			ignoreErrMap[igErr] = true
		}
		if currentIndex%200 == 0 {
			task.UpdateDbAndLogLocal("[%d/%d] import progress...", currentIndex, totalCnt)
			row01, err := tendisdb.GetTaskByID(task.RowData.ID, task.Logger)
			if err != nil {
				continue
			}
			if row01 == nil {
				task.UpdateDbAndLogLocal("根据task_id:%d获取task row失败,row01:%v", task.RowData.ID, row01)
				continue
			}
			if row01.SyncOperate == constvar.RedisForceKillTaskTodo {
				// 用户选择强制终止,则终止所有导入
				task.SetSyncOperate(constvar.RedisForceKillTaskSuccess)
				task.Err = fmt.Errorf("%s...", constvar.RedisForceKillTaskSuccess)
				return importTasks, task.Err
			}
		}
	}
	for igErr := range ignoreErrMap {
		ignoreErrList = append(ignoreErrList, igErr)
	}
	task.SaveIgnoreErrs(ignoreErrList)

	return importTasks, nil
}

// PreClear 清理以往task生成的垃圾数据(tredis-binlog-0-output* list-output-0 tendis-binlog-expires*)
func (task *CmdsImporterTask) PreClear(delOutputFile, delOutputExpire, delImportLog bool) {
	// 删除output 文件
	if len(task.OutputFiles) > 0 && delOutputFile == true {
		// 文件存在,则清理
		// rmCmd := fmt.Sprintf("rm -rf %s/%s > /dev/null 2>&1", task.RowData.SqlfileDir, constvar.TredisdumpOutputGlobMatch)
		rmCmd := fmt.Sprintf("cd %s && find . -maxdepth 1 -name '%s' -print|xargs rm > /dev/null 2>&1",
			task.RowData.SqlfileDir, constvar.TredisdumpOutputGlobMatch)
		task.Logger.Info(fmt.Sprintf("CmdsImporterTask PreClear execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 1*time.Hour, task.Logger)
	}

	// 删除del 文件
	if len(task.DelFiles) > 0 && delOutputFile == true {
		// 文件存在,则清理
		// rmCmd := fmt.Sprintf("rm -rf %s/%s > /dev/null 2>&1", task.RowData.SqlfileDir, constvar.TredisdumpDelGlobMatch)
		rmCmd := fmt.Sprintf("cd %s && find . -maxdepth 1 -name '%s' -print|xargs rm > /dev/null 2>&1",
			task.RowData.SqlfileDir, constvar.TredisdumpDelGlobMatch)
		task.Logger.Info(fmt.Sprintf("CmdsImporterTask PreClear execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 1*time.Hour, task.Logger)
	}

	// 删除list 文件
	if len(task.ListFiles) > 0 && delOutputFile == true {
		// 文件存在,则清理
		// rmCmd := fmt.Sprintf("rm -rf %s/%s > /dev/null 2>&1", task.RowData.SqlfileDir, constvar.TredisdumpListGlobMatch)
		rmCmd := fmt.Sprintf("cd %s && find . -maxdepth 1 -name '%s' -print|xargs rm > /dev/null 2>&1",
			task.RowData.SqlfileDir, constvar.TredisdumpListGlobMatch)
		task.Logger.Info(fmt.Sprintf("CmdsImporterTask PreClear execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 1*time.Hour, task.Logger)
	}

	// 找到expire文件
	if len(task.ExpireFiles) > 0 && delOutputExpire == true {
		// 文件存在,则清理
		// rmCmd := fmt.Sprintf("rm -rf %s/%s > /dev/null 2>&1", task.RowData.SqlfileDir, constvar.TredisdumpExpireGlobMatch)
		rmCmd := fmt.Sprintf("cd %s && find . -maxdepth 1 -name '%s' -print|xargs rm > /dev/null 2>&1",
			task.RowData.SqlfileDir, constvar.TredisdumpExpireGlobMatch)
		task.Logger.Info(fmt.Sprintf("CmdsImporterTask PreClear execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 1*time.Hour, task.Logger)
	}
	importLogDir := filepath.Join(task.RowData.SqlfileDir, "importlogs")
	_, err := os.Stat(importLogDir)
	if err == nil && delImportLog == true {
		// 文件存在,则清理
		rmCmd := fmt.Sprintf("rm -rf %s > /dev/null 2>&1", importLogDir)
		task.Logger.Info(fmt.Sprintf("CmdsImporterTask PreClear execute localCmd:%s", rmCmd))
		util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 1*time.Hour, task.Logger)
	}
}

// GetOutputFiles 获取output文件列表
func (task *CmdsImporterTask) GetOutputFiles() {
	outputFiles, err := filepath.Glob(task.RowData.SqlfileDir + "/" + constvar.TredisdumpOutputGlobMatch)
	if err != nil {
		task.Err = fmt.Errorf("GetOutputFiles match %s/%s fail,err:%v",
			task.RowData.SqlfileDir, constvar.TredisdumpOutputGlobMatch, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.OutputFiles = outputFiles
	return
}

// GetListFiles 获取list文件列表
func (task *CmdsImporterTask) GetListFiles() {
	listFiles, err := filepath.Glob(task.RowData.SqlfileDir + "/" + constvar.TredisdumpListGlobMatch)
	if err != nil {
		task.Err = fmt.Errorf("GetListFiles match %s/%s fail,err:%v",
			task.RowData.SqlfileDir, constvar.TredisdumpListGlobMatch, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	twoNumReg := regexp.MustCompile(`^(\d+)_list_(\d+)$`)
	sort.Slice(listFiles, func(i, j int) bool {
		f01 := filepath.Base(listFiles[i])
		f02 := filepath.Base(listFiles[j])

		list01 := twoNumReg.FindStringSubmatch(f01)
		list02 := twoNumReg.FindStringSubmatch(f02)
		if len(list01) != 3 || len(list02) != 3 {
			return false
		}

		f01ThreadID, _ := strconv.ParseUint(list01[1], 10, 64)
		f01Idx, _ := strconv.ParseUint(list01[2], 10, 64)

		f02ThreadID, _ := strconv.ParseUint(list02[1], 10, 64)
		f02Idx, _ := strconv.ParseUint(list02[2], 10, 64)

		// 按照线程id、文件编号 正序
		if f01ThreadID < f02ThreadID {
			return true
		} else if f01ThreadID == f02ThreadID {
			if f01Idx < f02Idx {
				return true
			}
		}
		return false
	})

	task.ListFiles = listFiles
	return
}

// GetExpireFiles 获取expire文件列表
func (task *CmdsImporterTask) GetExpireFiles() {
	expireFiles, err := filepath.Glob(task.RowData.SqlfileDir + "/" + constvar.TredisdumpExpireGlobMatch)
	if err != nil {
		task.Err = fmt.Errorf("GetExpireFiles match %s/%s fail,err:%v",
			task.RowData.SqlfileDir, constvar.TredisdumpExpireGlobMatch, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.ExpireFiles = expireFiles
	return
}

// GetDelFiles 获取del文件列表(包含符合类型key del命令)
func (task *CmdsImporterTask) GetDelFiles() {
	delFiles, err := filepath.Glob(task.RowData.SqlfileDir + "/" + constvar.TredisdumpDelGlobMatch)
	if err != nil {
		task.Err = fmt.Errorf("GetDelFiles match %s/%s fail,err:%v",
			task.RowData.SqlfileDir, constvar.TredisdumpDelGlobMatch, err)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.DelFiles = delFiles
	return
}

// createImportLogDirNotExists create importLogDir if not exists
func (task *CmdsImporterTask) createImportLogDirNotExists() {
	_, err := os.Stat(task.RowData.SqlfileDir)
	if err != nil && os.IsNotExist(err) == true {
		task.Err = fmt.Errorf("sql文件夹:%s not exists", task.RowData.SqlfileDir)
		task.Logger.Error(task.Err.Error())
		return
	}
	task.Logger.Info("SqlfileDir is ok", zap.String("SqlfileDir", task.RowData.SqlfileDir))

	// 创建日志目录
	task.ImportLogDir = filepath.Join(task.RowData.SqlfileDir, "importlogs")
	task.Err = util.MkDirIfNotExists(task.ImportLogDir)
	if task.Err != nil {
		return
	}
}

// getimportLogDir ..
func (task *CmdsImporterTask) getimportLogDir() string {
	return task.ImportLogDir
}

func (task *CmdsImporterTask) confirmHaveListKeys() {
	if len(task.ListFiles) == 0 {
		return
	}
	for _, listFile := range task.ListFiles {
		file01, err := os.Stat(listFile)
		if err != nil {
			task.Err = fmt.Errorf("os.stat fail,err:%v,file:%s", err, listFile)
			task.Logger.Error(task.Err.Error())
			return
		}
		if file01.Size() > 0 {
			task.SetSrcHaveListKeys(1)
			task.UpdateRow()
			task.Logger.Info(fmt.Sprintf("srcRedis:%s#%d have list keys", task.RowData.SrcIP, task.RowData.SrcPort))
			return
		}
	}
	task.Logger.Info(fmt.Sprintf("srcRedis:%s#%d no list keys", task.RowData.SrcIP, task.RowData.SrcPort))
}

// Execute 执行命令导入
func (task *CmdsImporterTask) Execute() {
	if task.Err != nil {
		return
	}
	defer func() {
		if task.Err != nil {
			task.SetStatus(-1)
			task.SetMessage(task.Err.Error())
			task.UpdateRow()
		}
	}()

	task.SetStatus(1)
	task.UpdateDbAndLogLocal("开始对执行cmdsImporter")

	redisClient, err := util.IsToolExecutableInCurrDir("redis-cli")
	if err != nil {
		task.Err = err
		return
	}
	task.createImportLogDirNotExists()
	if task.Err != nil {
		return
	}
	parallelLimit := task.ImportParallelLimit()
	dstPasswd, _ := base64.StdEncoding.DecodeString(task.RowData.DstPassword)

	// 找到 del 文件
	task.GetDelFiles()
	if task.Err != nil {
		return
	}
	// 找到所有 output 文件
	task.GetOutputFiles()
	if task.Err != nil {
		return
	}
	// 找到所有 list 文件
	task.GetListFiles()
	if task.Err != nil {
		return
	}
	// 找到 expire 文件
	task.GetExpireFiles()
	if task.Err != nil {
		return
	}
	// 确定是否有list文件
	task.confirmHaveListKeys()
	if task.Err != nil {
		return
	}

	task.LookupDstRedisProxyAddrs()
	if task.Err != nil {
		return
	}
	// 导入数据时关闭目的集群慢查询
	task.DisableDstClusterSlowlog()

	task.UpdateDbAndLogLocal("found %d del files", len(task.DelFiles))

	if task.IsToDelFirst() {
		// 如果是重试迁移,则优先导入 del 命令
		task.UpdateDbAndLogLocal("found %d del files", len(task.DelFiles))

		delsTasks := []*ImporterItem{}
		for _, del1 := range task.DelFiles {
			taskItem, err := task.NewImporterItem(redisClient, del1, string(dstPasswd))
			if err != nil {
				task.Err = err
				return
			}
			delsTasks = append(delsTasks, &taskItem)
		}
		task.UpdateDbAndLogLocal("开始执行dels文件导入...")

		_, err = task.parallelImportV2(delsTasks, parallelLimit)
		if task.RowData.SyncOperate == constvar.RedisForceKillTaskSuccess {
			// task had been terminated
			// restore src redis 'slave-log-keep-count'
			task.RestoreSrcSSDKeepCount()
			// clear output、expires,keep importlogs
			task.PreClear(true, true, false)
			return
		}
		if err != nil {
			task.Err = err
			return
		}
	} else {
		task.Logger.Info(fmt.Sprintf("found %d del files,task %d retry times,no need import del",
			len(task.DelFiles), task.RowData.RetryTimes))
	}

	task.UpdateDbAndLogLocal("found %d output files", len(task.OutputFiles))

	outputFileTasks := []*ImporterItem{}
	for _, output01 := range task.OutputFiles {
		taskItem, err := task.NewImporterItem(redisClient, output01, string(dstPasswd))
		if err != nil {
			task.Err = err
			return
		}
		outputFileTasks = append(outputFileTasks, &taskItem)
	}
	if len(outputFileTasks) > 0 {
		task.UpdateDbAndLogLocal("共有%d个output文件需导入,开始执行output文件导入...", len(outputFileTasks))

		_, err = task.parallelImportV2(outputFileTasks, parallelLimit)
		if task.RowData.SyncOperate == constvar.RedisForceKillTaskSuccess {
			// task had been terminated
			// restore src redis 'slave-log-keep-count'
			task.RestoreSrcSSDKeepCount()
			// clear output、expires,keep importlogs
			task.PreClear(true, true, false)
			return
		}
		if err != nil {
			task.Err = err
			return
		}
	} else {
		task.UpdateDbAndLogLocal("该实例无任何hash/string/set/zset需导入...")
	}

	listFileTasks := []*ImporterItem{}
	task.UpdateDbAndLogLocal("found %d list files", len(task.ListFiles))

	for _, list01 := range task.ListFiles {
		taskItem, err := task.NewImporterItem(redisClient, list01, string(dstPasswd))
		if err != nil {
			task.Err = err
			return
		}
		listFileTasks = append(listFileTasks, &taskItem)
	}

	if len(listFileTasks) > 0 {
		task.UpdateDbAndLogLocal("共有%d个list文件需导入,开始执行list文件导入...", len(listFileTasks))

		_, err = task.SyncImport(listFileTasks)
		if task.RowData.SyncOperate == constvar.RedisForceKillTaskSuccess {
			// task had been terminated
			// restore src redis 'slave-log-keep-count'
			task.RestoreSrcSSDKeepCount()
			// clear output、expires,keep importlogs
			task.PreClear(true, true, false)
			return
		}
		if err != nil {
			task.Err = err
			return
		}
	} else {
		task.UpdateDbAndLogLocal("该实例无任何list key需导入....")
	}

	if len(task.ExpireFiles) > 0 {
		task.UpdateDbAndLogLocal("found %d expire files", len(task.ExpireFiles))

		expiresTasks := []*ImporterItem{}
		for _, expires1 := range task.ExpireFiles {
			taskItem, err := task.NewImporterItem(redisClient, expires1, string(dstPasswd))
			if err != nil {
				task.Err = err
				return
			}
			expiresTasks = append(expiresTasks, &taskItem)
		}
		task.UpdateDbAndLogLocal("开始执行expires文件导入...")

		_, err = task.parallelImportV2(expiresTasks, parallelLimit)
		if task.RowData.SyncOperate == constvar.RedisForceKillTaskSuccess {
			// task had been terminated
			// restore src redis 'slave-log-keep-count'
			task.RestoreSrcSSDKeepCount()
			// clear output、expires,keep importlogs
			task.PreClear(true, true, false)
			return
		}
		if err != nil {
			task.Err = err
			return
		}
	} else {
		task.Logger.Info("没有找到expire文件,无需import")
	}

	task.EndClear()
	if task.Err != nil {
		return
	}

	task.SetTaskType(task.NextTask())
	task.SetStatus(0)
	task.UpdateDbAndLogLocal("等待启动redis_sync")
	return
}

// IsToDelFirst 是否先执行del命令
func (task *CmdsImporterTask) IsToDelFirst() bool {
	if len(task.DelFiles) == 0 {
		return false
	}
	if task.RowData.WriteMode == constvar.WriteModeDeleteAndWriteToRedis {
		// 用户选择的就是 del + hset
		return true
	}
	if task.RowData.WriteMode == constvar.WriteModeFlushallAndWriteToRedis &&
		task.RowData.RetryTimes > 0 {
		// 用户选择 flushall + hset,第一次无需执行del,重试迁移时,先执行del
		return true
	}
	// 如果是 keep_and_append_to_redis模式,则不执行del
	return false
}

// EndClear 命令导入完成后清理output、expires文件
func (task *CmdsImporterTask) EndClear() {
	debug := viper.GetBool("TENDIS_DEBUG")
	if debug == true {
		return
	}
	task.PreClear(true, true, false) // output、expires文件,importlogs保留
}
