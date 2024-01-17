/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"bytes"
	"encoding/json"
	"fmt"
	"html/template"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/rollback"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/components"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/sqlserver"

	"github.com/shirou/gopsutil/mem"
)

// InstallSqlServerComp TODO
type InstallSqlServerComp struct {
	GeneralParam           *components.GeneralParam `json:"general"`
	Params                 *InstallSqlServerParams  `json:"extend"`
	installSQLServerConfig `json:"-"`
	RollBackContext        rollback.RollBackObjects `json:"-"`
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int

// InstallSqlServerParams TODO
type InstallSqlServerParams struct {
	components.Medium
	Ports            []int           `json:"ports" validate:"required,gt=0,dive"`
	SQlServerVersion string          `json:"sqlserver_version"  validate:"required"`
	Charset          string          `json:"charset"  validate:"required"`
	Host             string          `json:"host" validate:"required,ip" `
	InstallKey       string          `json:"install_key" validate:"required" `
	BufferPercent    uint64          `json:"buffer_percent" validate:"required,gt=0,lt=100"`
	MaxRemainMemGB   uint64          `json:"max_remain_mem_gb" validate:"required,gt=0"`
	SQLServerConfigs json.RawMessage `json:"sqlserver_configs"  validate:"required" `
}

// RenderConfig TODO
type RenderConfig struct {
	InstanceID     string
	InstanceName   string
	InstallKey     string
	DataDir        string
	SqlSVCAccout   string
	SqlSVCPassWord string
	AgtSVCAccount  string
	AgtSVCPassWord string
	SAPwd          string
	Charset        string
}

// Cnf TODO
type Cnf struct {
	ConfFile  string
	MssqlConf json.RawMessage
}

type installSQLServerConfig struct {
	InstallDir     string
	DataRootPath   string
	BackupRootPath string
	CnfTpls        map[Port]*Cnf
	InsPorts       []Port
	RenderConfigs  map[Port]RenderConfig
	InsInitDirs    map[Port]InitDirs
}

// Example TODO
func (i *InstallSqlServerComp) Example() interface{} {
	comp := InstallSqlServerComp{
		Params: &InstallSqlServerParams{
			Medium: components.Medium{
				Pkg:    "SQL2008x64_SorceMedia.7z",
				PkgMd5: "xxx",
			},
			Host:             "1.1.1.1",
			SQlServerVersion: "SQL2008x64",
			Ports:            []int{48322, 48332},
			InstallKey:       "xxxx",
			BufferPercent:    75,
			MaxRemainMemGB:   32,
			SQLServerConfigs: []byte(`{
							"48322":{"xxx":"xxx"},
							"48332":{"xxx":"xxx"}
							}`),
		},
	}
	return comp
}

// InitDefaultParam 初始化一些安装时需要的变量
func (i *InstallSqlServerComp) InitDefaultParam() error {
	i.InstallDir = cst.INSTALL_SQL_DATA_DIR
	i.DataRootPath = filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_DATA_NAME)
	i.InsPorts = i.Params.Ports

	// 判断E盘是否存在，如果存在，设计backup目录在E盘上
	e := osutil.WINSFile{FileName: cst.BASE_BACKUP_PATH}
	if _, check := e.FileExists(); check {
		i.BackupRootPath = filepath.Join(cst.BASE_BACKUP_PATH, cst.MSSQL_BACKUP_NAME)
	} else {
		i.BackupRootPath = filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_BACKUP_NAME)
	}

	i.CnfTpls = make(map[int]*Cnf)

	// 反序列化sqlserver的配置
	var MssqlCnfs map[Port]json.RawMessage
	if err := json.Unmarshal([]byte(i.Params.SQLServerConfigs), &MssqlCnfs); err != nil {
		logger.Error("反序列化配置失败:%s", err.Error())
		return err
	}

	// 计算每个实例需要安装的配置信息
	for _, port := range i.InsPorts {
		var conf json.RawMessage
		var ok bool
		// confFile := fmt.Sprintf(
		// 	"%s\\%s\\%s_%d", cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME, cst.CONFIGURATION_FILE_NAME, port,
		// )
		confFile := filepath.Join(
			cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME, fmt.Sprintf("%s_%d", cst.CONFIGURATION_FILE_NAME, port),
		)
		if conf, ok = MssqlCnfs[port]; !ok {
			return fmt.Errorf("参数中没有%d的配置", port)
		}
		i.CnfTpls[port] = &Cnf{ConfFile: confFile, MssqlConf: conf}
	}
	// 计算需要替换的安装配置参数
	i.RenderConfigs = make(map[Port]RenderConfig)
	for _, port := range i.InsPorts {
		i.RenderConfigs[port] = RenderConfig{
			InstanceID:     osutil.GetInstallName(port),
			InstanceName:   osutil.GetInstallName(port),
			InstallKey:     i.Params.InstallKey,
			DataDir:        fmt.Sprintf("%s\\%s\\\\%d", cst.BASE_DATA_PATH, cst.MSSQL_DATA_NAME, port),
			SqlSVCAccout:   i.GeneralParam.RuntimeAccountParam.SQLServerUser,
			SqlSVCPassWord: i.GeneralParam.RuntimeAccountParam.SQLServerPwd,
			AgtSVCAccount:  i.GeneralParam.RuntimeAccountParam.SQLServerUser,
			AgtSVCPassWord: i.GeneralParam.RuntimeAccountParam.SQLServerPwd,
			SAPwd:          i.GeneralParam.RuntimeAccountParam.SAPwd,
			Charset:        i.Params.Charset,
		}
	}

	return nil
}

// CheckDataDir 检测数据目录是否存在
func (i *InstallSqlServerComp) CheckDataDir() error {
	dataDir := osutil.WINSFile{FileName: i.DataRootPath}
	err, check := dataDir.FileExists()
	if err != nil {
		return err
	}
	if !check {
		return fmt.Errorf("data dir [%s] not exists", i.DataRootPath)
	}
	return nil
}

// CheckMssqlProcess 判断本地是否部署mssql开头的服务进程
func (i *InstallSqlServerComp) CheckMssqlProcess() error {
	ret, err := osutil.StandardPowerShellCommand(
		"GET-SERVICE -NAME MSSQL* | " +
			"WHERE-OBJECT {$_.STATUS -EQ \"RUNNING\" -AND $_.NAME -NOTLIKE \"*#*\"} | " +
			"SELECT-OBJECT -PROPERTY NAME",
	)
	if err != nil {
		return err
	}
	if ret != "" {
		// 输出不为空则表示有部署进程
		return fmt.Errorf("there is a mssql process check [%s]", osutil.CleanExecOutput(ret))
	}
	return nil
}

// PreCheck 预检测，检测必要目录、进程、介质包的md5
func (i *InstallSqlServerComp) PreCheck() error {
	// 验证文件的md5值
	if err := i.Params.Medium.Check(); err != nil {
		logger.Error("md5 check failed %s", err.Error())
		return err
	}
	// 检测机器是否存在必要目录
	if err := i.CheckDataDir(); err != nil {
		logger.Error("check datadir failed %s", err.Error())
		return err
	}
	// 检测机器是否有启动mssql服务，如果有则退出，表示机器不属于干净机器
	if err := i.CheckMssqlProcess(); err != nil {
		logger.Error("check mssql process failed %s", err.Error())
		return err
	}

	return nil
}

// GenerateCnf 生成sqlserver安装配置
func (i *InstallSqlServerComp) GenerateCnf() error {
	for _, port := range i.InsPorts {
		// 模板配置渲染
		var rendered bytes.Buffer

		tmpl := template.Must(template.New("conf").Parse(string(i.CnfTpls[port].MssqlConf)))
		err := tmpl.Execute(&rendered, i.RenderConfigs[port])
		if err != nil {
			return err
		}
		// 生成对应配置文件
		if err := osutil.CreateInstallConf(
			rendered.Bytes(), i.CnfTpls[port].ConfFile, i.Params.SQlServerVersion); err != nil {
			return err
		}
	}
	return nil
}

// InitInstanceDirs 负责生成每个实例下的数据目录
// 因为安装SQLserver时候数据目录是不影响安装进度的，所以这里如果检测不存在，则做生成处理
func (i *InstallSqlServerComp) InitInstanceDirs() error {
	for _, port := range i.InsPorts {
		// dataDir := fmt.Sprintf("%s\\\\%d", i.DataRootPath, port)
		dataDir := filepath.Join(i.DataRootPath, strconv.Itoa(port))
		f := osutil.WINSFile{FileName: dataDir}
		if _, check := f.FileExists(); !check {
			// 不存在则创建
			logger.Info(fmt.Sprintf("data dir [%s] not exists, create", dataDir))
			if !f.Create(0777) {
				return fmt.Errorf("create dir [%s] failed", dataDir)
			}
		}
		// 目录归属于mssql账号
		if !f.SetChown(i.GeneralParam.RuntimeAccountParam.OSMssqlUser) {
			return fmt.Errorf("create dir [%s] failed", dataDir)
		}
		// 目录归属于sqlserver账号
		if !f.SetChown(i.GeneralParam.RuntimeAccountParam.SQLServerUser) {
			return fmt.Errorf("create dir [%s] failed", dataDir)
		}
	}
	return nil
}

// DecompressPkg TODO
// 解压安装文件,支持.7z 和 .zip的解压方式
func (i *InstallSqlServerComp) DecompressPkg() error {
	switch {
	case strings.Contains(i.Params.Pkg, ".7z"):
		// 安装包属于7z文件包，选择7z的解压方式
		_, err := osutil.StandardPowerShellCommand(
			fmt.Sprintf(" & '%s' x -y %s -o%s  ", cst.SQLSERVER_UNZIP_TOOL, i.Params.GetAbsolutePath(), cst.BASE_DATA_PATH),
		)
		if err != nil {
			return err
		}
	case strings.Contains(i.Params.Pkg, ".zip"):
		// 安装包属于zip文件包，选择zip的解压方式
		_, err := osutil.StandardPowerShellCommand(
			fmt.Sprintf("Expand-Archive -Path %s -DestinationPath %s", i.Params.GetAbsolutePath(), cst.BASE_DATA_PATH),
		)
		if err != nil {
			return err
		}
	default:
		return fmt.Errorf("[%s] Currently only supports decompression of .7z files and .zip files. check", i.Params.Pkg)
	}

	logger.Info("decompress mysql pkg successfully")
	return nil
}

// SqlServerStartup TODO
// 遍历端口，启动实例
func (i *InstallSqlServerComp) SqlServerStartup() error {
	// 导入相关模块
	cmds := []string{
		"IMPORT-MODULE SERVERMANAGER",
		"ADD-WINDOWSFEATURE TELNET-CLIENT",
	}
	if _, err := osutil.StandardPowerShellCommands(cmds); err != nil {
		return err
	}
	// 遍历端口安装启动实例
	for _, port := range i.InsPorts {
		cmds := []string{
			fmt.Sprintf("Remove-Item -Path '%s' -Force", cst.REBOOTREQUIRED_KEY),
			fmt.Sprintf("Remove-ItemProperty -Path '%s' -Name PendingFileRenameOperations' -Force", cst.SESSION_MANAGER_KEY),
		}
		osutil.StandardPowerShellCommands(cmds)

		// 等到3秒，等注册表信息足够删除
		time.Sleep(3 * time.Second)

		// 执行安装
		result, err := osutil.StandardPowerShellCommand(
			fmt.Sprintf(
				"& %s /ConfigurationFile=%s",
				filepath.Join(cst.BASE_DATA_PATH, osutil.GetInstallPackageName(i.Params.Medium.Pkg), "setup.exe"),
				i.CnfTpls[port].ConfFile,
			),
		)
		if err != nil {
			i.DeleteConfs()
			logger.Error("setup failed: %s", result)
			return err
		}
		logger.Info("installing sqlserver instance [%d] successfully", port)
	}
	i.DeleteConfs()
	return nil
}

// DeleteConfs 删除所有实例配置安装配置, 无论是安装失败或者成功
func (i *InstallSqlServerComp) DeleteConfs() error {
	var cmds []string
	for _, port := range i.InsPorts {
		cmds = append(cmds, fmt.Sprintf("REMOVE-ITEM %s", i.CnfTpls[port].ConfFile))
	}
	if _, err := osutil.StandardPowerShellCommands(cmds); err != nil {
		return err
	}
	return nil
}

// InitConfigs 成功安装之后初始化配置
func (i *InstallSqlServerComp) InitConfigs() error {
	logger.Info("start exec init_sqlserver ...")
	data, err := staticembed.InitSqlServer.ReadFile(staticembed.InitSqlServerFileName)
	if err != nil {
		logger.Error("read init_sqlserver script failed %s", err.Error())
		return err
	}
	// tmpScriptName := fmt.Sprintf("%s\\%s\\init_sqlserver.ps1", cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME)
	tmpScriptName := filepath.Join(cst.BASE_DATA_PATH, cst.BK_PKG_INSTALL_NAME, "init_sqlserver.ps1")
	if err = os.WriteFile(tmpScriptName, data, 0755); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	var InstanceNames []string
	var HADREnabled int = 0
	var SSMSEnabled int = 0
	for _, port := range i.InsPorts {
		InstanceNames = append(InstanceNames, osutil.GetInstallName(port))
	}
	num, err := osutil.GetVersionYears(i.Params.SQlServerVersion)
	if err != nil {
		return err
	}
	if num >= 2017 {
		// 版本大于2017，安装allway-on集群模块
		HADREnabled = 1
	}
	if num >= 2016 {
		// 版本大于2016，需要安装smss18版本
		SSMSEnabled = 1
	}
	cmd := fmt.Sprintf("& %s %s %s %s %d %d",
		tmpScriptName,
		i.Params.Host,
		osutil.GetInstallPackageName(i.Params.Medium.Pkg),
		strings.Join(InstanceNames, ","),
		HADREnabled,
		SSMSEnabled,
	)

	if _, err := osutil.StandardPowerShellCommand(cmd); err != nil {
		logger.Error("exec init script failed %s", err.Error())
		return err
	}
	// 执行完成后删除文件,删除失败不退出
	remoteCmd := fmt.Sprintf("REMOVE-ITEM %s", tmpScriptName)
	if _, err := osutil.StandardPowerShellCommand(remoteCmd); err != nil {
		logger.Warn("delete init-script failed %s", err.Error())
	}
	return nil
}

// InitDB TODO
// 按照实例维度初始化实例DB
func (i *InstallSqlServerComp) InitDB() error {
	// 把初始化sql脚本加载到本地d:
	var files []string
	var err error
	if files, err = WriteInitSQLFile(); err != nil {
		return err
	}
	for _, port := range i.InsPorts {
		if err := sqlserver.ExecLocalSQLFile(i.Params.SQlServerVersion, "master", 0, files, port); err != nil {
			return err
		}
	}
	// 执行完成后删除文件,删除失败不退出
	for _, file := range files {
		remoteCmd := fmt.Sprintf("REMOVE-ITEM %s", file)
		if _, err := osutil.StandardPowerShellCommand(remoteCmd); err != nil {
			logger.Warn("delete [%s] failed %s", file, err.Error())
		}
	}

	return nil
}

// InitInstanceBuffer TODO
// 计算每个实例的内存分配
func (i *InstallSqlServerComp) InitInstanceBuffer() error {

	// 获取系统物理内存
	mem, err := mem.VirtualMemory()
	if err != nil {
		return err
	}
	// 计算每个实例分配到内存
	var secondUsedMem float32 = 0
	usedMem := float32(mem.Total) * (float32(i.Params.BufferPercent) / 100)
	if usedMem > float32(i.Params.MaxRemainMemGB*1024*1024*1024) {
		secondUsedMem = usedMem - float32(i.Params.MaxRemainMemGB*1024*1024*1024)
	}
	instMemMB := (usedMem + secondUsedMem) / float32(len(i.InsPorts)) / 1024 / 1024
	logger.Info("%d", int(instMemMB))

	cmds := []string{
		"EXEC SP_CONFIGURE 'SHOW ADVANCED OPTIONS',1;",
		"RECONFIGURE;",
		fmt.Sprintf("EXEC SP_CONFIGURE N'MIN SERVER MEMORY (MB)', N'%d';", int(instMemMB)),
		fmt.Sprintf("EXEC SP_CONFIGURE N'MAX SERVER MEMORY (MB)', N'%d';", int(instMemMB)),
		"RECONFIGURE;",
		"EXEC SP_CONFIGURE 'SHOW ADVANCED OPTIONS',0;",
		"RECONFIGURE;",
	}
	// 内存分配加载到实例上
	for _, port := range i.InsPorts {
		var dbWork *sqlserver.DbWorker
		if dbWork, err = sqlserver.NewDbWorker(
			i.GeneralParam.RuntimeAccountParam.SAUser,
			i.GeneralParam.RuntimeAccountParam.SAPwd,
			i.Params.Host,
			port,
		); err != nil {
			logger.Error("connenct by %s failed,err:%s", port, err.Error())
			return err
		}
		// 到最后回收db连接
		defer dbWork.Stop()

		if _, err := dbWork.ExecMore(cmds); err != nil {
			logger.Error("exec SERVER MEMORY failed %v", err)
			return err
		}

	}

	return nil
}

// CreateExporterConf 创建exporter文件，每个端口有一份
func (i *InstallSqlServerComp) CreateExporterConf() error {
	for _, port := range i.InsPorts {
		if err := osutil.CreateExporterConf(
			filepath.Join(cst.BASE_DATA_PATH, cst.MSSQL_EXPOTER_NAME, fmt.Sprintf("exporter_%d.conf", port)),
			"localhost",
			port,
			i.GeneralParam.RuntimeAccountParam.MssqlExporterUser,
			i.GeneralParam.RuntimeAccountParam.MssqlExporterPwd,
		); err != nil {
			return err
		}
	}
	return nil
}

// WriteInitSQLFile TODO
// 把初始化的sql文件写入到本地
func WriteInitSQLFile() ([]string, error) {
	var dealFiles []string
	sqls := []string{
		staticembed.MonitorFileName,
		staticembed.BackupFileName,
		staticembed.AutoSwitchFileName,
		staticembed.SqlSettingFileName,
	}

	for _, sqlFile := range sqls {
		data, err := staticembed.SQLScript.ReadFile(sqlFile)
		if err != nil {
			logger.Error("read sql script failed %s", err.Error())
			return nil, err
		}
		// tmpScriptName := fmt.Sprintf("%s\\%s", cst.BASE_DATA_PATH, sqlFile)
		// 添加 UTF-8 BOM 字节序列
		data = append([]byte{0xEF, 0xBB, 0xBF}, data...)

		tmpScriptName := filepath.Join(cst.BASE_DATA_PATH, sqlFile)
		if err = os.WriteFile(tmpScriptName, data, 0755); err != nil {
			logger.Error("write sql script failed %s", err.Error())
			return nil, err
		}
		dealFiles = append(dealFiles, tmpScriptName)
	}
	return dealFiles, nil
}
