/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package sysinit TODO
package sysinit

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"

	"github.com/shirou/gopsutil/mem"
	"golang.org/x/crypto/ssh"
)

// SysInitParam TODO
type SysInitParam struct {
	SSHPort       int    `json:"ssh_port" validate:"required,gt=0"`
	OSMssqlUser   string `json:"mssql_user"`
	OSMssqlPwd    string `json:"mssql_pwd"`
	SQLServerUser string `json:"sqlserver_user"`
	SQLServerPwd  string `json:"sqlserver_pwd"`
}

/*
	执行系统初始化脚本 原来的sysinit.sh
	创建mssql账户等操作
*/

// PreCheck 初始化的预检测
func (s *SysInitParam) PreCheck() error {
	// 判断机器是否数据盘D盘，如果没有存在则异常
	d := osutil.WINSFile{FileName: cst.BASE_DATA_PATH}
	err, check := d.FileExists()
	if err != nil {
		return err
	}
	if !check {
		return fmt.Errorf("data dir [%s] not exists", cst.BASE_DATA_PATH)
	}
	logger.Info("data dir [%s] exists, pass", cst.BASE_DATA_PATH)

	// 检查SQLserver的安装目录是否存在, 如果存在证明机器部署SQLserver实例
	dirGroup := []string{
		cst.INSTALL_SHARED_DIR,
		cst.INSTALL_SHARED_WOW_DIR,
		cst.INSTALL_SQL_DATA_DIR,
	}
	isErr := false
	for _, dir := range dirGroup {
		d := osutil.WINSFile{FileName: dir}
		err, check := d.FileExists()
		if err != nil {
			logger.Error(err.Error())
			isErr = true
		}
		if check {
			logger.Error("dir [%s] exists, check!", dir)
			isErr = true
		}
		logger.Info("The dir [%s] not exists , pass", dir)
	}
	if isErr {
		return fmt.Errorf("percheck failed")
	}

	// 检测机器内存容量，低于2GB不允许安装SqlServer
	mem, err := mem.VirtualMemory()
	if err != nil {
		return err
	}
	if mem.Total < 2*1024*1024*1024 {
		return fmt.Errorf("system  memory does not exceed 2GB")
	}
	logger.Info("System memory exceed 2GB, pass")
	return nil
}

// CreateSysUser 创建需要的系统账号
func (s *SysInitParam) CreateSysUser() error {
	logger.Info("start exec createSysUser ...")
	// 创建mssql账号
	mssql := osutil.WINSOSUser{
		User:    s.OSMssqlUser,
		Pass:    s.OSMssqlPwd,
		Comment: "SQL SERVER ACCOUNT",
	}
	if mssql.UserExists() {
		if err := mssql.SetUerPass(); err != nil {
			return err
		}
	} else {
		if err := mssql.CreateUser(false); err != nil {
			return err
		}
	}
	if err := mssql.AddGroupMember("Administrators"); err != nil {
		return err
	}
	if err := mssql.RemoveGroupMember("Users"); err != nil {
		return err
	}
	logger.Info("create system-user [%s] successfully ", s.OSMssqlUser)

	// 创建sqlserver账号
	sqlserver := osutil.WINSOSUser{
		User:    s.SQLServerUser,
		Pass:    s.SQLServerPwd,
		Comment: "SQL SERVER SERVICE ACCOUNT",
	}
	if sqlserver.UserExists() {
		if err := sqlserver.SetUerPass(); err != nil {
			return err
		}
	} else {
		if err := sqlserver.CreateUser(false); err != nil {
			return err
		}
	}
	if err := sqlserver.AddGroupMember("Administrators"); err != nil {
		return err
	}
	if err := sqlserver.RemoveGroupMember("Users"); err != nil {
		return err
	}
	logger.Info("create system-user [%s] successfully ", s.SQLServerUser)
	// 创建backupman账号
	backupman := osutil.WINSOSUser{
		User:    "backupman",
		Pass:    osutil.GenerateRandomString(12),
		Comment: "BACKUP ACCOUNT",
	}
	if backupman.UserExists() {
		logger.Info("backupman is exist,skip")
		return nil
	} else {
		if err := backupman.CreateUser(false); err != nil {
			return err
		}
	}

	return nil
}

// CreateSysDir TODO
func (s *SysInitParam) CreateSysDir() error {
	logger.Info("start exec createSysDir ...")
	createDir := []string{
		filepath.Join(cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_DATA_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.IEOD_FILE_BACKUP),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_EXPOTER_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_DBHA_NAME),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME, "full"),
		filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME, "log"),
	}
	// 判断机器是否存在E盘，如果有在创建必要目录
	e := osutil.WINSFile{FileName: cst.BASE_BACKUP_PATH}
	err, check := e.FileExists()
	if err != nil {
		logger.Warn(err.Error())
	}
	if check {
		// 添加E盘必须创建的目录
		createDir = append(createDir, filepath.Join(cst.BASE_DATA_PATH, cst.BASE_BACKUP_PATH))
		createDir = append(createDir, filepath.Join(cst.BASE_DATA_PATH, cst.BASE_BACKUP_PATH, "full"))
		createDir = append(createDir, filepath.Join(cst.BASE_DATA_PATH, cst.BASE_BACKUP_PATH, "log"))
	}

	// 循环创建目录
	for _, dirName := range createDir {
		dir := osutil.WINSFile{FileName: dirName}
		err, check := dir.FileExists()
		if check && err == nil {
			// 表示目录在系统存在，先跳过
			continue
		}
		if err != nil {
			// 表示检查目录是否存在出现异常，报错
			return err
		}
		// 创建目录
		if !dir.Create(0777) {
			return fmt.Errorf("create dir [%s] failed", dirName)
		}
		logger.Info("create system-dir [%s] successfully", dirName)
	}
	// 增加一个cygwin目录，目的让备份系统可以顺利下载文件
	cygwinHomeDir := osutil.WINSFile{FileName: cst.CYGWIN_MSSQL_PATH}
	_, cygwinHomecheck := cygwinHomeDir.FileExists()
	if cygwinHomecheck {
		// 表示目录在系统存在，跳过
		return nil
	}
	// 创建mssql目录，不捕捉日志
	cygwinHomeDir.Create(0777)
	return nil
}

// SysInitMachine TODO
func (s *SysInitParam) SysInitMachine() error {
	logger.Info("start exec sysinit ...")
	data, err := staticembed.SysInitScript.ReadFile(staticembed.SysInitScriptFileName)
	if err != nil {
		logger.Error("read sysinit script failed %s", err.Error())
		return err
	}
	// tmpScriptName := fmt.Sprintf("%s\\%s\\sysinit.ps1", cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME)
	tmpScriptName := filepath.Join(cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME, "sysinit.ps1")
	if err = os.WriteFile(tmpScriptName, data, 0755); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	_, err = osutil.StandardPowerShellCommand(
		fmt.Sprintf("& %s ", tmpScriptName),
	)
	if err != nil {
		return err
	}
	if err := os.RemoveAll(tmpScriptName); err != nil {
		logger.Warn("delete sysinit-file failed :[%s]", err.Error())
	} else {
		logger.Info("delete sysinit-file success")
	}
	return nil
}

// CheckSSHForLocal 本地模拟ssh连接检测是否正常，模拟dbha做一次ssh校验
func (s *SysInitParam) CheckSSHForLocal() error {
	host, err := osutil.StandardPowerShellCommand(
		`(Get-NetIPAddress -InterfaceAlias "Ethernet" -AddressFamily IPv4).IPAddress`,
	)
	if err != nil {
		return err
	}
	checkStr := fmt.Sprintf("echo 1 > %s", fmt.Sprintf("%s\\\\%s\\\\%s", cst.BASE_DATA_PATH, cst.MSSQL_DBHA_NAME, "test"))
	conf := &ssh.ClientConfig{
		Timeout:         time.Second * time.Duration(10), // ssh 连接time out 时间10秒钟, 如果ssh验证错误 会在一秒内返回
		User:            s.OSMssqlUser,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // 这个可以， 但是不够安全
		Config: ssh.Config{
			Ciphers: []string{"arcfour"}, // 指定加密算法，目前利用sygwin联调
		},
	}
	conf.Auth = []ssh.AuthMethod{ssh.Password(s.OSMssqlPwd)}
	addr := fmt.Sprintf("%s:%d", strings.ReplaceAll(strings.ReplaceAll(host, "\r", ""), "\n", ""), s.SSHPort)
	logger.Info(addr)
	sshClient, err := ssh.Dial("tcp", addr, conf)
	if err != nil {
		panic(err)
	}
	defer sshClient.Close()

	session, err := sshClient.NewSession()
	if err != nil {
		return err
	}
	defer session.Close()

	_, err = session.CombinedOutput(checkStr)
	if err != nil {
		return err
	}
	logger.Info("ssh check successfully")
	return nil
}
