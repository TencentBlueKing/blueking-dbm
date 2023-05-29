package restore

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
)

// XLoadParam TODO
type XLoadParam struct {
	Client       string `json:"client"`
	TaskDir      string `json:"taskDir"` // taskDir 已经包含了 work_id
	FilePath     string `json:"filePath"`
	MyCnfFile    string `json:"myCnfFile"`
	MysqlDataDir string `json:"mysqlDataDir"`

	Host string `json:"host"`
}

// XLoadCheckParam TODO
type XLoadCheckParam struct {
	Client string `json:"client"`
}

// XLoadData TODO
func XLoadData(m XLoadParam) error {
	logger.Info("XLoadData param: %+v", m)
	xloadLogFile := fmt.Sprintf("%s/xload.log", m.TaskDir)
	xloadLogoutFile := fmt.Sprintf("%s/xload.out", m.TaskDir)

	// generate log4perl.conf
	log4perlConf := fmt.Sprintf("%s/log4perl.conf", m.TaskDir)
	logConfContent := `log4perl.rootLogger=INFO, LOGFILE
log4perl.appender.LOGFILE = Log::Log4perl::Appender::File
log4perl.appender.LOGFILE.filename = ` + xloadLogFile
	logConfContent = logConfContent + `
log4perl.appender.LOGFILE.mode = append
log4perl.appender.LOGFILE.layout = PatternLayout
log4perl.appender.LOGFILE.layout.ConversionPattern = %d %-5p %c %F:%L - %m%n`

	if err := ioutil.WriteFile(log4perlConf, []byte(logConfContent), os.ModePerm); err != nil {
		return fmt.Errorf("write %s failed, err:%w", log4perlConf, err)
	}

	// do xload
	backupPath := m.FilePath // fmt.Sprintf("%s/%s", m.TaskDir, m.FilePath)
	script := fmt.Sprintf(
		`/usr/bin/perl %s --backup-path=%s --defaults-file=%s --log-config-file=%s `,
		m.Client, backupPath, m.MyCnfFile, log4perlConf,
	)
	logger.Info("XLoadData: %s", script)
	cmd := &osutil.FileOutputCmd{
		Cmd: exec.Cmd{
			Path: "/bin/bash",
			Args: []string{"/bin/bash", "-c", script},
		},
		StdOutFile: xloadLogoutFile,
		StdErrFile: xloadLogoutFile,
	}
	if err := cmd.Start(); err != nil {
		return err
	}

	done := make(chan error, 1)

	go func(cmd *osutil.FileOutputCmd) {
		done <- cmd.Wait()
	}(cmd)

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	// 检查任务进程
	// 检查进程是否还在运行
For:
	for {
		select {
		case err := <-done:
			if err != nil {
				return errors.Wrapf(err, "xload导入数据失败, script:%s", script)
			}
			break For
		case <-ticker.C:
			_, _, _ = m.checkExistRunningXLoad()
		}
	}

	// 检查结果
	isSuccess, errorNum, err := m.checkXLoadComplete(xloadLogFile)
	if err != nil {
		return err
	}
	if !isSuccess {
		return errors.Errorf("xload导入失败，error数量：%d, 错误详情：%s", errorNum, xloadLogFile)
	}

	// chown mysqldata
	command := fmt.Sprintf("cd %s;chown -R mysql mysqldata;", m.MysqlDataDir)
	_, err = exec.Command("/bin/bash", "-c", command).CombinedOutput()
	if err != nil {
		return errors.Wrap(err, script)
	}

	return nil
}

// checkExistRunningXLoad 检查进程
func (m *XLoadParam) checkExistRunningXLoad() (bool, []string, error) {
	return true, nil, nil
}

func (m *XLoadParam) checkXLoadComplete(errFile string) (bool, int, error) {
	script := GrepError + errFile + ` |wc -l`
	out, err := exec.Command("/bin/bash", "-c", script).CombinedOutput()
	if err != nil {
		return false, 0, errors.Wrap(err, script)
	}
	outStr := strings.TrimSpace(string(out))
	errorNum, err := strconv.Atoi(outStr)
	if err != nil {
		return false, 0, errors.Wrapf(err, "命令: %s 的结果转换失败.结果：%s", script, outStr)
	}
	if errorNum > 0 {
		return false, errorNum, errors.Errorf("存在 %s 处错误. 命令：%s", outStr, script)
	}

	script = `grep 'task is COMPLETE' ` + errFile + ` |wc -l`
	out, err = exec.Command("/bin/bash", "-c", script).CombinedOutput()
	if err != nil {
		return false, 0, errors.Wrap(err, script)
	}
	outStr = strings.TrimSpace(string(out))
	isComplete, err := strconv.Atoi(outStr)
	if err != nil {
		return false, 0, errors.Wrapf(err, "命令: %s 的结果转换失败.结果：%s", script, outStr)
	}
	if isComplete < 1 {
		return false, 0, errors.New("COMPLETE not found。返回：" + outStr)
	}

	return true, 0, nil
}
