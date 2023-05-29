/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package mysql_proxy TODO
/*
 * @Description: 安装 MySQL Proxy
 */
package mysql_proxy

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/proxyutil"
)

// InstallMySQLProxyComp TODO
type InstallMySQLProxyComp struct {
	GeneralParam            *components.GeneralParam
	Params                  *InstallMySQLProxyParam
	InstallMySQLProxyConfig // 运行时初始化配置
}

// InstallMySQLProxyParam TODO
// payload param
type InstallMySQLProxyParam struct {
	components.Medium
	ProxyConfigs json.RawMessage `json:"proxy_configs"`
	Host         string          `json:"host"  validate:"required,ip"`
	Ports        []int           `json:"ports" validate:"required,gt=0,dive"`
}

// InitDirs 别名
type InitDirs = []string

// InitFiles TODO
type InitFiles = []string

// Port TODO
type Port = int

// InstallMySQLProxyConfig TODO
type InstallMySQLProxyConfig struct {
	UserLocal         string
	Version           string
	ProxyInstallDir   string
	ProxyDataDir      string
	ProxyBaseDir      string
	ProxyAdminPortInc int
	ProxyAdminUser    string
	ProxyAdminPwd     string
	InsPorts          []Port
	InsReplaceConfigs map[Port]proxyutil.ReplaceProxyConfigs
	InsInitDirs       map[Port]InitDirs  // 需要初始化创建的目录
	InsInitFile       map[Port]InitFiles // 需要初始化创建的文件
	Checkfunc         []func() error
}

// Init TODO
/**
 * @description: 计算proxy挂载点,获取需要替换的配置项，初始化端口，目录等
 * @return {*}
 */
func (i *InstallMySQLProxyComp) Init() (err error) {
	var mountpoint string
	i.UserLocal = cst.UsrLocal
	i.ProxyInstallDir = cst.ProxyInstallPath
	i.ProxyDataDir = cst.DefaultProxyDataRootPath
	i.ProxyAdminPortInc = cst.ProxyAdminPortInc
	i.ProxyAdminUser = i.GeneralParam.RuntimeAccountParam.ProxyAdminUser
	i.ProxyAdminPwd = i.GeneralParam.RuntimeAccountParam.ProxyAdminPwd
	// 数据目录优先放在 /data1 盘下
	if mountpoint, err = osutil.FindFirstMountPointProxy(
		cst.DefaultProxyDataRootPath,
		cst.AlterNativeProxyDataRootPath,
	); err != nil {
		logger.Error("not found mount point /data1")
		return err
	}
	i.ProxyDataDir = mountpoint
	i.ProxyBaseDir = path.Join(mountpoint, cst.DefaultProxyLogBasePath)
	// 计算获取需要安装的ports
	if len(i.Params.Ports) == 0 {
		return fmt.Errorf("param Ports[len:%d] may be mistake", len(i.Params.Ports))
	}
	i.InsPorts = i.Params.Ports
	if err = i.calculateRepalceConfigs(); err != nil {
		logger.Error("计算替换配置失败: %s", err.Error())
		return err
	}
	return
}

// PreCheck TODO
/**
 * @description: 预检查：
 * 				- 检查是否存在安装proxy的路径
 *				- 检查是否存在proxy processs
 * 				- 检查安装包是否存在，如果存在检查md5是否正确
 * 				-
 * @return {*}
 */
func (i *InstallMySQLProxyComp) PreCheck() (err error) {
	// 判断 /usr/local/mysql-proxy 目录是否已经存在,如果存在则删除掉
	// if _, err := os.Stat(i.ProxyInstallDir); !os.IsNotExist(err) {
	if cmutil.FileExists(i.ProxyInstallDir) {
		if _, err = osutil.ExecShellCommand(false, "rm -r "+i.ProxyInstallDir); err != nil {
			logger.Error("rm -r %s error:%s", i.ProxyInstallDir, err.Error())
			return err
		}
	}
	// 校验介质
	if err = i.Params.Medium.Check(); err != nil {
		return err
	}

	if err := i.checkRunningProcess(); err != nil {
		logger.Error("checkRunningProcess %s", err.Error())
		return err
	}
	if err := i.checkDirs(); err != nil {
		logger.Error("checkDirs %s", err.Error())
		return err
	}
	return nil
}

// checkRunningProcess TODO
/**
 * @description:  检查是否mysql-proxy 进程存在
 * @return {*}
 */
func (i *InstallMySQLProxyComp) checkRunningProcess() (err error) {
	// 正在运行的 proxy 机器是不能安装 proxy 的吧。
	proxyNumStr, err := osutil.ExecShellCommand(false, "ps -efwww|grep -w mysql-proxy|grep -v grep|wc -l")
	if err != nil {
		return fmt.Errorf("error occurs while getting number of mysql-proxy.[%w]", err)
	}
	proxyNum, err := strconv.Atoi(strings.Replace(proxyNumStr, "\n", "", -1))
	if err != nil {
		logger.Error("= strconv.Atoi %s failed,err:%s", proxyNumStr, err.Error())
	}
	if proxyNum > 0 {
		return fmt.Errorf("already have %d running  proxy process ", proxyNum)
	}
	return
}

// checkDirs TODO
/**
 * @description: 检查相关proxy目录是否已经存在
 * @return {*}
 */
func (i *InstallMySQLProxyComp) checkDirs() error {
	for _, port := range i.InsPorts {
		for _, dir := range i.InsInitDirs[port] {
			if cmutil.FileExists(dir) {
				return fmt.Errorf("%s already exist", dir)
			}
		}
	}
	return nil
}

// GenerateProxycnf TODO
/**
 * @description: 生成proxy.cnf
 * @return {*}
 */
func (i *InstallMySQLProxyComp) GenerateProxycnf() (err error) {
	// 1. 根据参数反序列化配置
	var tmplConfigs proxyutil.ProxyCnfObject
	var tmplFileName = "proxy.cnf.tpl"
	var nf *util.CnfFile
	logger.Info("proxy Configs: %s", i.Params.ProxyConfigs)
	if err = json.Unmarshal(i.Params.ProxyConfigs, &tmplConfigs); err != nil {
		logger.Error("反序列化配置失败:%s", err.Error())
		return err
	}
	if nf, err = tmplConfigs.NewProxyCnfObject(tmplFileName); err != nil {
		logger.Error("渲染模版配置文件失败:%s", err.Error())
		return err
	}
	for _, port := range i.InsPorts {
		nf.FileName = util.GetProxyCnfName(port)
		logger.Info("will replace config: %v", i.InsReplaceConfigs[port])
		if err = proxyutil.ReplaceProxyConfigsObjects(nf, i.InsReplaceConfigs[port]); err != nil {
			logger.Error("替换参数失败%s", err.Error())
			return err
		}
		if err = nf.SafeSaveFile(true); err != nil {
			logger.Error("保存配置文件失败", err.Error())
			return err
		}
		if _, err = osutil.ExecShellCommand(
			false, fmt.Sprintf(
				"chown -R mysql %s && chmod 0660 %s", nf.FileName,
				nf.FileName,
			),
		); err != nil {
			logger.Error("chown -R mysql %s %s", nf.FileName, err.Error())
			return err
		}
	}
	return err
}

// calculateRepalceConfigs 计算每个实例proxy.cnf.{port} 需要替换的配置项 同时将需要的初始化的目录计算出来并赋值
//
//	@receiver i
//	@return err
func (i *InstallMySQLProxyComp) calculateRepalceConfigs() (err error) {
	i.InsReplaceConfigs = make(map[Port]proxyutil.ReplaceProxyConfigs)
	i.InsInitDirs = make(map[Port]InitDirs)
	i.InsInitFile = make(map[int]InitFiles)
	for _, port := range i.InsPorts {
		proxyLogPath := path.Join(i.ProxyBaseDir, strconv.Itoa(port), "log")
		adminUserfile := fmt.Sprintf("%s.%d", cst.DefaultProxyUserCnfName, port)
		i.InsInitDirs[port] = append(i.InsInitDirs[port], proxyLogPath)
		i.InsInitFile[port] = append(i.InsInitFile[port], adminUserfile)
		i.InsReplaceConfigs[port] = proxyutil.ReplaceProxyConfigs{
			BaseDir:             i.ProxyInstallDir,
			LogFile:             path.Join(proxyLogPath, "mysql-proxy.log"),
			AdminUsersFile:      adminUserfile,
			AdminAddress:        fmt.Sprintf("%s:%d", i.Params.Host, port+i.ProxyAdminPortInc),
			AdminUserName:       i.ProxyAdminUser,
			AdminPassWord:       i.ProxyAdminPwd,
			AdminLuaScript:      cst.DefaultAdminScripyLua,
			ProxyAddress:        fmt.Sprintf("%s:%d", i.Params.Host, port),
			ProxyBackendAddress: cst.DefaultBackend,
		}
	}
	return
}

// InitInstanceDirs 创建实例相关的数据，日志目录以及修改权限
//
//	@receiver i
//	@return err
func (i *InstallMySQLProxyComp) InitInstanceDirs() (err error) {
	for _, port := range i.InsPorts {
		for _, dir := range i.InsInitDirs[port] {
			if _, err := osutil.ExecShellCommand(
				false,
				fmt.Sprintf("mkdir -p %s && chown -R mysql %s", dir, dir),
			); err != nil {
				logger.Error("初始化实例目录%s 失败:%s", dir, err.Error())
				return err
			}
		}
		for _, file := range i.InsInitFile[port] {
			if _, err := osutil.ExecShellCommand(
				false, fmt.Sprintf(
					"touch %s && chown -R mysql %s && chmod 0660 %s ", file,
					file, file,
				),
			); err != nil {
				logger.Error("初始化文件%s 失败:%s", file, err.Error())
				return err
			}
		}
	}
	// 给根目录加权限
	if _, err := osutil.ExecShellCommand(false, fmt.Sprintf("chown -R mysql %s", i.ProxyBaseDir)); err != nil {
		logger.Error("初始化实例目录%s 失败:%s", i.ProxyBaseDir, err.Error())
		return err
	}
	return nil
}

// DecompressPkg TODO
/**
 * @description: 解压安装包
 * @return {*}
 */
func (i *InstallMySQLProxyComp) DecompressPkg() (err error) {
	if err = os.Chdir(i.UserLocal); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.UserLocal, err)
	}
	pkgAbPath := i.Params.Medium.GetAbsolutePath()
	if output, err := osutil.ExecShellCommand(
		false, fmt.Sprintf(
			"tar zxf %s -C %s ", pkgAbPath,
			i.UserLocal,
		),
	); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	proxyRealDirName := i.Params.Medium.GePkgBaseName()
	extraCmd := fmt.Sprintf(
		"ln -s %s mysql-proxy && chown -R mysql mysql-proxy && chown -R mysql %s", proxyRealDirName,
		proxyRealDirName,
	)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		err := fmt.Errorf("execute shell[%s]  get an error:%w and output:%s", extraCmd, err, output)
		return err
	}
	logger.Info("untar %s successfully", i.Params.Pkg)
	return nil
}

// Start TODO
/**
 * @description: 启动proxy
 * @return {*}
 */
func (i *InstallMySQLProxyComp) Start() error {
	for _, port := range i.InsPorts {
		p := proxyutil.StartProxyParam{
			InstallPath:    i.ProxyInstallDir,
			ProxyCnf:       util.GetProxyCnfName(port),
			Host:           i.Params.Host,
			Port:           port,
			ProxyAdminUser: i.ProxyAdminUser,
			ProxyAdminPwd:  i.ProxyAdminPwd,
		}
		if err := p.Start(); err != nil {
			logger.Error("start proxy(%d) failed,err:%s", port, err.Error())
			return err
		}
		logger.Info("start proxy(%d) successfully", port)
	}
	return nil
}

// InitProxyAdminAccount TODO
/**
 * @description:   初始化默认账户: add monitor@% user
 * @return {*}
 */
func (i *InstallMySQLProxyComp) InitProxyAdminAccount() (err error) {
	for _, port := range i.InsPorts {
		err = i.initOneProxyAdminAccount(port)
		if err != nil {
			return err
		}
	}
	return
}

func (i *InstallMySQLProxyComp) initOneProxyAdminAccount(port Port) (err error) {
	pc, err := native.NewDbWorkerNoPing(
		fmt.Sprintf("%s:%d", i.Params.Host, native.GetProxyAdminPort(port)), i.ProxyAdminUser,
		i.ProxyAdminPwd,
	)
	if err != nil {
		logger.Error("connect %d failed", port)
		return err
	}
	defer pc.Stop()
	_, err = pc.Exec(fmt.Sprintf("refresh_users('%s','+')", cst.ProxyUserMonitorAccessAll))
	if err != nil {
		logger.Error("add ProxyAdminAccount failed %s", err.Error())
		return err
	}
	return nil
}

// CreateExporterCnf 根据mysql部署端口生成对应的exporter配置文件
// 回档也会调用 install_mysql，但可能不会 install_monitor，为了避免健康误报，这个 install_mysql 阶段也渲染 exporter cnf
func (i *InstallMySQLProxyComp) CreateExporterCnf() (err error) {
	for _, inst := range i.InsPorts {
		err = mysql.CreateProxyExporterCnf(
			i.Params.Host, inst,
			i.GeneralParam.RuntimeAccountParam.MonitorUser,
			i.GeneralParam.RuntimeAccountParam.MonitorPwd,
		)
		if err != nil {
			return err
		}
	}

	return nil
}
