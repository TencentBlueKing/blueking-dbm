package backupexe

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/pkg/errors"
)

// PhysicalTokudbLoader this is used to load physical backup
// decompress, apply, recover
type PhysicalTokudbLoader struct {
	cnf           *config.BackupConfig
	dbbackupHome  string
	mysqlVersion  string
	storageEngine string
}

func (p *PhysicalTokudbLoader) initConfig(indexContent *dbareport.IndexContent) error {
	if p.cnf == nil {
		return errors.New("tokudb loader params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		p.dbbackupHome = filepath.Dir(cmdPath)
	}

	p.mysqlVersion, _ = util.VersionParser(indexContent.MysqlVersion)
	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	return nil
}

// Execute excute loading backup with physical backup tool
func (p *PhysicalTokudbLoader) Execute() error {
	if p.storageEngine != cst.StorageEngineTokudb {
		err := fmt.Errorf("%s engine not supported", p.storageEngine)
		logger.Log.Error(err)
		return err
	}

	err := p.load()
	if err != nil {
		return err
	}

	return nil
}

// load tokudb_recovery.pl
func (p *PhysicalTokudbLoader) load() error {
	binPath := filepath.Join(p.dbbackupHome, "bin", "tokudb_recovery.pl")

	args := []string{fmt.Sprintf("--defaults-file=%s", p.cnf.PhysicalLoad.DefaultsFile)}
	args = append(args, fmt.Sprintf("--backup-path=%s", p.cnf.PhysicalLoad.MysqlLoadDir))

	// 日志输出到当前目录的 logs/loader_tokudb_xx.log
	pwd, _ := os.Getwd()
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("loader_%s_%d_%d.log",
		p.storageEngine, p.cnf.Public.MysqlPort, int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("tokudb recover command:", binPath, strings.Join(args, " "))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("tokudb recover failed: ", err, errStr)
		errStrPrefix := fmt.Sprintf("tail 5 error from %s", logfile)
		errStrDetail, _ := cmutil.NewGrepLines(logfile, true, false).MatchWords([]string{"ERROR", "fatal"}, 5)
		if len(errStrDetail) > 0 {
			logger.Log.Info(errStrPrefix)
			logger.Log.Error(errStrDetail)
		} else {
			logger.Log.Warn("tail can not find more detail error message from ", logfile)
		}
		return errors.WithMessagef(err, fmt.Sprintf("%s\n%s", errStrPrefix, errStrDetail))
	}
	logger.Log.Info("tokudb recover success: ", outStr)
	return nil
}
