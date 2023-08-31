package dbloader

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
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
	p := l.LoaderUtil
	if l.myloaderRegex == "" {
		return errors.New("myloader config need filter regex")
	}
	loaderConfig := config.LogicalLoad{
		MysqlHost:     p.TgtInstance.Host,
		MysqlPort:     p.TgtInstance.Port,
		MysqlUser:     p.TgtInstance.User,
		MysqlPasswd:   p.TgtInstance.Pwd,
		MysqlCharset:  l.IndexObj.BackupCharset,
		MysqlLoadDir:  p.LoaderDir,
		IndexFilePath: p.IndexFilePath,
		Threads:       4,
		EnableBinlog:  !l.WithOutBinlog,
		Regex:         l.myloaderRegex,
	}
	if loaderConfig.MysqlCharset == "" {
		loaderConfig.MysqlCharset = "binary"
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
	if err := l.buildFilter(); err != nil {
		return err
	}

	dbWorker, err := l.TgtInstance.Conn()
	if err != nil {
		return errors.Wrap(err, "目标实例连接失败")
	}
	defer dbWorker.Stop()
	return nil
}

// Load 恢复数据
// 1. create config 2. loadbackup
func (l *LogicalLoader) Load() error {
	if err := l.CreateConfigFile(); err != nil {
		return err
	}

	if err := l.loadBackup(); err != nil {
		return err
	}
	return nil
}

func (l *LogicalLoader) loadBackup() error {
	cmdArgs := []string{"loadbackup", "--config", l.cfgFilePath}
	cmd := []string{l.Client}
	cmd = append(cmd, cmdArgs...)
	logger.Info("dbLoader cmd: %s", strings.Join(cmd, " "))
	outStr, errStr, err := cmutil.ExecCommand(false, l.TaskDir, cmd[0], cmd[1:]...)
	if err != nil {
		logger.Info("dbbackup loadbackup stdout: %s", outStr)
		return errors.Wrap(err, errStr)
	}
	return nil
}

// buildFilter 只有逻辑备份才有 filter options, myloader filter regex 存入 myloaderRegex
func (l *LogicalLoader) buildFilter() error {
	o := l.MyloaderOpt
	if o != nil {
		if len(o.Databases) == 0 {
			l.Databases = []string{"*"}
		}
		if len(o.Tables) == 0 {
			l.Tables = []string{"*"}
		}
		if len(o.Databases)+len(o.Tables)+len(o.IgnoreDatabases)+len(o.IgnoreTables) == 0 {
			// schema/data 一起全部导入, recover-binlog quick_mode只能false
			logger.Info("no filter: import schema and data together, recover-binlog need quick_mode=false")
			l.doDr = true
		}
		if o.WillRecoverBinlog && o.SourceBinlogFormat != "ROW" {
			// 指定 filter databases/tables（或者指定无效）,导入数据时
			// 必须全部导入 schema 和 data.恢复时也恢复全量 binlog,即 quick_mode=false
			logger.Info("binlog_format!=row: import schema and data together, recover-binlog need quick_mode=false")
			l.doDr = true
		} else {
			// 后续不恢复binlog
			// 或者，后续要恢复binlog，且源binlog格式是row，可以只导入需要的表
			l.Databases = o.Databases
			l.Tables = o.Tables
			l.ExcludeDatabases = o.IgnoreDatabases
			l.ExcludeTables = o.IgnoreTables
		}
	} else {
		l.doDr = true
	}
	if l.doDr == true {
		l.Databases = []string{"*"}
		l.Tables = []string{"*"}
	}
	// build regex
	if filter, err := db_table_filter.NewDbTableFilter(
		l.Databases,
		l.Tables,
		l.ExcludeDatabases,
		l.ExcludeTables,
	); err != nil {
		return err
	} else {
		l.myloaderRegex = filter.MyloaderRegex(l.doDr)
	}
	return nil
}
