/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// 下架MySQL实例
// 因为下架需要操作数据目录和日志目录
// 这个两个参数是从my.cnf里面读取的
// ** 一定要存在my.cnf ** 否则无法下架,如果my.cnf 丢失可以伪造一个my.cnf

package mysql

import (
	"fmt"
	"path"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/mitchellh/go-ps"
	"github.com/shirou/gopsutil/v3/process"
)

// UnInstallMySQLComp 卸载mysql
type UnInstallMySQLComp struct {
	GeneralParam *components.GeneralParam
	Params       *UnInstallMySQLParam
	runTimeCtx
	tools *tools.ToolSet
}

// UnInstallMySQLParam 参数
type UnInstallMySQLParam struct {
	Host  string `json:"host" validate:"required,ip" `
	Force bool   `json:"force"`                                // 是否强制下架mysqld
	Ports []int  `json:"ports"  validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口

}

// 运行是需要的必须参数,可以提前计算
type runTimeCtx struct {
	adminUser string
	adminPwd  string
	insMyObj  map[Port]*MyCnfObj
}

// MyCnfObj 配置
type MyCnfObj struct {
	MyCnfPath  string
	Datadir    string
	LogDir     string
	Socket     string
	IsShutdown bool // 标记卸载的实例是否已经是关闭/不能访问的状态
}

// Init 初始化 UnInstallMySQLRunTimeContext
// check my.cnf 配置，并加载配置
func (u *UnInstallMySQLComp) Init() (err error) {
	u.insMyObj = make(map[int]*MyCnfObj)
	for _, port := range u.Params.Ports {
		var socket string
		myfile := util.GetMyCnfFileName(port)
		if !cmutil.FileExists(myfile) {
			return fmt.Errorf("%s不存在", myfile)
		}
		f, err := util.LoadMyCnfForFile(myfile)
		if err != nil {
			logger.Error("加载%s配置失败%s", myfile, err)
			return err
		}
		if socket, err = f.GetMySQLSocket(); err != nil {
			return err
		}
		u.insMyObj[port] = &MyCnfObj{
			MyCnfPath:  myfile,
			Datadir:    "",
			LogDir:     "",
			Socket:     socket,
			IsShutdown: false, // 初始化给个默认值，后续判断实例是否正常才变更
		}
	}
	u.runTimeCtx.adminPwd = u.GeneralParam.RuntimeAccountParam.AdminPwd
	u.runTimeCtx.adminUser = u.GeneralParam.RuntimeAccountParam.AdminUser
	u.tools = tools.NewToolSetWithPickNoValidate(tools.ToolMysqlTableChecksum)
	return nil
}

// PreCheck  非强制下架时候需要做一些安全卸载检查
//
//	@receiver u
//	@return err
func (u *UnInstallMySQLComp) PreCheck() (err error) {
	for _, port := range u.Params.Ports {
		inst := native.InsObject{
			User:   u.adminUser,
			Pwd:    u.adminPwd,
			Socket: u.runTimeCtx.insMyObj[port].Socket,
		}
		if _, err := inst.ConnBySocket(); err != nil {
			logger.Warn("try connent this mysql instance [%p] failed:%s", port, err.Error())
			u.insMyObj[port].IsShutdown = true
		}
		if !u.Params.Force && !u.insMyObj[port].IsShutdown {
			// 非强制下架，且实例正常的情况下，需要判断实例是否有业务连接,
			// todo 这里重新去创建连接，如果检测实例状态和连接业务访问之间出现实例异常，则会触发bug，后续考虑怎么优化这点
			if err := inst.CheckInstanceConnIdle(u.GeneralParam.GetAllSysAccount(), time.Second*1); err != nil {
				logger.Warn("try connent this mysql instance [%p] failed:%s", port, err.Error())
				u.insMyObj[port].IsShutdown = true
			}
		}
		continue
	}
	return nil
}

// ShutDownMySQLD 关闭mysqld
func (u *UnInstallMySQLComp) ShutDownMySQLD() (err error) {
	for _, port := range u.Params.Ports {
		if u.Params.Force || u.insMyObj[port].IsShutdown {
			// 这里如果传入强制卸载，或者之前判断实例已经异常，则走强制关闭逻辑，否则走正常卸载过程
			err = computil.ShutdownMySQLParam{
				MySQLUser: u.adminUser,
				MySQLPwd:  u.adminPwd,
				Socket:    u.insMyObj[port].Socket,
			}.ForceShutDownMySQL()
			if err != nil {
				logger.Error("shutdown mysql instance %p failed:%s", port, err.Error())
				return err
			}
		} else {
			// 走正常mysql关闭命令流程
			err = computil.ShutdownMySQLParam{
				MySQLUser: u.adminUser,
				MySQLPwd:  u.adminPwd,
				Socket:    u.insMyObj[port].Socket,
			}.ShutdownMySQLBySocket()
			if err != nil {
				logger.Error("shutdown mysql instance %p failed:%s", port, err.Error())
				return err
			}
		}
	}
	return err
}

// ClearMachine 清理目录
//
//		@receiver u
//		@return err
//	 todo 删除备份程序配置， 删除数据校验程序的
func (u *UnInstallMySQLComp) ClearMachine() (err error) {
	for _, port := range u.Params.Ports {
		var (
			dataLog = path.Join(
				cst.DefaultMysqlLogRootPath,
				cst.DefaultMysqlLogBasePath,
				strconv.Itoa(port),
			) //  "/data/mysqllog/{port}"
			data1Log = path.Join(
				cst.AlterNativeMysqlLogRootPath,
				cst.DefaultMysqlLogBasePath,
				strconv.Itoa(port),
			) //  "/data1/mysqllog/{port}"
			dataPath = path.Join(
				cst.AlterNativeMysqlDataRootPath,
				cst.DefaultMysqlDataBasePath,
				strconv.Itoa(port),
			) //  "/data/mysqldata/{port}"
			data1Path = path.Join(
				cst.DefaultMysqlDataRootPath,
				cst.DefaultMysqlDataBasePath,
				strconv.Itoa(port),
			) //  "/data1/mysqldata/{port}"
			data1Bak = path.Join(
				cst.DefaultMysqlDataRootPath,
				cst.DefaultBackupBasePath,
			) //  "/data1/dbbak/"
			dataBak = path.Join(
				cst.AlterNativeMysqlDataRootPath,
				cst.DefaultBackupBasePath,
			) //  "/data/dbbak/"
			suffix     = fmt.Sprintf("_bak_%s", time.Now().Format(cst.TIMELAYOUTSEQ))
			dataLogBak = path.Join(
				cst.DefaultMysqlLogRootPath,
				fmt.Sprintf("%s_%d%s", cst.DefaultMysqlLogBasePath, port, suffix),
			) // "/data/mysqllog_{port}_bak__xxxx"
			data1LogBak = path.Join(
				cst.AlterNativeMysqlLogRootPath,
				fmt.Sprintf("%s_%d%s", cst.DefaultMysqlLogBasePath, port, suffix),
			) // "/data/mysqllog_{port}_bak__xxxx"

		)

		if cmutil.FileExists(dataLog) {
			cmd := fmt.Sprintf("mv %s %s;", dataLog, dataLogBak)
			logger.Info("backup command [%s]", cmd)
			output, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", cmd, err, output)
				return err
			}
		}
		if cmutil.FileExists(data1Log) {
			cmd := fmt.Sprintf("mv %s %s;", data1Log, data1LogBak)
			logger.Info("backup command [%s]", cmd)
			output, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", cmd, err, output)
				return err
			}
		}
		if cmutil.FileExists(dataPath) {
			var shellCMD string
			if !cmutil.FileExists(dataBak) {
				shellCMD += fmt.Sprintf("mkdir %s;", dataBak)
			}
			shellCMD += fmt.Sprintf(
				"mv %s %s_%d%s;",
				dataPath,
				path.Join(dataBak, cst.DefaultMysqlDataBasePath),
				port,
				suffix,
			)
			logger.Info("backup command [%s]", shellCMD)
			output, err := osutil.ExecShellCommand(false, shellCMD)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", shellCMD, err, output)
				return err
			}
		}
		if cmutil.FileExists(data1Path) {
			var shellCMD string
			if !cmutil.FileExists(data1Bak) {
				shellCMD += fmt.Sprintf("mkdir %s;", data1Bak)
			}
			shellCMD += fmt.Sprintf(
				"mv %s %s_%d%s;",
				data1Path,
				path.Join(data1Bak, cst.DefaultMysqlDataBasePath),
				port,
				suffix,
			)
			logger.Info("backup command [%s]", shellCMD)
			output, err := osutil.ExecShellCommand(false, shellCMD)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", shellCMD, err, output)
				return err
			}
		}
	}
	return nil
}

// KillDirtyProcess 清理系统残留的mysql 相关进程，下架的时候会检查，比如hang住的mysql client 进程
//
//	@receiver u
//	@return err
func (u *UnInstallMySQLComp) KillDirtyProcess() (err error) {
	dirtyProcessNames := []string{
		"mysql",
	}
	processes, err := ps.Processes()
	if err != nil {
		return fmt.Errorf("list processes failed, err:%s", err.Error())
	}
	msgs := make([]string, 0)
	for _, proc := range processes {
		processName := proc.Executable()
		if !cmutil.HasElem(processName, dirtyProcessNames) {
			continue
		}

		p, err := process.NewProcess(int32(proc.Pid()))
		if err != nil {
			msgs = append(msgs, fmt.Sprintf("process:%s, err:%s", processName, err.Error()))
			continue
		}
		if err := p.Terminate(); err != nil {
			msg := fmt.Sprintf("terminate process %s failed, err:%s", processName, err.Error())
			msgs = append(msgs, msg)
			continue
		}
		logger.Info("success terminate dirty process %s", processName)
	}
	if len(msgs) != 0 {
		return fmt.Errorf("failed kill %d processes, they are: %s", len(msgs), strings.Join(msgs, "\n"))
	}
	return nil
}
