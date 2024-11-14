package dbbackup_loader

import (
	"fmt"
	"path/filepath"
	"slices"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// LogicalLoader TODO
type LogicalLoader struct {
	*LoaderUtil
	MyloaderOpt   *LoaderOpt
	myloaderRegex string
}

// CreateConfigFile 要确保 buildFilter 在这之前运行
func (l *LogicalLoader) CreateConfigFile() error {
	cpuCores := 8
	if cpus, err := cmutil.GetCPUInfo(); err == nil {
		cpuCores = cpus.CoresLogical
	} else {
		logger.Warn("fail loader get cpu cores: ", err.Error())
	}
	p := l.LoaderUtil
	if l.myloaderRegex == "" {
		return errors.New("myloader config need filter regex")
	}
	loaderConfig := config.LogicalLoad{
		MysqlHost:     p.TgtInstance.Host,
		MysqlPort:     p.TgtInstance.Port,
		MysqlUser:     p.TgtInstance.User,
		MysqlPasswd:   p.TgtInstance.Pwd,
		MysqlCharset:  l.IndexObj.BackupCharset, // 尽量用备份原始备份里面的字符集
		MysqlLoadDir:  p.LoaderDir,
		IndexFilePath: p.IndexFilePath,
		Threads:       cpuCores,
		EnableBinlog:  p.EnableBinlog,
		InitCommand:   p.InitCommand,
		TableFilter: config.TableFilter{
			Regex: l.myloaderRegex,
		},
	}

	if loaderConfig.MysqlCharset == "" {
		loaderConfig.MysqlCharset = "binary"
	}
	if l.doDr {
		loaderConfig.DBListDropIfExists = native.INFODBA_SCHEMA
	}
	//logger.Info("dbloader config file, %+v", loaderConfig) // 有密码打印

	f := ini.Empty()
	section, err := f.NewSection("LogicalLoad")
	if err != nil {
		return err
	}
	if err = section.ReflectFrom(&loaderConfig); err != nil {
		return err
	}
	cfgFilePath := filepath.Join(p.TaskDir, fmt.Sprintf("dbloader_%d.cfg", p.TgtInstance.Port))
	if err = f.SaveTo(cfgFilePath); err != nil {
		return errors.Wrap(err, "create config")
	}
	p.cfgFilePath = cfgFilePath
	//logger.Info("tmp dbloader config file %s", p.cfgFilePath) // 有密码打印
	return nil
}

// PreLoad 在解压之前做的事情
// 检查实例连通性
func (l *LogicalLoader) PreLoad() error {
	err := l.buildFilter()
	if err != nil {
		return err
	}
	return nil
}

// Load 恢复数据
// 1. create config 2. loadbackup
func (l *LogicalLoader) Load() error {
	if err := l.CreateConfigFile(); err != nil {
		return err
	}

	// set variables
	dbWorker, err := l.TgtInstance.Conn()
	if err != nil {
		return errors.Wrap(err, "目标实例连接失败")
	}
	defer dbWorker.Stop()
	if _, err = dbWorker.Exec("set global init_connect=''"); err != nil { // 禁用 init_connect，这里为了兼容跑一次置空
		logger.Warn("failed to set global init_connect='' for %d. ignore %s", l.TgtInstance.Port, err.Error())
	}
	// 关闭慢查询
	originalValue, err := dbWorker.SetSingleGlobalVarAndReturnOrigin("slow_query_log", "off")
	if err != nil {
		logger.Warn("failed to set global slow_query_log=off for %d. ignore %s", l.TgtInstance.Port, err.Error())
	} else {
		defer dbWorker.SetSingleGlobalVar("slow_query_log", originalValue)
	}
	if err := l.loadBackup(); err != nil {
		return err
	}
	return nil
}

func (l *LogicalLoader) loadBackup() error {
	cmdArgs := []string{"loadbackup", "--config", l.cfgFilePath}
	if l.LogDir != "" {
		cmdArgs = append(cmdArgs, "--log-dir", l.LogDir)
	}
	cmd := []string{l.Client}
	cmd = append(cmd, cmdArgs...)
	logger.Info("dbLoader cmd: %s", strings.Join(cmd, " "))
	_, errStr, err := cmutil.ExecCommand(false, l.TaskDir, cmd[0], cmd[1:]...)
	if err != nil {
		logger.Error("logical dbbackup loadbackup stderr: ", errStr)
		return errors.Wrap(err, errStr)
	}

	return nil
}

// buildFilter 只有逻辑备份才有 filter options, myloader filter regex 存入 myloaderRegex
func (l *LogicalLoader) buildFilter() error {
	opt := l.MyloaderOpt
	// TODO 待重写，Databases 分不清是哪个？
	if opt != nil {
		if len(opt.Databases)+len(opt.Tables)+len(opt.IgnoreDatabases)+len(opt.IgnoreTables) == 0 {
			// schema/data 一起全部导入, recover-binlog quick_mode只能false
			logger.Info("no filter: import schema and data together, recover-binlog need quick_mode=false")
			l.doDr = true // todo 待优化，如果导出的文件里面只有少数 databases，即使全导入也不是 doDr 模式
		}
		if len(opt.Databases) > 0 && len(opt.Tables) > 0 && opt.Databases[0] == "*" && opt.Tables[0] == "*" &&
			len(opt.IgnoreDatabases)+len(opt.IgnoreTables) == 0 {
			l.doDr = true
		}
		if len(opt.Databases) == 0 {
			l.Databases = []string{"*"}
		}
		if len(opt.Tables) == 0 {
			l.Tables = []string{"*"}
		}
		if opt.WillRecoverBinlog && opt.SourceBinlogFormat != "ROW" {
			// 指定 filter databases/tables（或者指定无效）,导入数据时
			// 必须全部导入 schema 和 data.恢复时也恢复全量 binlog,即 quick_mode=false
			logger.Info("binlog_format!=row: import schema and data together, recover-binlog need quick_mode=false")
			l.doDr = true
		} else {
			// 后续不恢复binlog
			// 或者，后续要恢复binlog，且源binlog格式是row，可以只导入需要的表
			l.Databases = opt.Databases
			l.Tables = opt.Tables
			l.ExcludeDatabases = opt.IgnoreDatabases
			l.ExcludeTables = opt.IgnoreTables
		}
	} else {
		l.doDr = true
	}
	if l.doDr == true {
		l.Databases = []string{"*"}
		l.Tables = []string{"*"}
	}
	// build regex
	ignoreDbs := l.ExcludeDatabases
	if l.doDr {
		ignoreDbs = slices.DeleteFunc(native.DBSys, func(s string) bool {
			return s == "infodba_schema"
		})
	}

	if filter, err := db_table_filter.NewFilter(
		l.Databases,
		l.Tables,
		// l.ExcludeDatabases, ToDo xiaog 确认
		ignoreDbs,
		l.ExcludeTables,
	); err != nil {
		return err
	} else {
		//l.myloaderRegex = filter.MyloaderRegex(l.doDr) ToDo xiaog 确认
		l.myloaderRegex = filter.TableFilterRegex()
	}
	return nil
}
