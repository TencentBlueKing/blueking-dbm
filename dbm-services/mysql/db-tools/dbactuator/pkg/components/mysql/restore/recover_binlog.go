package restore

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"
	"sync"
	"text/template"
	"time"

	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"

	"github.com/spf13/cast"

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

// RecoverBinlogComp 有 resp 返回
type RecoverBinlogComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       RecoverBinlog            `json:"extend"`
}

// Example TODO
func (c *RecoverBinlogComp) Example() interface{} {
	return RecoverBinlogComp{
		Params: RecoverBinlog{
			TgtInstance: common.InstanceObjExample,
			RecoverOpt: &MySQLBinlogUtil{
				StartTime:      "2022-11-05 00:00:01",
				StopTime:       "2022-11-05 22:00:01",
				IdempotentMode: true,
				NotWriteBinlog: true,
				Databases:      []string{"db1,db2"},
				Tables:         []string{"tb1,tb2"},
				MySQLClientOpt: &MySQLClientOpt{
					MaxAllowedPacket: 1073741824,
					BinaryMode:       true,
				},
			},
			QuickMode:   true,
			BinlogDir:   "/data/dbbak/20000/binlog",
			BinlogFiles: []string{"binlog20000.00001", "binlog20000.00002"},
			WorkDir:     "/data/dbbak/",
			ParseOnly:   false,
			ToolSet:     *tools.NewToolSetWithPickNoValidate(tools.ToolMysqlbinlog),
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
}

// RecoverBinlog TODO
type RecoverBinlog struct {
	TgtInstance native.InsObject `json:"tgt_instance" validate:"required"`
	RecoverOpt  *MySQLBinlogUtil `json:"recover_opt" validate:"required"`
	// 恢复时 binlog 存放目录，一般是下载目录
	BinlogDir string `json:"binlog_dir" validate:"required" example:"/data/dbbak/123456/binlog"`
	// binlog列表
	BinlogFiles []string `json:"binlog_files" validate:"required"`
	// binlog 解析所在目录，存放运行日志
	WorkDir string `json:"work_dir" validate:"required" example:"/data/dbbak/"`
	WorkID  string `json:"work_id" example:"123456"`
	// 仅解析 binlog，不做导入
	ParseOnly bool `json:"parse_only"`
	// 解析的并发度，默认 1
	ParseConcurrency int `json:"parse_concurrency"`
	// 指定要开始应用的第 1 个 binlog。如果指定，一般要设置 start_pos，如果不指定则使用 start_time
	// BinlogStartFile 只能由外部传入，不要内部修改
	BinlogStartFile string `json:"binlog_start_file"`

	// 如果启用 quick_mode，解析 binlog 时根据 filter databases 等选项过滤 row event，对 query event 会全部保留 。需要 mysqlbinlog 工具支持 --tables 选项，可以指定参数的 tools
	// 当 quick_mode=false 时，recover_opt 里的 databases 等选项无效，会应用全部 binlog
	QuickMode          bool   `json:"quick_mode"`
	SourceBinlogFormat string `json:"source_binlog_format" enums:",ROW,STATEMENT,MIXED"`

	// 恢复用到的客户端工具，不提供时会有默认值
	tools.ToolSet

	// /WorkDir/WorkID/
	taskDir         string
	dbWorker        *native.DbWorker // TgtInstance
	binlogCli       string
	mysqlCli        string
	filterOpts      string
	importScript    string
	parseScript     string
	binlogParsedDir string
	logDir          string
	// tools           tools.ToolSet
}

const (
	dirBinlogParsed = "binlog_parsed"
	importScript    = "import_binlog.sh"
	parseScript     = "parse_binlog.sh"
)

// MySQLClientOpt TODO
type MySQLClientOpt struct {
	MaxAllowedPacket int `json:"max_allowed_packet"`
	// 是否启用 --binary-mode
	BinaryMode bool `json:"binary_mode"`
}

func (r *RecoverBinlog) parse(f string) error {
	parsedName := fmt.Sprintf(`%s/%s.sql`, dirBinlogParsed, f)
	cmd := fmt.Sprintf("cd %s && %s %s/%s  >%s", r.taskDir, r.binlogCli, r.BinlogDir, f, parsedName)
	//logger.Info("run: %s", cmd)
	if outStr, err := osutil.ExecShellCommand(false, cmd); err != nil {
		return errors.Wrapf(err, "fail to parse %s: %s, cmd: %s", f, outStr, cmd)
	}
	return nil
}

// ParseBinlogFiles TODO
func (r *RecoverBinlog) ParseBinlogFiles() error {
	logger.Info("start to parse binlog files with concurrency %d", r.ParseConcurrency)

	errChan := make(chan error)
	tokenBulkChan := make(chan struct{}, r.ParseConcurrency)

	go func() {
		var wg = &sync.WaitGroup{}
		wg.Add(len(r.BinlogFiles))
		logger.Info("need parse %d binlog files: %s", len(r.BinlogFiles), r.BinlogFiles)

		for _, f := range r.BinlogFiles {
			tokenBulkChan <- struct{}{}
			go func(binlogFilePath string) {
				logger.Info("parse %s", binlogFilePath)
				err := r.parse(binlogFilePath)

				<-tokenBulkChan

				if err != nil {
					logger.Error("parse %s failed: %s", binlogFilePath, err.Error())
				}
				errChan <- err
				wg.Done()
			}(f)
		}
		wg.Wait()
		logger.Info("all binlog finish")
		close(errChan)
	}()
	for err := range errChan {
		if err != nil {
			return err
		}
	}
	return nil
}

// buildScript 创建 parse_binlog.sh, import_binlog.sh 脚本，需要调用执行
func (r *RecoverBinlog) buildScript() error {
	// 创建解析 binlog 的脚本，只是为了查看或者后面手动跑
	// 因为要并行解析，所以真正跑的是 ParseBinlogFiles
	parseCmds := []string{fmt.Sprintf("cd %s", r.taskDir)}
	for _, f := range r.BinlogFiles {
		if f == "" {
			continue
		}
		parsedName := fmt.Sprintf(`%s/%s.sql`, dirBinlogParsed, f)
		cmd := fmt.Sprintf("%s %s/%s  >%s 2>logs/parse_%s.err", r.binlogCli, r.BinlogDir, f, parsedName, f)
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
exit $retcode
`
	r.importScript = fmt.Sprintf(filepath.Join(r.taskDir, importScript))
	fi, err := os.OpenFile(r.importScript, os.O_CREATE|os.O_WRONLY, 0755)
	if err != nil {
		return err
	}
	defer fi.Close()
	if r.RecoverOpt.Flashback {
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
		}
		if err := tpl.Execute(fi, Vars); err != nil {
			return err
		}
	}
	return nil
}

// Init TODO
func (r *RecoverBinlog) Init() error {
	var err error
	// 工具路径初始化，检查工具路径, 工具可执行权限
	toolset, err := tools.NewToolSetWithPick(tools.ToolMysqlbinlog, tools.ToolMysqlclient, tools.ToolMysqlbinlogRollback)
	if err != nil {
		return err
	}
	if err = r.ToolSet.Merge(toolset); err != nil {
		return err
	}

	// quick_mode is only allowed when binlog_format=row
	if r.SourceBinlogFormat != "ROW" && r.QuickMode {
		r.QuickMode = false
		logger.Warn("quick_mode set to false because source_binlog_format != ROW")
	}
	// quick_mode=true 需要 mysqlbinlog 支持 --databases --tables 等选项
	if r.QuickMode && !r.RecoverOpt.Flashback {
		mysqlbinlogCli := r.ToolSet.MustGet(tools.ToolMysqlbinlog)
		checkMysqlbinlog := fmt.Sprintf(`%s --help |grep "\-\-tables="`, mysqlbinlogCli)
		if _, err := mysqlutil.ExecCommandMySQLShell(checkMysqlbinlog); err != nil {
			r.QuickMode = false
			logger.Warn("%s has not --tables option, set recover_binlog quick_mode=false", mysqlbinlogCli)
		}
	}
	if r.RecoverOpt.Flashback && !r.QuickMode {
		return errors.New("--flashback need quick_mode=true")
	}
	if r.RecoverOpt.StartTime != "" {
		if t, err := time.ParseInLocation(time.DateTime, r.RecoverOpt.StartTime, time.Local); err == nil {
			r.RecoverOpt.StartTime = t.Format(time.RFC3339)
		} else if _, err := time.ParseInLocation(time.RFC3339, r.RecoverOpt.StartTime, time.Local); err == nil {
			// keep
		} else {
			return errors.Errorf("unknown time format for start_time: %s", r.RecoverOpt.StartTime)
		}
	}

	if r.RecoverOpt.StopTime != "" {
		var stopTime time.Time
		if t, err := time.ParseInLocation(time.DateTime, r.RecoverOpt.StopTime, time.Local); err == nil {
			r.RecoverOpt.StopTime = t.Format(time.RFC3339)
		} else if _, err := time.ParseInLocation(time.RFC3339, r.RecoverOpt.StopTime, time.Local); err == nil {
			// keep
		} else {
			return errors.Errorf("unknown time format for stop_time: %s", r.RecoverOpt.StopTime)
		}
		stopTime, _ = time.ParseInLocation(time.RFC3339, r.RecoverOpt.StopTime, time.Local)
		if nowTime := time.Now(); nowTime.Compare(stopTime) < 0 {
			return errors.Errorf("StopTime [%s] cannot be greater than db current time [%s]",
				r.RecoverOpt.StopTime, nowTime)
		}
	}

	if err = r.initDirs(); err != nil {
		return err
	}
	if r.ParseConcurrency == 0 {
		r.ParseConcurrency = 1
	}
	// 检查目标实例连接性
	if r.RecoverOpt.Flashback || !r.ParseOnly {
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
	if r.RecoverOpt.Flashback && !r.ParseOnly {
		return errors.New("flashback=true must have parse_only=true")
	}
	return nil
}

func (r *RecoverBinlog) buildMysqlOptions() error {
	b := r.RecoverOpt
	mysqlOpt := r.RecoverOpt.MySQLClientOpt

	// init mysql client options
	var initCommands []string
	if b.NotWriteBinlog {
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

func (r *RecoverBinlog) buildBinlogOptions() error {
	b := r.RecoverOpt
	if b.StartPos == 0 && b.StartTime == "" {
		return errors.Errorf("start_time and start_pos cannot be empty both")
	}
	// 优先使用 start_pos
	if b.StartPos > 0 {
		if r.BinlogStartFile == "" {
			return errors.Errorf("start_pos must has binlog_start_file")
		} else {
			b.options += fmt.Sprintf(" --start-position=%d", b.StartPos)
			// 输入的 binlog 列表的第一个文件，就是 start_file
			// 同时要把 BinlogFiles 列表里面，binlog_start_file 之前的文件去掉
		}
	} else {
		if b.StartTime != "" {
			startTime, err := time.ParseInLocation(time.RFC3339, b.StartTime, time.Local)
			if err != nil {
				return errors.Errorf("start_time expect format %s but got %s", time.RFC3339, b.StartTime)
			}
			b.options += fmt.Sprintf(" --start-datetime='%s'", startTime.Local().Format(time.DateTime))
		}
	}
	if b.StopTime != "" {
		stopTime, err := time.ParseInLocation(time.RFC3339, b.StopTime, time.Local)
		if err != nil {
			return errors.Errorf("stop_time expect format %s but got %s", time.RFC3339, b.StopTime)
		}
		b.options += fmt.Sprintf(" --stop-datetime='%s'", stopTime.Local().Format(time.DateTime))
	} else {
		return errors.Errorf("stop_time cannot be empty")
	}
	b.options += " --base64-output=auto"
	// 严谨的情况，只有在确定源实例是 row full 模式下，才能启用 binlog 过滤条件，否则只能全量应用。
	// 但 --databases 等条件只对 row event 有效，在 query-event-handler=keep 情况下解析不会报错
	// 逻辑导入的库表过滤规则，跟 mysqlbinlog_rollback 的库表过滤规则不一样，这里先不处理 @todo
	// 如果 mysqlbinlog 没有 --tables 选项，也不能启用 quick_mode
	if r.QuickMode {
		if err := r.buildFilterOpts(); err != nil {
			return err
		}
	}
	if b.NotWriteBinlog {
		b.options += " --disable-log-bin"
	}
	binlogTool := ""
	if r.RecoverOpt.Flashback {
		binlogTool = r.ToolSet.MustGet(tools.ToolMysqlbinlogRollback)
	} else {
		binlogTool = r.ToolSet.MustGet(tools.ToolMysqlbinlog)
	}
	if b.IdempotentMode && mysqlbinlogHasOpt(binlogTool, "--idempotent") == nil {
		b.options += fmt.Sprintf(" --idempotent")
	} else if r.QuickMode {
		logger.Warn("idempotent=false and quick_mode=true may lead binlog-recover fail")
	}
	r.binlogCli += fmt.Sprintf("%s %s", binlogTool, r.RecoverOpt.options)
	logger.Info("mysqlbinlog parse cmd:%s", r.binlogCli)
	return nil
}

func (r *RecoverBinlog) buildFilterOpts() error {
	b := r.RecoverOpt
	r.filterOpts = ""
	if b.Flashback {
		r.filterOpts += " --flashback"
		if len(b.Databases) > 0 {
			r.filterOpts += fmt.Sprintf(" --flashback-databases='%s'", strings.Join(b.Databases, ","))
		}
		if len(b.Tables) > 0 {
			r.filterOpts += fmt.Sprintf(" --flashback-tables='%s'", strings.Join(b.Tables, ","))
		}
		if len(b.DatabasesIgnore) > 0 {
			r.filterOpts += fmt.Sprintf(" --flashback-databases-ignore='%s'", strings.Join(b.DatabasesIgnore, ","))
		}
		if len(b.TablesIgnore) > 0 {
			r.filterOpts += fmt.Sprintf(" --flashback-tables-ignore='%s'", strings.Join(b.TablesIgnore, ","))
		}
	} else {
		if len(b.Databases) > 0 {
			r.filterOpts += fmt.Sprintf(" --databases='%s'", strings.Join(b.Databases, ","))
		}
		if len(b.Tables) > 0 {
			r.filterOpts += fmt.Sprintf(" --tables='%s'", strings.Join(b.Tables, ","))
		}
		if len(b.DatabasesIgnore) > 0 {
			r.filterOpts += fmt.Sprintf(" --databases-ignore='%s'", strings.Join(b.DatabasesIgnore, ","))
		}
		if len(b.TablesIgnore) > 0 {
			r.filterOpts += fmt.Sprintf(" --tables-ignore='%s'", strings.Join(b.TablesIgnore, ","))
		}
	}

	if r.filterOpts == "" {
		logger.Warn("quick_mode=true shall works with binlog-filter data import")
	}
	if r.filterOpts == "" && !b.IdempotentMode {
		return errors.Errorf("no binlog-filter need idempotent_mode=true")
	}
	// query event 都全部应用，没法做部分过滤。前提是表结构已全部导入，否则导入会报错。也可以设置为 error 模式，解析时就会报错
	if b.QueryEventHandler == "" {
		b.QueryEventHandler = "keep"
	}
	r.filterOpts += fmt.Sprintf(" --query-event-handler=%s", b.QueryEventHandler)
	// 正向解析，不设置 --filter-statement-match-error
	if b.Flashback {
		if len(b.Tables) > 0 {
			r.filterOpts += fmt.Sprintf(" --filter-statement-match-error=\"%s\"", strings.Join(b.Tables, ","))
		} else {
			r.filterOpts += fmt.Sprintf(" --filter-statement-match-error=\"%s\"", strings.Join(b.Databases, ","))
		}
		r.filterOpts += fmt.Sprintf(" --filter-statement-match-ignore=\"flush ,FLUSH ,create table,CREATE TABLE\"")
	}
	r.filterOpts += fmt.Sprintf(" --filter-statement-match-ignore-force=\"%s\"", native.INFODBA_SCHEMA)
	b.options += " " + r.filterOpts
	return nil
}

func (r *RecoverBinlog) initDirs() error {
	if r.WorkID == "" {
		r.WorkID = newTimestampString()
	}
	r.taskDir = fmt.Sprintf("%s/recover_binlog_%s/%d", r.WorkDir, r.WorkID, r.TgtInstance.Port)
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

var ErrorBinlogMissing = errors.New("binlog missing")

func (r *RecoverBinlog) checkBinlogFiles() error {
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
func (r *RecoverBinlog) GetBinlogFilesFromDir(binlogDir, namePrefix string) ([]string, error) {
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
func (r *RecoverBinlog) PreCheck() error {
	var err error
	if err = r.buildMysqlOptions(); err != nil {
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
func (r *RecoverBinlog) FilterBinlogFiles() (totalSize int64, err error) {
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
	var startTimeMore, stopTimeMore time.Time // 前后时间偏移 20分钟
	var startTimeFilter, stopTimeFilter string
	if r.RecoverOpt.StartTime != "" {
		startTimeMore, _ = time.ParseInLocation(time.RFC3339, r.RecoverOpt.StartTime, time.Local)
		// binlog时间 start_time 比 预期start_time 提早 20 分钟
		startTimeFilter = startTimeMore.Add(-20 * time.Minute).Format(time.RFC3339)
	}
	if stopTimeMore, err = time.ParseInLocation(time.RFC3339, r.RecoverOpt.StopTime, time.Local); err != nil {
		return 0, errors.Errorf("stop_time parse failed: %s", r.RecoverOpt.StopTime)
	} else {
		// binlog时间 stop_time 比 预期stop_time 延后 20 分钟
		stopTimeFilter = stopTimeMore.Add(20 * time.Minute).Format(time.RFC3339)
	}

	for _, f := range r.BinlogFiles {
		fileName := filepath.Join(r.BinlogDir, f)
		// **** get binlog time
		// todo 如果是闪回模式，只从本地binlog获取，也可以读取 file mtime，确保不会出错
		events, err := bp.GetTimeIgnoreStopErr(fileName, true, true)
		if err != nil {
			return 0, err
		}
		startTime := events[0].EventTime
		stopTime := events[1].EventTime
		fileSize := cmutil.GetFileSize(fileName)
		// **** get binlog time

		if r.RecoverOpt.StopTime != "" && stopTime > stopTimeFilter {
			break
		}
		if r.BinlogStartFile != "" {
			binlogFiles = append(binlogFiles, f)
			totalSize += fileSize
		} else if r.RecoverOpt.StartTime != "" {
			if startTime > startTimeFilter { // time.RFC3339
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

func getSequenceFromFilename(binlogFileName string) int {
	file0Arr := strings.Split(binlogFileName, ".")
	return cast.ToInt(strings.TrimLeft(file0Arr[1], "0"))
}

func constructBinlogFilename(fileNameTmpl string, sequenceSuffix int) string {
	file0Arr := strings.Split(fileNameTmpl, ".")
	file0Arr1Len := cast.ToString(len(file0Arr[1]))
	fileNameFmt := "%s." + "%0" + file0Arr1Len + "d"
	newFileName := fmt.Sprintf(fileNameFmt, file0Arr[0], sequenceSuffix)
	return newFileName
}

// checkTimeRange 再次检查 binlog 时间
func (r *RecoverBinlog) checkTimeRange() error {
	startTime := r.RecoverOpt.StartTime
	stopTime := r.RecoverOpt.StopTime
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
func (r *RecoverBinlog) Start() error {
	binlogFiles := strings.Join(r.BinlogFiles, " ")
	if r.ParseOnly {
		if err := r.buildScript(); err != nil {
			return err
		}
		return r.ParseBinlogFiles()
	} else if !r.RecoverOpt.Flashback {
		if r.RecoverOpt.IdempotentMode {
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
		cmd := fmt.Sprintf(
			`cd %s; %s %s | %s >>%s 2>%s`,
			r.BinlogDir, r.binlogCli, binlogFiles, r.mysqlCli, outFile, errFile,
		)
		logger.Info(mysqlcomm.ClearSensitiveInformation(mysqlcomm.RemovePassword(cmd)))
		stdoutStr, err := mysqlutil.ExecCommandMySQLShell(cmd)
		if err != nil {
			if strings.TrimSpace(stdoutStr) == "" {
				if errContent, err := osutil.ExecShellCommand(
					false,
					fmt.Sprintf("head -2 %s", errFile),
				); err == nil {
					if strings.TrimSpace(errContent) != "" {
						logger.Error(errContent)
					}
				}
			} else {
				return errors.WithMessagef(err, "errFile: %s", errFile)
			}
			return err
		}
	} else {
		return errors.New("flashback=true must have parse_only=true")
	}
	return nil
}

// Import import_binlog.sh
func (r *RecoverBinlog) Import() error {
	if r.RecoverOpt.IdempotentMode {
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
	script := fmt.Sprintf(`cd %s && %s > import.log 2>import.err`, r.taskDir, r.importScript)
	logger.Info("run script: %s", script)
	_, err := osutil.ExecShellCommand(false, script)
	if err != nil {
		return errors.Wrap(err, "run import_binlog.sh")
	}
	return nil
}

// WaitDone TODO
func (r *RecoverBinlog) WaitDone() error {
	// 通过 lsof 查看 mysqlbinlog 当前打开的是那个 binlog，来判断进度
	return nil
}

// PostCheck TODO
func (r *RecoverBinlog) PostCheck() error {
	// 检查 infodba_schema.master_slave_heartbeat 里面的时间与 target_time 差异不超过 65s
	return nil
}

// GetDBWorker TODO
func (r *RecoverBinlog) GetDBWorker() *native.DbWorker {
	return r.dbWorker
}

// GetTaskDir TODO
func (r *RecoverBinlog) GetTaskDir() string {
	return r.taskDir
}
