package restore

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
)

const (
	// GrepError TODO
	GrepError = `grep -iP '\[FATAL\]|\[ERROR\]| ERROR | FATAL |^ERROR |^FATAL '  `
)

// MLoadParam TODO
type MLoadParam struct {
	Client   string   `json:"client" validate:"required"`
	Host     string   `json:"host"`
	Port     int      `json:"port"`
	User     string   `json:"user"`
	Password string   `json:"password"`
	Charset  string   `json:"charset" validate:"required"`
	PathList []string `json:"pathList"` // 绝对路径列表
	// 不写 binlog -without-binlog: set sql_log_bin=0
	WithOutBinlog   bool     `json:"withoutBinlog"`
	NoData          bool     `json:"noData"`
	NoCreateTable   bool     `json:"noCreateTable"`
	Databases       []string `json:"databases"`
	Tables          []string `json:"tables"`
	IgnoreDatabases []string `json:"ignoreDatabases"`
	IgnoreTables    []string `json:"ignoreTables"`

	TaskDir string `json:"taskDir"`
	// 导入全量 schema, 仅在允许分开导入 schema 和 data 的情况下有效(有 filterOpts 且 要恢复 binlog 且 binlog_format=row)
	flagApartSchemaData bool
	// 标记是否已经导入 schema
	flagSchemaImported int
	// 标记是否已导入 data
	flagDataImported int

	db *native.DbWorker // 本地db链接
	// 转化 --databases ... --tables... 之后的子串拼接
	filterOpts string

	// 内部检查相关
	checkMLoadProcess bool
	mloadScript       string
}

// MLoadCheck TODO
func (m *MLoadParam) MLoadCheck() error {
	// 判断MLoad工具存在
	if err := cmutil.FileExistsErr(m.Client); err != nil {
		return err
	}
	// 判断MLoad工具可执行
	return nil
}

func (m *MLoadParam) initFilterOpt() error {
	// MLOAD.pl的过滤选项，当指定了 --databases 时，一切已 databases 作为基准，即 --tables, --ignore-tables 都是在 database 里过滤
	// 当指定 --ignore-databases 时，不能有其它过滤选项
	if len(m.IgnoreDatabases) > 0 && (len(m.Tables) > 0 || len(m.IgnoreTables) > 0) {
		return errors.New("MLOAD.pl --ignore-databases should has no other filter options")
	}
	if len(m.Databases) != 1 && len(m.Tables) > 0 {
		return errors.New("MLOAD.pl --tables should has only one database using --databases")
	}
	if len(m.Databases) != 1 && len(m.IgnoreTables) > 0 {
		return errors.New("MLOAD.pl --ignore-tables should has only one database using --databases")
	}
	if len(m.Databases) > 0 && len(m.IgnoreDatabases) > 0 {
		return errors.New("MLOAD.pl --databases and --ignore-databases cannot work together")
	}
	if len(m.Tables) > 0 && len(m.IgnoreTables) > 0 {
		return errors.New("MLOAD.pl --tables and --ignore-tables cannot work together")
	}

	if len(m.Databases) > 0 {
		m.filterOpts += fmt.Sprintf(" --databases=%s", strings.Join(m.Databases, ","))
	}
	if len(m.Tables) > 0 {
		m.filterOpts += fmt.Sprintf(" --tables=%s", strings.Join(m.Tables, ","))
	}
	if len(m.IgnoreTables) > 0 {
		m.filterOpts += fmt.Sprintf(" --ignore-tables=%s", strings.Join(m.IgnoreTables, ","))
	}
	if len(m.IgnoreDatabases) > 0 {
		logger.Info("mload ignore-databases=%v", m.IgnoreDatabases)
		m.filterOpts += fmt.Sprintf(
			" --ignore_not_exist_dbs --ignore-databases=%s",
			strings.Join(m.IgnoreDatabases, ","),
		)
	}
	return nil
}

// Run TODO
func (m *MLoadParam) Run() error {
	if err := m.MLoadCheck(); err != nil {
		return err
	}
	if err := m.initFilterOpt(); err != nil {
		return err
	}
	return m.MLoadData()
}

// MLoadData TODO
func (m *MLoadParam) MLoadData() error {
	defer func() {
		if r := recover(); r != nil {
			logger.Error("MLoadData panic, err:%+v, stack:%s", r, string(debug.Stack()))
		}
	}()
	logger.Info("MLoadParam: %+v", m)
	for i, filePath := range m.PathList {
		var logFile = fmt.Sprintf("%s/MLoad_backup_%d_%d.log", m.TaskDir, i, m.Port)
		// load日志是追加的方式，之前的错误会被统计到本次
		if err := os.RemoveAll(logFile); err != nil {
			logger.Warn("remove %s failed, err:%w", logFile, err)
		}
		m.mloadScript = fmt.Sprintf(
			"/usr/bin/perl %s -u%s -p%s -h %s -P %d --charset=%s -L %s --conc %d  --path=%s",
			m.Client, m.User, m.Password, m.Host, m.Port, m.Charset, logFile, runtime.NumCPU(), filePath,
		)
		if m.WithOutBinlog {
			m.mloadScript += ` --without-binlog `
		}
		if m.NoData {
			m.mloadScript += ` --no-data`
		}
		if m.NoCreateTable {
			m.mloadScript += ` --no-create-table`
		}
		if m.filterOpts != "" {
			m.mloadScript += " " + m.filterOpts
		}

		logger.Info("MLoad script:%s", mysqlutil.RemovePassword(m.mloadScript))
		cmd := &osutil.FileOutputCmd{
			Cmd: exec.Cmd{
				Path: "/bin/bash",
				Args: []string{"/bin/bash", "-c", m.mloadScript},
			},
			StdOutFile: logFile,
			StdErrFile: logFile,
		}
		if err := cmd.Start(); err != nil {
			return errors.WithStack(err)
		}
		done := make(chan error, 1)
		go func(cmd *osutil.FileOutputCmd) {
			done <- cmd.Wait()
		}(cmd)

		interval := 10 * time.Second // 每 10s 检查一次 mload
		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		// 检查任务进程
		// 检查进程是否还在运行
		var counter int
		for {
			stop := false
			select {
			case err := <-done:
				if err != nil {
					if _, _, err2 := m.checkMLoadComplete(logFile); err2 != nil {
						return errors.Wrap(err, err2.Error())
					}
					return fmt.Errorf("MLoad导入失败, 命令:%s, 错误:%w", mysqlutil.RemovePassword(m.mloadScript), err)
				}
				stop = true
			case <-ticker.C:
				_, runningDBS, err := checkExistRunningDbLoad(m.db, m.checkMLoadProcess, m.Databases)
				if err != nil {
					logger.Warn("checkExistRunningMLoad failed, err:%w", err)
				}
				counter++
				if counter%12 == 0 {
					logger.Info("checkExistRunningMLoad runningDBS: %+v", runningDBS)
				}
			}
			if stop {
				break
			}
		}

		// 检查结果
		isSuccess, errorNum, err := m.checkMLoadComplete(logFile)
		if err != nil {
			return err
		}
		if !isSuccess {
			return fmt.Errorf("MLoad导入失败，error数量：%d, 具体请查看错误日志文件：<br>%s", errorNum, logFile)
		}
	}
	return nil
}

func (m *MLoadParam) checkMLoadComplete(errFile string) (bool, int, error) {
	script := GrepError + errFile + ` |wc -l`
	out, err := exec.Command("/bin/bash", "-c", script).CombinedOutput()
	if err != nil {
		return false, 0, errors.Wrap(err, script)
	}
	outStr := strings.TrimSpace(string(out))
	errorNum, err := strconv.Atoi(outStr)
	if err != nil {
		return false, 0, errors.Wrapf(err, "命令 %s 的结果转换失败.结果：%s", script, outStr)
	}
	if errorNum > 0 {
		// 尝试从 mload 日志里面
		scriptErr := GrepError + errFile + ` |tail -1 |awk -F ' ' '{print $NF}'`
		if out, err := exec.Command("/bin/bash", "-c", scriptErr).CombinedOutput(); err == nil {
			loadErrFile := strings.TrimSpace(string(out))
			if out, err := exec.Command("/bin/bash", "-c", "grep -i error "+loadErrFile+" | head -2").
				CombinedOutput(); err == nil {
				errInfo := strings.TrimSpace(string(out))
				if errInfo != "" {
					return false, errorNum, errors.Errorf("error num: %d, error info: %s", errorNum, errInfo)
				}
			} else {
				return false, errorNum, errors.Errorf("error num: %d, error file: %s", errorNum, loadErrFile)
			}
		}
		return false, errorNum, errors.Errorf("存在%d处错误. 命令：%s", errorNum, script)
	}

	var isComplete = 0
	script = `grep '\[COMPLETE\]' ` + errFile + ` |wc -l`
	out, err = exec.Command("/bin/bash", "-c", script).CombinedOutput()
	if err != nil {
		return false, 0, errors.Wrap(err, script)
	}
	outStr = strings.TrimSpace(string(out))
	isComplete, err = strconv.Atoi(outStr)
	if err != nil {
		return false, 0, errors.Wrapf(err, "命令 %s 的结果转换失败.结果：%s", script, outStr)
	}
	if isComplete < 1 {
		return false, 0, errors.Wrapf(err, "COMPLETE not found。返回：%s", outStr)
	}

	return true, 0, nil
}
