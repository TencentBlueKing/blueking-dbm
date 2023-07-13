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
	"database/sql"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
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
			mysqlclient, forceStr, e.User, passwd, e.Host, e.Port, e.Charset,
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
		if err = e.ExcuteSqlByMySQLClientOne(sqlfile, db); err != nil {
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
func (e ExecuteSqlAtLocal) ExcuteSqlByMySQLClientOne(sqlfile string, db string) (err error) {
	command := e.CreateLoadSQLCommand()
	command = command + " " + db + "<" + path.Join(e.WorkDir, sqlfile)
	e.ErrFile = path.Join(e.WorkDir, fmt.Sprintf("%s.%s.%s.err", sqlfile, db, time.Now().Format(cst.TimeLayoutDir)))
	err = e.ExcuteCommand(command)
	if err != nil {
		return err
	}
	return nil
}

// ExcuteCommand TODO
func (e ExecuteSqlAtLocal) ExcuteCommand(command string) (err error) {
	var errStdout, errStderr error
	logger.Info("The Command Is %s", ClearSensitiveInformation(command))
	cmd := exec.Command("/bin/bash", "-c", command)
	stdoutIn, _ := cmd.StdoutPipe()
	stderrIn, _ := cmd.StderrPipe()
	stdout := osutil.NewCapturingPassThroughWriter(os.Stdout)
	stderr := osutil.NewCapturingPassThroughWriter(os.Stderr)
	defer func() {
		// 写入error 文件
		ef, errO := os.OpenFile(e.ErrFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
		if errO != nil {
			logger.Warn("打开日志时失败! %s", errO.Error())
			return
		}
		defer ef.Close()
		_, errW := ef.Write(stderr.Bytes())
		if errW != nil {
			logger.Warn("写错误日志时失败! %s", err.Error())
		}
	}()
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

	_, errStderr = io.Copy(stderr, stderrIn)
	wg.Wait()

	if errStdout != nil || errStderr != nil {
		logger.Error("failed to capture stdout or stderr\n")
		return
	}

	if err = cmd.Wait(); err != nil {
		errStr := string(stderr.Bytes())
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
	logger.Info("The partitionsql is %s", ClearSensitiveInformation(partitionsql))
	err = util.Retry(
		util.RetryConfig{Times: 2, DelayTime: 2 * time.Second}, func() error {
			_, err = dbw.Exec(partitionsql)
			return err
		},
	)
	if err != nil {
		logger.Error("分区执行失败！%s", err)
		lock.Lock()
		errFile := path.Join(e.WorkDir, e.ErrFile)
		ef, errO := os.OpenFile(errFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
		defer lock.Unlock()
		defer ef.Close()
		if errO != nil {
			logger.Warn("打开日志时失败! %s", errO.Error())
			return
		}
		if err != nil {
			_, errW := ef.Write([]byte(fmt.Sprintf("%s\n", err.Error())))
			if errW != nil {
				logger.Warn("写错误日志时失败! %s", err.Error())
			}
		}
		return err
	}
	return nil
}

// ExcuteInitPartition TODO
func (e ExecuteSqlAtLocal) ExcuteInitPartition(command string) (err error) {
	e.ErrFile = path.Join(e.WorkDir, e.ErrFile)
	err = e.ExcuteCommand(command)
	if err != nil {
		return err
	}
	return nil
}
