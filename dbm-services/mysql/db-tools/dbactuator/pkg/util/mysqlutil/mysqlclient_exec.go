/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil

import (
	"bytes"
	"context"
	"database/sql"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path"
	"strings"
	"sync"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/mysqlcomm"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/marker"
)

// ExecuteSqlAtLocal 本地 mysql client 执行 SQL。
// WorkDir 必传：sql 文件与 ErrFile 均相对该目录拼接；为空会在执行入口直接报错。
type ExecuteSqlAtLocal struct {
	MySQLBinPath     string
	WorkDir          string `json:"workdir"` // 必传，sql/err 文件工作目录
	IsForce          bool   `json:"isForce"`
	Charset          string `json:"charset"`
	NeedShowWarnings bool   `json:"needShowWarnings"`
	Host             string `json:"host"`
	Port             int    `json:"port"`
	Socket           string `json:"socket"`
	User             string `json:"user"`
	Password         string `json:"password"`
	ErrFile          string
}

func (e ExecuteSqlAtLocal) requireWorkDir() error {
	if util.StrIsEmpty(e.WorkDir) {
		return errors.New("ExecuteSqlAtLocal.WorkDir 不能为空，请显式指定 sql/err 文件所在目录")
	}
	return nil
}

// CreateLoadSQLCommand TODO
func (e ExecuteSqlAtLocal) CreateLoadSQLCommand() (command string) {
	var forceStr, mysqlclient string
	if e.IsForce {
		forceStr = " -f "
	}
	mysqlclient = e.MySQLBinPath
	if util.StrIsEmpty(e.MySQLBinPath) {
		mysqlclient = cst.MySQLClientPath
	}
	connCharset := ""
	if !util.StrIsEmpty(e.Charset) {
		connCharset = fmt.Sprintf(" --default-character-set=%s ", e.Charset)
	}
	passwd := ""
	if !util.StrIsEmpty(e.Password) {
		passwd = fmt.Sprintf("-p%s", e.Password)
	}
	// 如果socket不存在的话的,选择连接tcp的方式导入
	if util.StrIsEmpty(e.Socket) {
		return fmt.Sprintf(
			`%s %s --safe_updates=0 -u %s %s -h%s -P %d  %s -vvv `,
			mysqlclient, forceStr, e.User, passwd, e.Host, e.Port, connCharset,
		)
	}
	return fmt.Sprintf(
		`%s %s --safe_updates=0 -u %s %s  --socket=%s %s -vvv `,
		mysqlclient, forceStr, e.User, passwd, e.Socket, connCharset,
	)
}

// ExecuteSqlByMySQLClient TODO
func (e ExecuteSqlAtLocal) ExecuteSqlByMySQLClient(sqlfile string, targetdbs []string) (err error) {
	for _, db := range targetdbs {
		if err = e.ExecuteSqlByMySQLClientOne(sqlfile, db, true); err != nil {
			return err
		}
	}
	return nil
}

// ExecuteSqlWithOutReport TODO
func (e ExecuteSqlAtLocal) ExecuteSqlWithOutReport(sqlfile string, targetdbs []string) (err error) {
	for _, db := range targetdbs {
		if err = e.ExecuteSqlByMySQLClientOne(sqlfile, db, false); err != nil {
			return err
		}
	}
	return nil
}

// BuildExecuteErrFileBase 拼装 ExecuteSqlByMySQLClientOne 的 err 文件名（不含目录）。
// 格式: {sqlfile}.{db}.err；db 为空时为 {sqlfile}.err。
// 始终使用 path.Base(sqlfile)，避免 sqlfile 含目录时把 ErrFile 写到不存在的相对子目录。
func BuildExecuteErrFileBase(sqlfile, db string) string {
	base := path.Base(sqlfile)
	db = strings.TrimSpace(db)
	if db == "" {
		return fmt.Sprintf("%s.err", base)
	}
	return fmt.Sprintf("%s.%s.err", base, db)
}

// ExecuteSqlByMySQLClientOne 使用本地mysqlclient 去执行sql
//
//	@receiver e
//	@receiver sqlfile
//	@receiver targetdbs
//	@return err
func (e ExecuteSqlAtLocal) ExecuteSqlByMySQLClientOne(sqlfile string, db string, report bool) (err error) {
	if err = e.requireWorkDir(); err != nil {
		return err
	}
	command := e.CreateLoadSQLCommand()
	command = command + " " + db + "<" + path.Join(e.WorkDir, sqlfile)
	e.ErrFile = path.Join(e.WorkDir, BuildExecuteErrFileBase(sqlfile, db)) // 删除原有的时间戳方便调用方拼接
	logger.Info("Run sql file %s", mysqlcomm.ClearSensitiveInformation(command))

	// 通过 marker 协议向 stdout 发出 begin/end 事件，便于上游 (dbm-ui backend)
	// 解析 log_content 切分出每个 db 的执行边界。详见 pkg/util/marker。
	marker.Emit(marker.Event{Event: marker.EventExecDBBegin, DB: db})
	err = e.ExecuteCommand(command, report)
	endEv := marker.Event{Event: marker.EventExecDBEnd, DB: db}
	if err != nil {
		endEv.Err = err.Error()
	}
	marker.Emit(endEv)
	if err != nil {
		return err
	}
	return nil
}

// TestConnectionByMySQLClient TODO
func (e ExecuteSqlAtLocal) TestConnectionByMySQLClient(db string, report bool) (err error) {
	if err = e.requireWorkDir(); err != nil {
		return err
	}
	command := e.CreateLoadSQLCommand()
	command = fmt.Sprintf(`echo "select version()" | %s %s`, command, db)
	e.ErrFile = path.Join(e.WorkDir, fmt.Sprintf("test_connection_%s.err", db)) // 删除原有的时间戳方便调用方拼接
	err = e.ExecuteCommand(command, report)
	if err != nil {
		return err
	}
	return nil
}

// ExecuteCommand TODO
func (e ExecuteSqlAtLocal) ExecuteCommand(command string, report bool) (err error) {
	var stderrBuf bytes.Buffer
	var errStdout, errStderr error
	logger.Info("The Command Is %s", mysqlcomm.ClearSensitiveInformation(command))
	cmd := exec.Command("/bin/bash", "-c", command)
	stdoutIn, _ := cmd.StdoutPipe()
	stderrIn, _ := cmd.StderrPipe()

	// 写入error 文件
	ef, errO := os.OpenFile(e.ErrFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if errO != nil {
		logger.Error("打开错误日志失败! %s", errO.Error())
		return errors.Wrapf(errO, "打开错误日志失败: %s", e.ErrFile)
	}
	defer ef.Close()
	defer ef.Sync()
	// 标准输出复制一份到错误文件中
	stdout := io.MultiWriter(os.Stdout)
	// stdout := io.MultiWriter(os.Stdout, ef)
	// 错误不输出控制台 去掉os.Stderr
	// stderr := io.MultiWriter(os.Stderr, &stderrBuf, ef)
	stderr := io.MultiWriter(&stderrBuf, ef)
	if !report {
		stderr = io.MultiWriter(&stderrBuf, ef)
	}

	if err = cmd.Start(); err != nil {
		logger.Error("start command failed:%s", err.Error())
		return
	}

	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		_, errStdout = io.Copy(stdout, stdoutIn)
		wg.Done()
	}()

	// 管道stderrIn输出到stderr。stderr又写到&stderrBuf、ef
	_, errStderr = io.Copy(stderr, stderrIn)

	wg.Wait()

	// Start 成功后必须 Wait，避免 capture 失败时留下残留进程
	waitErr := cmd.Wait()
	if errStdout != nil || errStderr != nil {
		logger.Error("failed to capture stdout or stderr\n")
		return errors.Errorf(
			"failed to capture stdout or stderr: stdout=%v, stderr=%v, wait=%v",
			errStdout, errStderr, waitErr,
		)
	}
	if waitErr != nil {
		errStr := string(stderrBuf.Bytes())
		logger.Error("exec failed:%s,stderr: %s", waitErr.Error(), errStr)
		return waitErr
	}

	return nil
}

// ExecutePartitionByMySQLClient TODO
func (e ExecuteSqlAtLocal) ExecutePartitionByMySQLClient(
	dbw *sql.DB, partitionsql string,
	lock *sync.Mutex,
) (err error) {
	logger.Info("The partitionsql is %s", mysqlcomm.ClearSensitiveInformation(partitionsql))
	err = util.Retry(
		util.RetryConfig{Times: 2, DelayTime: 2 * time.Second}, func() error {
			var myerr error
			// context.Background()被用作dbw.Conn方法的参数，这个数据库连接不会被自动取消，也没有截止日期。
			db, myerr := dbw.Conn(context.Background())
			if myerr != nil {
				return myerr
			}
			partitionsqls := strings.Split(partitionsql, ";;;")
			for _, psql := range partitionsqls {
				_, myerr = db.ExecContext(context.Background(), psql)
			}
			return myerr
		},
	)
	if err != nil {
		logger.Error("分区执行失败！%s", err)
		return err
	}
	return nil
}

// ExecuteInitPartition TODO
func (e ExecuteSqlAtLocal) ExecuteInitPartition(command string) (err error) {
	// e.ErrFile = path.Join(e.WorkDir, e.ErrFile)
	err = e.MyExecuteCommand(command)
	if err != nil {
		return err
	}
	return nil
}

// MyExecuteCommand TODO
func (e ExecuteSqlAtLocal) MyExecuteCommand(command string) (err error) {
	var stderrBuf bytes.Buffer
	// var errStdout, errStderr error
	logger.Info("The Command Is %s", mysqlcomm.ClearSensitiveInformation(command))
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Hour)
	defer cancel()
	// command = fmt.Sprintf("sleep 3 && %s", command)
	cmd := exec.CommandContext(ctx, "/bin/bash", "-c", command)

	// 启动指定命令
	if err = cmd.Start(); err != nil {
		logger.Error("start command failed:%s", err.Error())
		return
	}

	if ctx.Err() == context.DeadlineExceeded {
		errmsg := fmt.Sprintf("执行已超过1小时，初始化分区失败！")
		logger.Error(errmsg)
		return errors.New(errmsg)
	}

	// 会阻塞 直到命令执行完
	err = cmd.Wait()
	if err != nil {
		errStr := string(stderrBuf.Bytes())
		logger.Error("exec failed:%s,stderr: %s", err.Error(), errStr)
		return
	}

	return nil
}

// LinuxNameMax Linux 单段文件名长度上限（NAME_MAX）。
const LinuxNameMax = 255

// ErrLogTimestampPlaceholder MyExecuteSqlByMySQLClientOne 使用的时间戳占位（与 cst.TimeLayoutDir 等长）。
const ErrLogTimestampPlaceholder = "20060102150405"

// BuildMyExecuteErrFileBase 拼装 MyExecuteSqlByMySQLClientOne 的 err 文件名（不含目录）。
// 格式: {sqlfile}.{db}.{timestamp}.err
func BuildMyExecuteErrFileBase(sqlfile, db, timestamp string) string {
	return fmt.Sprintf("%s.%s.%s.err", path.Base(sqlfile), db, timestamp)
}

// CheckMyExecuteErrFileNameLen 校验 {sqlfile}.{db}.{timestamp}.err 不超过 NAME_MAX。
func CheckMyExecuteErrFileNameLen(sqlfile, db string) error {
	errBase := BuildMyExecuteErrFileBase(sqlfile, db, ErrLogTimestampPlaceholder)
	if len(errBase) > LinuxNameMax {
		return errors.Errorf(
			"err log 文件名过长:%s, 长度%d, 上限%d(拼装为 {sqlfile}.{db}.{timestamp}.err), sqlfile=%s db=%s, 请缩短库名或文件名",
			errBase, len(errBase), LinuxNameMax, path.Base(sqlfile), db,
		)
	}
	return nil
}

// MyExecuteSqlByMySQLClientOne 只输出错误到控制台，
func (e ExecuteSqlAtLocal) MyExecuteSqlByMySQLClientOne(sqlfile string, db string) (err error) {
	if err = e.requireWorkDir(); err != nil {
		return err
	}
	command := e.CreateLoadSQLCommand()
	command = command + " " + db + "<" + path.Join(e.WorkDir, sqlfile)
	e.ErrFile = path.Join(e.WorkDir, BuildMyExecuteErrFileBase(sqlfile, db, time.Now().Format(cst.TimeLayoutDir)))
	err = e.ExecuteCommandIgnoreStdo(command)
	if err != nil {
		return err
	}
	return nil
}

// ExecuteCommandIgnoreStdo 用于mysql数据迁移的的命令执行 只打印错误
func (e ExecuteSqlAtLocal) ExecuteCommandIgnoreStdo(command string) (err error) {
	var stderrBuf bytes.Buffer
	var errStderr error
	logger.Info("The Command Is %s", mysqlcomm.ClearSensitiveInformation(command))
	cmd := exec.Command("/bin/bash", "-c", command)
	stderrIn, _ := cmd.StderrPipe()

	// 写入error 文件
	ef, errO := os.OpenFile(e.ErrFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if errO != nil {
		logger.Error("打开错误日志失败! %s", errO.Error())
		return errors.Wrapf(errO, "打开错误日志失败: %s", e.ErrFile)
	}
	defer ef.Close()
	defer ef.Sync()
	// stdout := io.MultiWriter(os.Stdout)
	stderr := io.MultiWriter(os.Stderr, &stderrBuf, ef)

	if err = cmd.Start(); err != nil {
		logger.Error("start command failed:%s", err.Error())
		return
	}

	_, errStderr = io.Copy(stderr, stderrIn)

	// Start 成功后必须 Wait，避免 capture 失败时留下残留进程
	waitErr := cmd.Wait()
	if errStderr != nil {
		logger.Error("failed to capture stderr\n")
		return errors.Errorf(
			"failed to capture stderr: stderr=%v, wait=%v",
			errStderr, waitErr,
		)
	}
	if waitErr != nil {
		errStr := string(stderrBuf.Bytes())
		logger.Error("exec failed:%s,stderr: %s", waitErr.Error(), errStr)
		return waitErr
	}

	return nil
}
