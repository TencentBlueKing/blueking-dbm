package restore

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"
	"text/template"
	"time"

	"golang.org/x/sync/errgroup"

	"dbm-services/common/go-pubpkg/filecontext"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/reportlog"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	binlogParser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"

	"github.com/pkg/errors"
)

// GoApplyBinlogComp 有 resp 返回
type GoApplyBinlogComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       GoApplyBinlog            `json:"extend"`
}

// Example TODO
func (c *GoApplyBinlogComp) Example() interface{} {
	return GoApplyBinlogComp{
		Params: GoApplyBinlog{
			TgtInstance: common.InstanceObjExample,
			BinlogOpt: &GoMySQLBinlogUtil{
				StartTime:     "2022-11-05 00:00:01",
				StopTime:      "2022-11-05 22:00:01",
				Idempotent:    true,
				DisableLogBin: true,
				Databases:     []string{"db1", "db2"},
				Tables:        []string{"tb1", "tb2"},
			},
			MySQLClientOpt: &MySQLClientOpt{
				MaxAllowedPacket: 1073741824,
				BinaryMode:       true,
			},
			QuickMode:       true,
			BinlogDir:       "/data/dbbak/20000/binlog",
			BinlogFiles:     []string{"binlog20000.00001", "binlog20000.00002", "binlog20000.00003"},
			BinlogStartFile: "binlog20000.00001",
			WorkDir:         "/data/dbbak/",
			ParseOnly:       false,
			ToolSet:         *tools.NewToolSetWithPickNoValidate(tools.ToolGoMysqlbinlog),
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
}

// GoApplyBinlog TODO
type GoApplyBinlog struct {
	TgtInstance native.InsObject   `json:"tgt_instance" validate:"required"`
	BinlogOpt   *GoMySQLBinlogUtil `json:"binlog_opt" validate:"required"`
	// 恢复时 binlog 存放目录，一般是下载目录
	BinlogDir string `json:"binlog_dir" validate:"required" example:"/data/dbbak/123456/binlog"`
	// binlog列表
	BinlogFiles []string `json:"binlog_files" validate:"required"`
	// 指定要开始应用的第 1 个 binlog。如果指定，一般要设置 start_pos，如果不指定则使用 start_time
	// BinlogStartFile 只能由外部传入，不要内部修改
	BinlogStartPos  uint   `json:"binlog_start_pos"`
	BinlogStartFile string `json:"binlog_start_file"`
	// 格式 "2006-01-02 15:04:05" 原样传递给 mysqlbinlog
	// 格式"2006-01-02T15:04:05Z07:00"(示例"2023-12-11T05:03:05+08:00")按照机器本地时间，解析成 "2006-01-02 15:04:05" 再传递给 mysqlbinlog
	// 在 Init 时会统一把时间字符串转换成 time.RFC3399
	StartTime string `json:"start_time"`
	// --stop-datetime   时间格式同 StartTime，可带时区，会转换成机器本地时间
	StopTime string `json:"stop_time"`
	// binlog 解析所在目录，存放运行日志
	WorkDir string `json:"work_dir" validate:"required" example:"/data/dbbak/"`
	WorkID  string `json:"work_id" example:"123456"`
	// 仅解析 binlog，不做导入
	ParseOnly bool `json:"parse_only"`
	// 解析的并发度，默认 1
	ParseConcurrency int `json:"parse_concurrency"`

	// 如果启用 quick_mode，解析 binlog 时根据 filter databases 等选项过滤 row event，对 query event 会全部保留 。
	// 需要 mysqlbinlog 工具支持 --tables 选项，可以指定参数的 tools
	// 当 quick_mode=false 时，recover_opt 里的 databases 等选项无效，会应用全部 binlog
	QuickMode          bool   `json:"quick_mode"`
	SourceBinlogFormat string `json:"source_binlog_format" enums:",ROW,STATEMENT,MIXED"`

	MySQLClientOpt *MySQLClientOpt `json:"mysql_client_opt"`

	// 恢复用到的客户端工具，不提供时会有默认值
	tools.ToolSet

	// /WorkDir/WorkID/
	taskDir         string
	dbWorker        *native.DbWorker // TgtInstance
	mysqlCli        string
	importScript    string
	parseScript     string
	binlogParsedDir string
	logDir          string
}

// ParseBinlogFiles TODO
func (r *GoApplyBinlog) ParseBinlogFiles() error {
	logger.Info("start to parse binlog files with concurrency %d", r.ParseConcurrency)

	errChan := make(chan error)
	//var externalErr error
	//tokenBulkChan := make(chan struct{}, r.ParseConcurrency)
	binlogParseLockFile := "/tmp/mysql_binlog_parse.lock.yaml"
	fileLock, err := filecontext.NewIncrFile(binlogParseLockFile, r.ParseConcurrency, 10*time.Second)
	if err != nil {
		return err
	}
	logger.Info("using lock file %s", fileLock.GetContextFilePath())
	//cancelCtx, cancel := context.WithCancel(context.Background())
	g, _ := errgroup.WithContext(context.Background())
	g.SetLimit(r.ParseConcurrency) // 单个进程也设置一下最大并发

	logger.Info("need parse %d binlog files: %s", len(r.BinlogFiles), r.BinlogFiles)

	for _, f := range r.BinlogFiles {
		//tokenBulkChan <- struct{}{}
		// 如果遇到解析错误，不启动后续解析的 goroutine，所以要在 routine 外层
		select {
		case e := <-errChan:
			if e != nil {
				//不直接 return e，error 信息在 g.Wait() 也能获取到
				close(errChan)
				break
			}
		default:
			// 默认不阻塞
		}
		lockErr := fileLock.Incr(1)

		if lockErr != nil {
			// 这里全局并发控制失效，但不让任务失败
			logger.Error("failed to get file lock:%s. ignore error and concurrency not work", err.Error())
		}
		g.Go(func() error {
			defer func() {
				if lockErr == nil {
					_ = fileLock.Incr(-1)
				}
			}()
			logger.Info("parse %s", f)
			if f == r.BinlogStartFile {
				r.BinlogOpt.StartPos = r.BinlogStartPos
			} else {
				r.BinlogOpt.StartPos = 0
			}
			_, internalErr := r.BinlogOpt.Parse(r.BinlogDir, f, r.QuickMode)
			if internalErr != nil {
				logger.Error("parse %s failed: %s", f, internalErr.Error())
				errChan <- internalErr
			}
			//<-tokenBulkChan
			return internalErr
		})
	}
	if err := g.Wait(); err != nil {
		return err
	} else {
		logger.Info("all binlog finish")
	}
	return nil
}

// buildScript 创建 parse_binlog.sh, import_binlog.sh 脚本，需要调用执行
func (r *GoApplyBinlog) buildScript() error {
	// 创建解析 binlog 的脚本，只是为了查看或者后面手动跑
	// 因为要并行解析，所以真正跑的是 ParseBinlogFiles
	parseCmds := []string{fmt.Sprintf("cd %s", r.taskDir)}
	for _, fileName := range r.BinlogFiles {
		if fileName == "" {
			continue
		} else if fileName == r.BinlogStartFile {
			r.BinlogOpt.StartPos = r.BinlogStartPos
		} else {
			r.BinlogOpt.StartPos = 0
		}
		_, _ = r.BinlogOpt.BuildArgs(r.QuickMode)
		parsedFile := fmt.Sprintf(`%s/%s.sql`, dirBinlogParsed, fileName)
		logFile := fmt.Sprintf("logs/parse_%s.err", fileName)
		binlogFile := filepath.Join(r.BinlogDir, fileName)
		cmd := fmt.Sprintf("%s %s --file %s  -r %s 2>%s",
			r.BinlogOpt.cmdPath, strings.Join(r.BinlogOpt.cmdArgs, " "), binlogFile, parsedFile, logFile)
		parseCmds = append(parseCmds, cmd)
	}
	r.parseScript = fmt.Sprintf(filepath.Join(r.taskDir, parseScript))
	fh, err := os.OpenFile(r.parseScript, os.O_CREATE|os.O_WRONLY, 0755)
	if err != nil {
		return err
	}
	defer fh.Close()
	_, err = io.WriteString(fh, strings.Join(parseCmds, "\n"))
	if err != nil {
		return errors.Wrap(err, "write parse script")
	}

	// 创建导入 binlog 的脚本
	importBinlogTmpl := `
#!/bin/bash
dbhost={{.dbHost}}
dbport={{.dbPort}}
dbuser={{.dbUser}}
dbpass={{.dbPass}}
mysql_cmd={{.mysqlCmd}}
retcode=0

if [ "$dbpass" = "" ];then 
	echo 'please set password'
	exit 1
fi
cd {{.taskDir}}

mysql_opt="-u$dbuser -p$dbpass -h$dbhost -P$dbport {{.mysqlOpt}} -A "
sqlFiles="{{.sqlFiles}}"
for f in $sqlFiles
do
	filename={{.dirBinlogParsed}}/${f}.sql
	echo "importing $filename"
	$mysql_cmd $mysql_opt < $filename >>logs/import_binlog.log 2>>logs/import_binlog.err
	if [ $? -gt 0 ];then
		retcode=1
		break
	fi
done
cd -
exit $retcode
`
	r.importScript = fmt.Sprintf(filepath.Join(r.taskDir, importScript))
	fi, err := os.OpenFile(r.importScript, os.O_CREATE|os.O_WRONLY, 0755)
	if err != nil {
		return err
	}
	defer fi.Close()
	if r.BinlogOpt.Flashback {
		sort.Sort(sort.Reverse(sort.StringSlice(r.BinlogFiles))) // 降序
		// sort.Slice(sqlFiles, func(i, j int) bool { return sqlFiles[i] > sqlFiles[j] }) // 降序
	}
	if tpl, err := template.New("").Parse(importBinlogTmpl); err != nil {
		return errors.Wrap(err, "write import script")
	} else {
		Vars := map[string]interface{}{
			"dbHost":          r.TgtInstance.Host,
			"dbPort":          r.TgtInstance.Port,
			"dbUser":          r.TgtInstance.User,
			"dbPass":          r.TgtInstance.Pwd,
			"mysqlOpt":        "--max-allowed-packet=1073741824 --binary-mode",
			"mysqlCmd":        r.ToolSet.MustGet(tools.ToolMysqlclient),
			"dirBinlogParsed": dirBinlogParsed,
			"sqlFiles":        strings.Join(r.BinlogFiles, " "),
			"taskDir":         r.taskDir,
		}
		if err := tpl.Execute(fi, Vars); err != nil {
			return err
		}
	}
	return nil
}

// Init TODO
func (r *GoApplyBinlog) Init() error {
	var err error
	// 工具路径初始化，检查工具路径, 工具可执行权限
	toolset, err := tools.NewToolSetWithPick(tools.ToolGoMysqlbinlog, tools.ToolMysqlclient)
	if err != nil {
		return err
	}
	if err = r.ToolSet.Merge(toolset); err != nil {
		return err
	}

	// quick_mode is only allowed when binlog_format=row
	if r.SourceBinlogFormat != "ROW" && r.QuickMode && !r.BinlogOpt.Flashback {
		r.QuickMode = false
		logger.Warn("quick_mode set to false because source_binlog_format != ROW")
	}
	//if r.QuickMode && r.SourceBinlogFormat != "ROW" {
	//	return errors.New("source_binlog_format=ROW is needed because quick_mode will filter tables from binlog")
	//}
	if r.BinlogOpt.Flashback {
		if r.SourceBinlogFormat != "ROW" {
			return errors.New("flashback=true need source_binlog_format=ROW")
		}
		if !r.QuickMode {
			return errors.New("flashback=true need quick_mode=true")
		}
		if !r.ParseOnly {
			return errors.New("flashback=true must have parse_only=true")
		}
	}

	if r.BinlogStartPos > 0 && r.BinlogStartFile == "" {
		return errors.Errorf("binlog_start_pos must has binlog_start_file")
	}
	if r.BinlogStartPos == 0 && r.StartTime == "" {
		return errors.Errorf("start_time and start_pos cannot be empty both")
	}
	// r.StartTime, r.StopTime 统一成 RFC3339 格式，便于后面做比较
	// r.BinlogOpt.StartTime r.BinlogOpt.StopTime 是 DateTime 格式，传给 gomysqlbinlog
	if r.StartTime != "" {
		if t, err := time.ParseInLocation(time.DateTime, r.StartTime, time.Local); err == nil {
			r.BinlogOpt.StartTime = r.StartTime
			r.StartTime = t.Format(time.RFC3339)
		} else if t, err := time.ParseInLocation(time.RFC3339, r.StartTime, time.Local); err == nil {
			r.BinlogOpt.StartTime = t.Format(time.DateTime)
		} else {
			return errors.Errorf("unknown time format for start_time: %s", r.StartTime)
		}
	}
	if r.StopTime != "" {
		var stopTime time.Time
		if t, err := time.ParseInLocation(time.DateTime, r.StopTime, time.Local); err == nil {
			r.BinlogOpt.StopTime = r.StopTime
			r.StopTime = t.Format(time.RFC3339)
		} else if t, err := time.ParseInLocation(time.RFC3339, r.StopTime, time.Local); err == nil {
			r.BinlogOpt.StopTime = t.Format(time.DateTime)
		} else {
			return errors.Errorf("unknown time format for stop_time: %s", r.StopTime)
		}
		stopTime, _ = time.ParseInLocation(time.DateTime, r.BinlogOpt.StopTime, time.Local)
		if nowTime := time.Now(); nowTime.Compare(stopTime) < 0 {
			return errors.Errorf("StopTime [%s] cannot be greater than db current time [%s]",
				r.BinlogOpt.StopTime, nowTime)
		}
	}

	if r.ParseConcurrency == 0 {
		r.ParseConcurrency = 1
	}
	// 检查目标实例连接性
	if r.BinlogOpt.Flashback || !r.ParseOnly {
		// logger.Info("tgtInstance: %+v", r.TgtInstance)
		r.dbWorker, err = r.TgtInstance.Conn()
		if err != nil {
			return errors.Wrap(err, "目标实例连接失败")
		}
		if ret, err := r.TgtInstance.MySQLClientExec(r.ToolSet.MustGet(tools.ToolMysqlclient), "select 1"); err != nil {
			return err
		} else if strings.Contains(ret, "ERROR ") {
			logger.Error("MySQLClientExec failed: %w %s", ret, err)
		}
	}
	if err = r.initDirs(); err != nil {
		return err
	}
	return nil
}

func (r *GoApplyBinlog) buildMysqlCliOptions() error {
	b := r.BinlogOpt
	mysqlOpt := r.MySQLClientOpt

	// init mysql client options
	var initCommands []string
	if b.DisableLogBin {
		initCommands = append(initCommands, "set session sql_log_bin=0")
	}
	if len(initCommands) > 0 {
		r.TgtInstance.Options += fmt.Sprintf(" --init-command='%s'", strings.Join(initCommands, ";"))
	}
	if mysqlOpt.BinaryMode {
		r.TgtInstance.Options += " --binary-mode"
	}
	if mysqlOpt.MaxAllowedPacket > 0 {
		r.TgtInstance.Options += fmt.Sprintf(" --max-allowed-packet=%d", mysqlOpt.MaxAllowedPacket)
	}
	r.mysqlCli = r.TgtInstance.MySQLClientCmd(r.ToolSet.MustGet(tools.ToolMysqlclient))
	return nil
}

func (r *GoApplyBinlog) buildBinlogOptions() error {

	binlogTool := r.ToolSet.MustGet(tools.ToolGoMysqlbinlog)
	r.BinlogOpt.SetCmdPath(binlogTool)
	r.BinlogOpt.SetWorkDir(r.taskDir)
	return nil
}

func (r *GoApplyBinlog) initDirs() error {
	if r.WorkID == "" {
		r.WorkID = newTimestampString()
	}
	r.taskDir = fmt.Sprintf("%s/apply_binlog_%s/%d", r.WorkDir, r.WorkID, r.TgtInstance.Port)
	if err := osutil.CheckAndMkdir("", r.taskDir); err != nil {
		return err
	}
	r.binlogParsedDir = fmt.Sprintf("%s/%s", r.taskDir, dirBinlogParsed)
	if err := osutil.CheckAndMkdir("", r.binlogParsedDir); err != nil {
		return err
	}
	r.logDir = fmt.Sprintf("%s/%s", r.taskDir, "logs")
	if err := osutil.CheckAndMkdir("", r.logDir); err != nil {
		return err
	}
	return nil
}

func (r *GoApplyBinlog) checkBinlogFiles() error {
	// 检查 binlog 是否存在
	var binlogFilesErrs []error
	for _, f := range r.BinlogFiles {
		filename := filepath.Join(r.BinlogDir, f)
		if err := cmutil.FileExistsErr(filename); err != nil {
			binlogFilesErrs = append(binlogFilesErrs, err)
		}
	}
	if len(r.BinlogFiles) == 0 {
		return errors.New("no binlog files given")
	} else if len(binlogFilesErrs) > 0 {
		return util.SliceErrorsToError(binlogFilesErrs)
	}

	// 检查 binlog 文件连续性
	sort.Strings(r.BinlogFiles)
	fileSeqList := util.GetSuffixWithLenAndSep(r.BinlogFiles, ".", 0)
	if leakInts, err := util.IsConsecutiveStrings(fileSeqList, true); err != nil {
		logger.Warn("binlog leak number: %v", leakInts)
		// 如果文件不连续，会尝试从本机器恢复目录下查找。用于手动补全了 binlog 的情况
		var leakFiles []string
		for _, intVal := range leakInts {
			binlogFileName := constructBinlogFilename(r.BinlogFiles[0], intVal)
			leakFiles = append(leakFiles, binlogFileName)
			logger.Warn("check leak binlog file exists: %s", filepath.Join(r.BinlogDir, binlogFileName))
			if err := cmutil.FileExistsErr(filepath.Join(r.BinlogDir, binlogFileName)); err != nil {
				binlogFilesErrs = append(binlogFilesErrs, err)
			}
		}
		if len(binlogFilesErrs) > 0 {
			return errors.WithMessage(err, util.SliceErrorsToError(binlogFilesErrs).Error())
		} else {
			r.BinlogFiles = append(r.BinlogFiles, leakFiles...)
			slices.Sort(r.BinlogFiles)
		}
		//return err
	}

	// 指定了开始 binlog file 时，忽略 start_time
	// 检查第一个 binlog 是否存在
	if r.BinlogStartFile != "" {
		if !util.StringsHas(r.BinlogFiles, r.BinlogStartFile) {
			return errors.WithMessagef(ErrorBinlogMissing, "binlog_start_file %s not found", r.BinlogStartFile)
		}
		// 如果 start_datetime 为空，依赖 start_file, start_pos 选择起始 binlog pos
		for i, f := range r.BinlogFiles {
			if f != r.BinlogStartFile {
				logger.Info("remove binlog file %s from list", f)
				r.BinlogFiles[i] = "" // 移除第一个 binlog 之前的 file
			} else {
				break
			}
		}
		r.BinlogFiles = cmutil.StringsRemoveEmpty(r.BinlogFiles)
	}

	if err := r.checkTimeRange(); err != nil {
		return err
	}
	return nil
}

// GetBinlogFilesFromDir 获取指定目录下的 binlog 文件列表
// 合法的 binlog 格式 binlog\d*\.\d+$
func (r *GoApplyBinlog) GetBinlogFilesFromDir(binlogDir, namePrefix string) ([]string, error) {
	// 临时关闭 binlog 删除
	files, err := os.ReadDir(binlogDir) // 已经按文件名排序
	if err != nil {
		return nil, errors.Wrap(err, "read binlog dir")
	}

	var binlogFiles []string
	reFilename := regexp.MustCompile(cst.ReBinlogFilename)
	for _, fi := range files {
		if reFilename.MatchString(fi.Name()) {
			if namePrefix == "" {
				binlogFiles = append(binlogFiles, fi.Name())
			} else if strings.HasPrefix(fi.Name(), namePrefix) {
				binlogFiles = append(binlogFiles, fi.Name())
			}
		}
	}
	return binlogFiles, nil
}

// PreCheck TODO
// r.BinlogFiles 是已经过滤后的 binlog 文件列表
func (r *GoApplyBinlog) PreCheck() error {
	var err error
	if err = r.buildMysqlCliOptions(); err != nil {
		return err
	}
	// init mysqlbinlog options
	if err = r.buildBinlogOptions(); err != nil {
		return err
	}
	if err = r.checkBinlogFiles(); err != nil {
		logger.Warn("check binlog files error: %s. try to get binlog file from recover dir", err.Error())
	}
	if errors.Is(err, ErrorBinlogMissing) {
		nameParts := strings.Split(r.BinlogFiles[0], ".")
		if binlogFiles, err := r.GetBinlogFilesFromDir(r.BinlogDir, nameParts[0]+"."); err != nil {
			return errors.WithMessagef(err, "get binlog files from %s", r.BinlogDir)
		} else {
			r.BinlogFiles = binlogFiles
		}
		return r.checkBinlogFiles()
	}
	return err
}

// FilterBinlogFiles 对 binlog 列表根据时间，掐头去尾，并返回文件总大小
// binlog开始点：如果 start_file 不为空，以 start_file 为优先
// binlog结束点：最后一个binlog end_time > 过滤条件 stop_time
func (r *GoApplyBinlog) FilterBinlogFiles() (totalSize int64, err error) {
	logger.Info("BinlogFiles before filter: %v", r.BinlogFiles)
	sort.Strings(r.BinlogFiles)

	// 如果传入了 start_file，第一个binlog很好找
	if r.BinlogStartFile != "" {
		if !util.StringsHas(r.BinlogFiles, r.BinlogStartFile) {
			return 0, errors.WithMessagef(ErrorBinlogMissing, "first binlog %s not found", r.BinlogStartFile)
		}
		// 如果 start_datetime 为空，依赖 start_file, start_pos 选择起始 binlog pos
		for i, f := range r.BinlogFiles {
			if f != r.BinlogStartFile {
				logger.Info("remove binlog file %s from list", f)
				r.BinlogFiles[i] = "" // 移除第一个 binlog 之前的 file
			} else {
				break
			}
		}
		r.BinlogFiles = cmutil.StringsRemoveEmpty(r.BinlogFiles)
	}

	// 如果传入的是 start_time，需要根据时间过滤。但如果也传入了 start_file，以 start_file 优先
	bp, _ := binlogParser.NewBinlogParse("", 0, time.RFC3339) // 接收的时间过滤参数也需要用 RFC3339
	var binlogFiles = []string{}                              // 第一个元素预留
	var firstBinlogFound bool
	var lastBinlogFile string
	var lastBinlogSize int64
	var firstBinlogFile string
	var firstBinlogSize int64 = 0
	// 过滤 binlog time < stop_time
	// 如果有需要 也会过滤 binlog time > start_time
	var startTimeFilter, stopTimeFilter time.Time // 前后时间偏移 20分钟
	if r.BinlogOpt.StartTime != "" {
		if startTimeFilter, err = cmutil.ParseLocalTimeString(r.BinlogOpt.StartTime); err != nil {
			return 0, errors.WithMessage(err, "start_time parse failed")
		}
		// binlog时间 start_time 比 预期start_time 提早 20 分钟
		startTimeFilter = startTimeFilter.Add(-20 * time.Minute)
	}
	if stopTimeFilter, err = cmutil.ParseLocalTimeString(r.BinlogOpt.StopTime); err != nil {
		return 0, errors.WithMessage(err, "stop_time parse failed")
	} else {
		// binlog时间 stop_time 比 预期stop_time 延后 20 分钟
		stopTimeFilter = stopTimeFilter.Add(20 * time.Minute)
	}

	for _, f := range r.BinlogFiles {
		fileName := filepath.Join(r.BinlogDir, f)
		// **** get binlog time
		// todo 如果是闪回模式，只从本地binlog获取，也可以读取 file mtime，确保不会出错
		events, err := bp.GetTimeIgnoreStopErr(fileName, true, true)
		if err != nil {
			return 0, err
		}
		startTime, _ := time.ParseInLocation(time.RFC3339, events[0].EventTime, time.Local)
		stopTime, _ := time.ParseInLocation(time.RFC3339, events[1].EventTime, time.Local)
		fileSize := cmutil.GetFileSize(fileName)
		// **** get binlog time

		if r.BinlogOpt.StopTime != "" && stopTime.Compare(stopTimeFilter) > 0 {
			break
		}
		if r.BinlogStartFile != "" {
			binlogFiles = append(binlogFiles, f)
			totalSize += fileSize
		} else if r.BinlogOpt.StartTime != "" {
			if startTime.Compare(startTimeFilter) > 0 { // time.RFC3339
				if !firstBinlogFound { // 拿到binlog时间符合条件的 前一个binlog
					firstBinlogFound = true
					firstBinlogFile = lastBinlogFile
					firstBinlogSize = lastBinlogSize
				}
				binlogFiles = append(binlogFiles, f)
				totalSize += fileSize
			}
		}
		lastBinlogFile = f // 记录上一个binlog的信息
		lastBinlogSize = fileSize
	}
	if r.BinlogStartFile == "" {
		if firstBinlogFile != "" {
			binlogFiles = cmutil.StringsInsertIndex(binlogFiles, 0, firstBinlogFile)
			totalSize += firstBinlogSize
		} else {
			logger.Warn("first binlog expect earlier than %s not found", startTimeFilter)
		}
	}
	r.BinlogFiles = binlogFiles
	logger.Info("BinlogFiles after filter: %v", r.BinlogFiles)
	return totalSize, nil
}

// checkTimeRange 再次检查 binlog 时间
func (r *GoApplyBinlog) checkTimeRange() error {
	startTime := r.StartTime
	stopTime := r.StopTime
	if startTime != "" && stopTime != "" && startTime >= stopTime {
		return errors.Errorf("binlog start_time [%s] should be little then stop_time [%s]", startTime, stopTime)
	}
	bp, _ := binlogParser.NewBinlogParse("", 0, reportlog.ReportTimeLayout1) // 用默认值
	if r.BinlogStartFile == "" && startTime != "" {
		events, err := bp.GetTime(filepath.Join(r.BinlogDir, r.BinlogFiles[0]), true, false)
		if err != nil {
			return err
		}
		evStartTime := events[0].EventTime
		if evStartTime > startTime {
			return errors.WithMessagef(ErrorBinlogMissing,
				"the first binlog %s start-datetime [%s] is greater then start_time [%s]",
				r.BinlogFiles[0], evStartTime, startTime,
			)
		} else {
			logger.Info(
				"the first binlog %s start-datetime [%s] is lte start time[%s]. ok",
				r.BinlogFiles[0], evStartTime, startTime,
			)
		}
	}

	// 检查最后一个 binlog 时间，需要在目标时间之后
	if stopTime != "" {
		lastBinlog := util.LastElement(r.BinlogFiles)
		events, err := bp.GetTimeIgnoreStopErr(filepath.Join(r.BinlogDir, lastBinlog), false, true)
		if err != nil {
			return err
		}
		evStopTime := events[0].EventTime
		if evStopTime < stopTime {
			return errors.WithMessagef(ErrorBinlogMissing,
				"the last binlog %s stop-datetime [%s] is little then target_time [%s]",
				lastBinlog, evStopTime, stopTime,
			)
		} else {
			logger.Info(
				"the last binlog %s stop-datetime [%s] gte target_time [%s]. ok",
				lastBinlog, evStopTime, stopTime,
			)
		}
	}
	return nil
}

// Start godoc
// 一定会解析 binlog
func (r *GoApplyBinlog) Start() error {
	// 本机可能多个实例，会共享解析binlog的并发数
	binlogParseLockFile := "/tmp/mysql_binlog_parse.lock.yaml"
	fileLock, err := filecontext.NewIncrFile(binlogParseLockFile, r.ParseConcurrency, 10*time.Second)
	if err != nil {
		return err
	}
	logger.Info("using lock file %s", fileLock.GetContextFilePath())
	if r.ParseOnly {
		if err = r.buildScript(); err != nil {
			return err
		}
		return r.ParseBinlogFiles()
	} else if !r.BinlogOpt.Flashback {
		if r.BinlogOpt.Idempotent {
			// 这个要在主函数运行，调用 defer 来设置回去
			newValue := "IDEMPOTENT"
			originValue, err := r.dbWorker.SetSingleGlobalVarAndReturnOrigin("slave_exec_mode", newValue)
			if err != nil {
				return err
			}
			if originValue != newValue {
				defer func() {
					if err = r.dbWorker.SetSingleGlobalVar("slave_exec_mode", originValue); err != nil {
						logger.Error("fail to set back slave_exec_mode=%s", originValue)
					}
				}()
			}
		}

		// 这里要考虑命令行的长度
		outFile := filepath.Join(r.taskDir, fmt.Sprintf("import_binlog_%s.log", r.WorkID))
		errFile := filepath.Join(r.taskDir, fmt.Sprintf("import_binlog_%s.err", r.WorkID))
		parseCmd := r.BinlogOpt.ReturnParseCommand(r.BinlogDir, r.BinlogFiles)
		// gomysqlbinlog ... | mysql ...
		cmd := fmt.Sprintf(`%s | %s >>%s 2>%s`, parseCmd, r.mysqlCli, outFile, errFile)
		logger.Info(mysqlcomm.ClearSensitiveInformation(mysqlcomm.RemovePassword(cmd)))

		if err := fileLock.Incr(1); err == nil {
			defer fileLock.Incr(-1)
			// 标准输出，错误输出到打印到 errFile 了
			retContent, err := mysqlutil.ExecCommandMySQLShell(cmd)
			if err != nil {
				//fileLock.FileIncrSafe(-1, 60)
				return errors.WithMessage(err, retContent)
			}
			// 因为错误日志都重定向到文件了，所以真实错误判断要从 errFile 中读取
			errContent, _ := cmutil.NewGrepLines(errFile, true, true).
				MatchWordsExclude([]string{"Using a password"}, 2)
			if errContent != "" || err != nil {
				logger.Error(errContent)
				//fileLock.FileIncrSafe(-1, 60)
				return errors.New(errContent)
			}
		} else {
			return errors.WithMessage(err, "file lock incr failed")
		}
	} else {
		return errors.New("flashback=true must have parse_only=true")
	}
	return nil
}

// Import import_binlog.sh
func (r *GoApplyBinlog) Import() error {

	return BinlogImport(r.taskDir, r.importScript, r.dbWorker)

}

// BinlogImport run import_binlog.sh
func BinlogImport(taskDir, scriptName string, dbWorker *native.DbWorker) error {
	newValue := "IDEMPOTENT"
	originValue, err := dbWorker.SetSingleGlobalVarAndReturnOrigin("slave_exec_mode", newValue)
	if err != nil {
		return err
	}
	if originValue != newValue {
		defer func() {
			if err = dbWorker.SetSingleGlobalVar("slave_exec_mode", originValue); err != nil {
				logger.Error("fail to set back slave_exec_mode=%s", originValue)
			}
		}()
	}
	script := fmt.Sprintf(`cd %s && %s > import.log 2>import.err`, taskDir, scriptName)
	logger.Warn("run script: %s", script)
	_, err = mysqlutil.ExecCommandMySQLShell(script)
	if err != nil {
		return errors.Wrapf(err, "run import_binlog.sh has error")
	}
	return nil
}

// WaitDone TODO
func (r *GoApplyBinlog) WaitDone() error {
	// 通过 lsof 查看 mysqlbinlog 当前打开的是那个 binlog，来判断进度
	return nil
}

// PostCheck TODO
func (r *GoApplyBinlog) PostCheck() error {
	// 检查 infodba_schema.master_slave_heartbeat 里面的时间与 target_time 差异不超过 65s
	return nil
}

// GetDBWorker TODO
func (r *GoApplyBinlog) GetDBWorker() *native.DbWorker {
	return r.dbWorker
}

// GetTaskDir TODO
func (r *GoApplyBinlog) GetTaskDir() string {
	return r.taskDir
}

func (r *GoApplyBinlog) GetScriptName() string {
	return r.importScript
}
