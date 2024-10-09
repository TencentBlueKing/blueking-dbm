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
)

// ExecuteSqlAtLocal TODO
type ExecuteSqlAtLocal struct {
	MySQLBinPath     string
	WorkDir          string `json:"workdir"`
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

// ExcuteSqlByMySQLClient TODO
func (e ExecuteSqlAtLocal) ExcuteSqlByMySQLClient(sqlfile string, targetdbs []string) (err error) {
	for _, db := range targetdbs {
		if err = e.ExcuteSqlByMySQLClientOne(sqlfile, db, true); err != nil {
			return err
		}
	}
	return nil
}

func (e ExecuteSqlAtLocal) ExcuteSqlByMySQLClientWithOutReport(sqlfile string, targetdbs []string) (err error) {
	for _, db := range targetdbs {
		if err = e.ExcuteSqlByMySQLClientOne(sqlfile, db, false); err != nil {
			return err
		}
	}
	return nil
}

// ExcuteSqlByMySQLClientOne 使用本地mysqlclient 去执行sql
//
//	@receiver e
//	@receiver sqlfile
//	@receiver targetdbs
//	@return err
func (e ExecuteSqlAtLocal) ExcuteSqlByMySQLClientOne(sqlfile string, db string, report bool) (err error) {
	command := e.CreateLoadSQLCommand()
	command = command + " " + db + "<" + path.Join(e.WorkDir, sqlfile)
	e.ErrFile = path.Join(e.WorkDir, fmt.Sprintf("%s.%s.err", sqlfile, db)) // 删除原有的时间戳方便调用方拼接
	err = e.ExcuteCommand(command, report)
	if err != nil {
		return err
	}
	return nil
}

// ExcuteCommand TODO
func (e ExecuteSqlAtLocal) ExcuteCommand(command string, report bool) (err error) {
	var stderrBuf bytes.Buffer
	var errStdout, errStderr error
	logger.Info("The Command Is %s", mysqlcomm.ClearSensitiveInformation(command))
	cmd := exec.Command("/bin/bash", "-c", command)
	stdoutIn, _ := cmd.StdoutPipe()
	stderrIn, _ := cmd.StderrPipe()

	// 写入error 文件
	ef, errO := os.OpenFile(e.ErrFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if errO != nil {
		logger.Warn("打开日志时失败! %s", errO.Error())
		return
	}
	defer ef.Close()
	defer ef.Sync()
	// 标准输出复制一份到错误文件中
	stdout := io.MultiWriter(os.Stdout)
	//stdout := io.MultiWriter(os.Stdout, ef)
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

	if errStdout != nil || errStderr != nil {
		logger.Error("failed to capture stdout or stderr\n")
		return
	}

	if err = cmd.Wait(); err != nil {
		errStr := string(stderrBuf.Bytes())
		logger.Error("exec failed:%s,stderr: %s", err.Error(), errStr)
		return
	}

	return nil
}

// ExcutePartitionByMySQLClient TODO
func (e ExecuteSqlAtLocal) ExcutePartitionByMySQLClient(
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

// ExcuteInitPartition TODO
func (e ExecuteSqlAtLocal) ExcuteInitPartition(command string) (err error) {
	// e.ErrFile = path.Join(e.WorkDir, e.ErrFile)
	err = e.MyExcuteCommand(command)
	if err != nil {
		return err
	}
	return nil
}

// MyExcuteCommand TODO
func (e ExecuteSqlAtLocal) MyExcuteCommand(command string) (err error) {
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

// MyExcuteSqlByMySQLClientOne 只输出错误到控制台，
func (e ExecuteSqlAtLocal) MyExcuteSqlByMySQLClientOne(sqlfile string, db string) (err error) {
	command := e.CreateLoadSQLCommand()
	command = command + " " + db + "<" + path.Join(e.WorkDir, sqlfile)
	e.ErrFile = path.Join(e.WorkDir, fmt.Sprintf("%s.%s.%s.err", sqlfile, db, time.Now().Format(cst.TimeLayoutDir)))
	err = e.ExcuteCommandIgnoreStdo(command)
	if err != nil {
		return err
	}
	return nil
}

// ExcuteCommandIgnoreStdo 用于mysql数据迁移的的命令执行 只打印错误
func (e ExecuteSqlAtLocal) ExcuteCommandIgnoreStdo(command string) (err error) {
	var stderrBuf bytes.Buffer
	var errStdout, errStderr error
	logger.Info("The Command Is %s", mysqlcomm.ClearSensitiveInformation(command))
	cmd := exec.Command("/bin/bash", "-c", command)
	// stdoutIn, _ := cmd.StdoutPipe()
	stderrIn, _ := cmd.StderrPipe()

	// 写入error 文件
	ef, errO := os.OpenFile(e.ErrFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if errO != nil {
		logger.Warn("打开日志时失败! %s", errO.Error())
		return
	}
	defer ef.Close()
	defer ef.Sync()
	// stdout := io.MultiWriter(os.Stdout)
	stderr := io.MultiWriter(os.Stderr, &stderrBuf, ef)

	if err = cmd.Start(); err != nil {
		logger.Error("start command failed:%s", err.Error())
		return
	}

	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		// _, errStdout = io.Copy(stdout, stdoutIn)
		wg.Done()
	}()

	_, errStderr = io.Copy(stderr, stderrIn)
	wg.Wait()

	if errStdout != nil || errStderr != nil {
		logger.Error("failed to capture stdout or stderr\n")
		return
	}

	if err = cmd.Wait(); err != nil {
		errStr := string(stderrBuf.Bytes())
		logger.Error("exec failed:%s,stderr: %s", err.Error(), errStr)
		return
	}

	return nil
}
