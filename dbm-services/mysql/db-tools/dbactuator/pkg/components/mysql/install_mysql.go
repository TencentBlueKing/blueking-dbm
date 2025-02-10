/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"text/template"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/rollback"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/spider"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/masterslaveheartbeat"
)

// InstallMySQLComp TODO
type InstallMySQLComp struct {
	GeneralParam       *components.GeneralParam `json:"general"`
	Params             *InstallMySQLParams      `json:"extend"`
	MySQLConfigParams  *MySQLConfigParams
	installMySQLConfig `json:"-"`
	RollBackContext    rollback.RollBackObjects `json:"-"`
	TimeZone           string

	// 执行这个 comp 时用的 mysql 帐号
	// 初始化安装的时候是 root, ""
	// 其他情况下用管理员帐号
	WorkUser     string `json:"-"`
	WorkPassword string `json:"-"`
	AvoidReset   bool   `json:"-"` // 迁移单据复用了这个 actor, 需要不做reset
}

// MySQLConfigParams TODO
type MySQLConfigParams struct {
	MyCnfConfigs json.RawMessage `json:"mycnf_configs"  validate:"required" `
}

// InstallMySQLParams TODO
type InstallMySQLParams struct {
	components.Medium
	// map[port]my.cnf
	MyCnfConfigs json.RawMessage
	// MySQLVersion 只需5.6 5.7 这样的大版本号
	MysqlVersion string `json:"mysql_version"  validate:"required"`
	// 字符集参数
	CharSet string `json:"charset" validate:"required,checkCharset"`
	// Ports
	Ports []int `json:"ports" validate:"required,gt=0,dive"`
	// 安装实例的内存大小，可以不指定，会自动计算
	InstMem                  uint64            `json:"inst_mem"`
	Host                     string            `json:"host" validate:"required,ip" `
	SuperAccount             AdditionalAccount `json:"super_account"`
	DBHAAccount              AdditionalAccount `json:"dbha_account"`
	WEBCONSOLERSAccount      AdditionalAccount `json:"webconsolers_account"`
	PartitionYWAccount       AdditionalAccount `json:"partition_yw_account"`
	SpiderAutoIncrModeMap    json.RawMessage   `json:"spider_auto_incr_mode_map"`
	AllowDiskFileSystemTypes []string
}

// InitDirs init dirs
type InitDirs = []string

// Port port
type Port = int
type socket = string

// SpiderAutoIncrModeValue spider au
type SpiderAutoIncrModeValue int

type installMySQLConfig struct {
	InstallDir              string
	MysqlInstallDir         string
	TdbctlInstallDir        string
	DataRootPath            string
	LogRootPath             string
	DataBaseDir             string // eg: /data1/mysqldata/
	LogBaseDir              string // eg: /data/mysqllog/
	DefaultMysqlDataDirName string
	DefaultMysqlLogDirName  string
	MyCnfTpls               map[Port]*util.CnfFile // 	MyCnfConfigs json.RawMessage 反序列化后的对象
	InsPorts                []Port
	RenderConfigs           map[Port]RenderConfigs
	InsInitDirs             map[Port]InitDirs
	InsSockets              map[Port]socket
	SpiderAutoIncrModeMap   map[Port]SpiderAutoIncrModeValue
	Checkfunc               []func() error
}

// RenderConfigs TODO
type RenderConfigs struct {
	Mysqld Mysqld
}

// Mysqld TODO
type Mysqld struct {
	Port                         string                  `json:"port"`
	Datadir                      string                  `json:"datadir"`
	Logdir                       string                  `json:"logdir"`
	CharacterSetServer           string                  `json:"character_set_server"`
	CollationServer              string                  `json:"collation_server"`
	BindAddress                  string                  `json:"bind-address"`
	ServerId                     uint64                  `json:"server_id"`
	InnodbBufferPoolSize         string                  `json:"innodb_buffer_pool_size"`
	SpiderAutoIncrementModeValue SpiderAutoIncrModeValue `json:"spider_auto_increment_mode_value"`
}

// Example subcommand example input
func (i *InstallMySQLComp) Example() interface{} {
	comp := InstallMySQLComp{
		Params: &InstallMySQLParams{
			Medium: components.Medium{
				Pkg:    "mysql-5.6.24-linux-x86_64-tmysql-2.2.3-gcs.tar.gz",
				PkgMd5: "a2dba04a7d96928473ab8ac5132edee1",
			},
			MysqlVersion: "",
			CharSet:      "utf8",
			Ports:        []int{20000, 20001},
			InstMem:      0,
			SuperAccount: AdditionalAccount{
				User:        "user",
				Pwd:         "xxx",
				AccessHosts: []string{"ip1", "ip2"},
			},
			DBHAAccount: AdditionalAccount{
				User:        "user",
				Pwd:         "xxx",
				AccessHosts: []string{"ip1", "ip2"},
			},
		},
	}
	return comp
}

// InitDefaultParam TODO
func (i *InstallMySQLComp) InitDefaultParam() (err error) {
	i.WorkUser = "root"
	i.WorkPassword = ""
	i.AvoidReset = false

	i.Params.MyCnfConfigs = i.MySQLConfigParams.MyCnfConfigs
	var mountpoint string
	i.InstallDir = cst.UsrLocal
	i.MysqlInstallDir = cst.MysqldInstallPath
	i.TdbctlInstallDir = cst.TdbctlInstallPath
	i.DataRootPath = cst.DefaultMysqlDataRootPath
	i.LogRootPath = cst.DefaultMysqlLogRootPath
	i.DefaultMysqlDataDirName = cst.DefaultMysqlDataBasePath
	i.DefaultMysqlLogDirName = cst.DefaultMysqlLogBasePath
	i.Params.AllowDiskFileSystemTypes = []string{"ext4", "xfs"}
	// 计算获取需要安装的ports
	i.InsPorts = i.Params.Ports
	i.MyCnfTpls = make(map[int]*util.CnfFile)
	// 获取系统内存,计算实例内存大小
	if err = i.initMySQLInstanceMem(); err != nil {
		return err
	}
	// var findMountPoint func(paths ...string) (string, error)
	if i.Params.GetPkgTypeName() != cst.PkgTypeMysql {
		// 日志目录优先放在 /data 盘下
		mountpoint, err = osutil.FindFirstMountPointProxy(cst.DefaultMysqlLogRootPath, cst.AlterNativeMysqlLogRootPath)
		if err != nil {
			logger.Error("not found mount point /data")
			return err
		}
		i.DataRootPath = mountpoint
		i.DataBaseDir = path.Join(mountpoint, cst.DefaultMysqlDataBasePath)
		i.LogRootPath = mountpoint
		i.LogBaseDir = path.Join(mountpoint, cst.DefaultMysqlLogBasePath)
		// 如果单独挂盘,就用单独挂的盘去作为数据盘
		ok, _ := osutil.IsMountPoint(cst.DefaultMysqlDataRootPath)
		if ok {
			var errx error
			mountpoint, errx = osutil.FindFirstMountPointProxy(cst.DefaultMysqlDataRootPath, cst.AlterNativeMysqlDataRootPath)
			if errx == nil {
				i.DataRootPath = mountpoint
				i.DataBaseDir = path.Join(mountpoint, cst.DefaultMysqlDataBasePath)
			}
		}
	} else {
		// 数据目录优先放在 /data1 盘下
		mountpoint, err = osutil.FindFirstMountPoint(cst.DefaultMysqlDataRootPath, cst.AlterNativeMysqlDataRootPath)
		if err != nil {
			logger.Error("not found mount point /data1")
			return err
		}
		i.DataRootPath = mountpoint
		i.DataBaseDir = path.Join(mountpoint, cst.DefaultMysqlDataBasePath)

		// 日志目录优先放在 /data 盘下
		mountpoint, err = osutil.FindFirstMountPoint(cst.DefaultMysqlLogRootPath, cst.AlterNativeMysqlLogRootPath)
		if err != nil {
			logger.Error("not found mount point /data")
			return err
		}
		i.LogRootPath = mountpoint
		i.LogBaseDir = path.Join(mountpoint, cst.DefaultMysqlLogBasePath)
	}
	// 反序列化mycnf 配置
	var mycnfs map[Port]json.RawMessage
	if err = json.Unmarshal(i.Params.MyCnfConfigs, &mycnfs); err != nil {
		logger.Error("反序列化配置失败:%s", err.Error())
		return err
	}

	for _, port := range i.InsPorts {
		var cnfraw json.RawMessage
		var ok bool
		if cnfraw, ok = mycnfs[port]; !ok {
			return fmt.Errorf("参数中没有%d的配置", port)
		}
		var mycnf mysqlutil.MycnfObject
		if err = json.Unmarshal(cnfraw, &mycnf); err != nil {
			logger.Error("反序列%d 化配置失败:%s", port, err.Error())
			return err
		}
		cnftpl, ierr := util.NewMyCnfObject(mycnf, "tpl")
		if ierr != nil {
			logger.Error("初始化mycnf ini 模版:%s", ierr.Error())
			return ierr
		}
		i.MyCnfTpls[port] = cnftpl
	}

	// 如果SpiderAutoIncrModeMap有传入，则渲染
	if i.Params.SpiderAutoIncrModeMap != nil {
		i.SpiderAutoIncrModeMap = make(map[int]SpiderAutoIncrModeValue)
		if err = json.Unmarshal(i.Params.SpiderAutoIncrModeMap, &i.SpiderAutoIncrModeMap); err != nil {
			logger.Error("反序列化配置失败:%s", err.Error())
			return err
		}
	}

	// 计算需要替换的参数配置
	if err := i.initInsReplaceMyConfigs(); err != nil {
		return err
	}
	i.Checkfunc = append(i.Checkfunc, i.CheckTimeZoneSetting)
	i.Checkfunc = append(i.Checkfunc, i.precheckMysqlDir)
	i.Checkfunc = append(i.Checkfunc, i.precheckMysqlProcess)
	i.Checkfunc = append(i.Checkfunc, i.precheckMysqlPackageBitOS)
	i.Checkfunc = append(i.Checkfunc, i.precheckGlibcVersion)
	i.Checkfunc = append(i.Checkfunc, i.Params.Medium.Check)
	return nil
}

// PreCheck TODO
func (i *InstallMySQLComp) PreCheck() error {
	for _, f := range i.Checkfunc {
		if err := f(); err != nil {
			logger.Error("check failed %s", err.Error())
			return err
		}
	}
	return nil
}

// precheckMysqlDir TODO
/*
	检查根路径下是已经存在mysql相关的数据和日志目录
	eg:
	/data1/mysqldata/{port}
	/data/mysqldata/{port}
	/data1/mysqllog/{port}
	/data/mysqllog/{port}
*/
func (i *InstallMySQLComp) precheckMysqlDir() error {
	for _, port := range i.InsPorts {
		for _, rootDir := range []string{cst.DefaultMysqlLogRootPath, cst.DefaultMysqlDataRootPath} {
			d := path.Join(rootDir, i.DefaultMysqlDataDirName, strconv.Itoa(port))
			if osutil.FileExist(d) {
				return fmt.Errorf("%s 已经存在了", d)
			}
			l := path.Join(rootDir, i.DefaultMysqlLogDirName, strconv.Itoa(port))
			if osutil.FileExist(l) {
				return fmt.Errorf("%s 已经存在了", l)
			}
		}
	}
	return nil
}

func (i *InstallMySQLComp) precheckFilesystemType() (err error) {
	for _, dirPath := range util.UniqueStrings([]string{i.DataRootPath, i.LogRootPath}) {
		mountInfo := osutil.GetMountPathInfo(dirPath)
		if len(mountInfo) != 1 {
			return errors.Errorf("failed to get filesystem type for %s", dirPath)
		}
		for mountPath, info := range mountInfo {
			if mountPath != dirPath {
				logger.Warn("dir %s is mounted original on %s with device %s", dirPath, info.Path, info.Filesystem)
			}
			logger.Info("dir %s : %s", dirPath, info.FileSystemType)
			if !util.StringsHas(i.Params.AllowDiskFileSystemTypes, info.FileSystemType) {
				return fmt.Errorf("the %s,Filesystem is %s,is not allowed", dirPath, info.FileSystemType)
			}
		}
	}
	return nil
}

func (i *InstallMySQLComp) precheckMysqlProcess() (err error) {
	var output string
	var mysqldNum int

	// 如果正在部署tdbctl组件，部署场景会与这块引起冲突，则暂时先跳过。
	if i.Params.Medium.GetPkgTypeName() == cst.PkgTypeTdbctl {
		logger.Warn("正在部署tdbctl组件,不再mysqld进程存活检查")
		return nil
	}
	if output, err = osutil.ExecShellCommand(false, "ps -ef|grep 'mysqld ' |grep -v grep |wc -l"); err != nil {
		return fmt.Errorf("%w 执行ps -efwww|grep -w mysqld|grep -v grep|wc -l失败", err)
	}
	logger.Info("output:", output)
	if mysqldNum, err = strconv.Atoi(osutil.CleanExecShellOutput(output)); err != nil {
		logger.Error("strconv.Atoi %s failed:%s", output, err.Error())
		return err
	}
	if mysqldNum > 0 {
		return fmt.Errorf("have %d mysqld process running", mysqldNum)
	}
	return nil
}

func (i *InstallMySQLComp) precheckMysqlPackageBitOS() error {
	var mysqlBits = cst.Bit64
	if strings.Contains(i.Params.Medium.Pkg, cst.X32) {
		mysqlBits = cst.Bit32
	}
	if mysqlBits != cst.OSBits {
		return fmt.Errorf("mysql 安装包的和系统不匹配,当前系统是%d", cst.OSBits)
	}
	return nil
}

func (i *InstallMySQLComp) precheckGlibcVersion() error {
	glibcVer, err := cmutil.GetGlibcVersion()
	if err != nil {
		logger.Error("failed to glibc version, err:%s", err.Error())
		return err
	}
	// mysql 8.0 不安装在 tlinux1.2上 (mysqld能运行，但周边 xtrabackup 8.0 依赖 glibc>=2.14)
	if cmutil.MySQLVersionParse(i.Params.MysqlVersion) >= cmutil.MySQLVersionParse("8.0.0") && glibcVer < "2.14" {
		return errors.Errorf("glibc version %s it not allowed to install %s", glibcVer, i.Params.MysqlVersion)
	}
	return nil
}

// initMySQLInstanceMem TODO
// GetInstMemByIP 返回的内存单位是 MB
func (i *InstallMySQLComp) initMySQLInstanceMem() (err error) {
	var instMem uint64
	if i.Params.InstMem > 0 {
		return nil
	}
	if instMem, err = mysqlutil.GetInstMemByIP(uint64(len(i.InsPorts))); err != nil {
		logger.Error("获取实例内存失败, err: %w", err)
		return fmt.Errorf("获取实例内存失败, err: %w", err)
	}
	i.Params.InstMem = instMem
	return nil
}

// initInsReplaceMyConfigs TODO
/*
	初始化每个实例需要替换的配置参数,供生成实际my.cnf配置文件

		mysqldata
			- socket					socket=/data1/mysqldata/20000/mysql.sock
			- datadir  					datadir=/data1/mysqldata/20000/data
			- tmpdir					tmpdir=/data1/mysqldata/20000/tmp
			- innodb_data_home_dir		innodb_data_home_dir=/data1/mysqldata/20000/innodb/data
			- innodb_log_group_home_dir innodb_log_group_home_dir=/data1/mysqldata/20000/innodb/log
		mysqllog
			- log_bin 					log_bin=/data/mysqllog/20000/binlog/binlog20000.bin
			- slow_query_log_file		slow_query_log_file=/data/mysqllog/20000/slow-query.log
			- relay-log					relay-log=/data1/mysqldata/relay-log/relay-log.bin
*/
func (i *InstallMySQLComp) initInsReplaceMyConfigs() error {
	i.RenderConfigs = make(map[int]RenderConfigs)
	i.InsInitDirs = make(map[int]InitDirs)
	i.InsSockets = make(map[int]string)
	for _, port := range i.InsPorts {
		insBaseDataDir := path.Join(i.DataBaseDir, strconv.Itoa(port))
		insBaseLogDir := path.Join(i.LogBaseDir, strconv.Itoa(port))
		serverId, err := mysqlutil.GenMysqlServerId(i.Params.Host, port)
		if err != nil {
			logger.Error("%s:%d generation serverId Failed %s", i.Params.Host, port, err.Error())
			return err
		}
		i.RenderConfigs[port] = RenderConfigs{Mysqld{
			Datadir:                      insBaseDataDir,
			Logdir:                       insBaseLogDir,
			ServerId:                     serverId,
			Port:                         strconv.Itoa(port),
			CharacterSetServer:           i.Params.CharSet,
			InnodbBufferPoolSize:         fmt.Sprintf("%dM", i.Params.InstMem),
			BindAddress:                  i.Params.Host,
			SpiderAutoIncrementModeValue: i.SpiderAutoIncrModeMap[port],
		}}

		i.InsInitDirs[port] = append(i.InsInitDirs[port], []string{insBaseDataDir, insBaseLogDir}...)
	}
	return nil
	//	return i.calInsInitDirs()
}

// getInitDirFromCnf TODO
// calInsInitDirs  从模板配置获取需要初始化新建的目录
func (i *InstallMySQLComp) getInitDirFromCnf() (err error) {
	// 获取需要初始化目录的模板值
	initDirTpls := map[string]string{
		"datadir":                   "",
		"innodb_log_group_home_dir": "",
		"innodb_data_home_dir":      "",
		"log_bin":                   "",
		"relay-log":                 "",
		"tmpdir":                    "",
		"socket":                    "",
	}
	for _, port := range i.InsPorts {
		cnf, ierr := util.LoadMyCnfForFile(util.GetMyCnfFileName(port))
		if ierr != nil {
			return ierr
		}
		if err = cnf.GetInitDirItemTpl(initDirTpls); err != nil {
			return err
		}
		for key, dir := range initDirTpls {
			switch strings.ReplaceAll(key, "-", "_") {
			case "log_bin", "relay_log":
				i.InsInitDirs[port] = append(i.InsInitDirs[port], path.Dir(dir))
			case "socket":
				i.InsSockets[port] = dir
			default:
				i.InsInitDirs[port] = append(i.InsInitDirs[port], dir)
			}
		}
	}
	return err
}

// GenerateMycnf TODO
/**
 * @description: 渲染配置
 * @return {*}
 */
func (i *InstallMySQLComp) GenerateMycnf() (err error) {
	// 1. 根据参数反序列化配置
	var tmplFileName = "/tmp/my.cnf.tpl"

	// 2. 替换数据目录、日志目录生产实际配置文件
	for _, port := range i.InsPorts {
		i.MyCnfTpls[port].FileName = tmplFileName
		err := i.generateMycnfOnePort(port, tmplFileName)
		if err != nil {
			return err
		}
	}
	return nil
}

func (i *InstallMySQLComp) generateMycnfOnePort(port Port, tmplFileName string) error {
	i.MyCnfTpls[port].FileName = tmplFileName
	if err := i.MyCnfTpls[port].SafeSaveFile(false); err != nil {
		logger.Error("保存模版文件失败:%s", err.Error())
		return err
	}
	// 防止过快读取到的是空文件
	if err := util.Retry(util.RetryConfig{Times: 3, DelayTime: 100 * time.Millisecond}, func() error {
		return util.FileIsEmpty(tmplFileName)
	}); err != nil {
		return err
	}
	tmpl, err := template.ParseFiles(tmplFileName)
	if err != nil {
		return fmt.Errorf("template ParseFiles failed, err: %w", err)
	}
	cnf := util.GetMyCnfFileName(port)
	f, err := os.Create(cnf)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	if err = tmpl.Execute(f, i.RenderConfigs[port]); err != nil {
		return err
	}
	if _, err = osutil.ExecShellCommand(false, fmt.Sprintf("chown -R mysql %s", cnf)); err != nil {
		logger.Error("chown -R mysql %s %s", cnf, err.Error())
		return err
	}

	return nil
}

// InitInstanceDirs TODO
/*
	创建实例相关的数据，日志目录以及修改权限
*/
func (i *InstallMySQLComp) InitInstanceDirs() (err error) {
	if err = i.getInitDirFromCnf(); err != nil {
		return err
	}
	for _, port := range i.InsPorts {
		for _, dir := range i.InsInitDirs[port] {
			if util.StrIsEmpty(dir) {
				continue
			}
			cmd := fmt.Sprintf("mkdir -p %s && chown -R mysql:mysql %s", dir, dir)
			if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
				logger.Error("初始化实例目录%s 失败:%s", dir, err.Error())
				return err
			}
			// mkdir ok, add will rollback dir
			i.RollBackContext.AddDelFile(dir)
		}
	}
	for _, dir := range []string{i.DataBaseDir, i.LogBaseDir} {
		if _, err := osutil.ExecShellCommand(false, fmt.Sprintf("chown -R mysql %s", dir)); err != nil {
			logger.Error("该更%s所属组失败:%s", dir, err.Error())
			return err
		}
	}
	return nil
}

// DecompressMysqlPkg TODO
/**
 * @description:  校验、解压mysql安装包
 * @return {*}
 */
func (i *InstallMySQLComp) DecompressMysqlPkg() (err error) {
	if err = os.Chdir(i.InstallDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InstallDir, err)
	}
	// 判断 /usr/local/mysql 目录是否已经存在,如果存在则删除掉
	if cmutil.FileExists(i.MysqlInstallDir) {
		if _, err = osutil.ExecShellCommand(false, "rm -r "+i.MysqlInstallDir); err != nil {
			logger.Error("rm -r %s error: %w", i.MysqlInstallDir, err)
			return err
		}
	}
	pkgAbPath := i.Params.Medium.GetAbsolutePath()
	if output, ierr := osutil.ExecShellCommand(false, fmt.Sprintf("tar -xf %s", pkgAbPath)); ierr != nil {
		logger.Error("tar -xf %s error:%s,%s", pkgAbPath, output, ierr.Error())
		return ierr
	}
	mysqlBinaryFile := i.Params.Medium.GePkgBaseName()
	extraCmd := fmt.Sprintf("ln -sf %s %s && chown -R mysql mysql*", mysqlBinaryFile, i.MysqlInstallDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	logger.Info("mysql binary directory: %s", mysqlBinaryFile)
	if _, err := os.Stat(i.MysqlInstallDir); err != nil {
		logger.Error("%s check failed, %v", i.MysqlInstallDir, err)
		return err
	}
	logger.Info("decompress mysql pkg successfully")
	return nil
}

// Install TODO
/**
 * @description:  mysqld init 初始化mysql 内置的系统库表
 * @return {*}
 */
func (i *InstallMySQLComp) Install() (err error) {
	logger.Info("开始安装mysql实例 ~  %v", i.InsPorts)
	var isSudo = mysqlutil.IsSudo()
	for _, port := range i.InsPorts {
		var initialMysql string
		myCnf := util.GetMyCnfFileName(port)
		initialLogFile := fmt.Sprintf("/tmp/install_mysql_%d.log", port)

		// mysql5.7.18以下版本或者spider版本的初始化命令
		initialMysql = fmt.Sprintf(
			"su - mysql -c \"cd /usr/local/mysql && ./scripts/mysql_install_db --defaults-file=%s --user=mysql --force &>%s\"",
			myCnf, initialLogFile)

		i.Params.MysqlVersion = i.Params.Medium.GetPkgVersion()
		// mysql5.7.18以上的版本
		if cmutil.MySQLVersionParse(i.Params.MysqlVersion) >= cmutil.MySQLVersionParse("5.7.18") &&
			i.Params.Medium.GetPkgTypeName() == "mysql" {
			initialMysql = fmt.Sprintf(
				"su - mysql -c \"cd /usr/local/mysql && ./bin/mysqld --defaults-file=%s --initialize-insecure --user=mysql &>%s\"",
				myCnf, initialLogFile)
		}
		// 拼接tdbctl专属初始化命令
		if i.Params.GetPkgTypeName() == cst.PkgTypeTdbctl {
			initialMysql = fmt.Sprintf(
				"su - mysql -c \"cd %s && ./bin/mysqld --defaults-file=%s  --tc-admin=0 --initialize-insecure --user=mysql &>%s\"",
				i.TdbctlInstallDir, myCnf, initialLogFile)
		}
		// 避免错误: /etc/profile: line 87: ulimit: open files: cannot modify limit: Operation not permitted
		if _, errStr, err := cmutil.ExecBashCommand(isSudo, "", initialMysql); err != nil {
			logger.Error("%s execute failed, err:%s, stderr:%s", initialMysql, err.Error(), errStr)
			// 如果存在初始化的日志文件，才初始化错误的时间，将日志cat出来
			if osutil.FileExist(initialLogFile) {
				ldat, e := os.ReadFile(initialLogFile)
				if e != nil {
					logger.Warn("读取初始化mysqld日志失败%s", e.Error())
				} else {
					logger.Error("初始化mysqld失败日志： %s", string(ldat))
				}
			}
			return err
		}
		/*
			checkFile := path.Join(i.InsReplaceMyConfigs[port].Mysqld.DataDir, "mysql", "user.MYD")
			if mysqlutil.MySQLVersionParse(i.Params.MysqlVersion) >= mysqlutil.MySQLVersionParse("8.0") {
				checkFile = path.Join(i.InsReplaceMyConfigs[port].Mysqld.DataDir, "sys", "sys_config.ibd")
			}
			logger-back.Info("check [%s]", checkFile)
			if _, err := os.Stat(checkFile); os.IsNotExist(err) {
				logger-back.Error("check [%s] file failed, %v", checkFile, err)
				return err
			}
		*/
		time.Sleep(5 * time.Second)
	}
	logger.Info("Init all mysqld successfully")
	return nil
}

// MakeSocketSoftLink 当单机只存在一个实例的时候,mysql.socket 软链到tmp 下
func (i *InstallMySQLComp) MakeSocketSoftLink() (err error) {
	logger.Info("install ports %v", i.InsPorts)
	if len(i.InsPorts) == 1 {
		port := i.InsPorts[0]
		socket, ok := i.InsSockets[port]
		if !ok {
			return fmt.Errorf("not found %d's socket", port)
		}
		shellCmds := []string{"unlink  /tmp/mysql.sock", fmt.Sprintf("ln -s %s  /tmp/mysql.sock", socket)}
		for _, shell := range shellCmds {
			stderr, err := osutil.StandardShellCommand(false, shell)
			if err != nil {
				logger.Warn("do %s failed,stderr:%s", shell, stderr)
				continue
			}
		}
	}
	return nil
}

// Startup @description: 启动mysqld实例 会重试连接判断是否启动成功
func (i *InstallMySQLComp) Startup() (err error) {
	if err = osutil.ClearTcpRecycle(); err != nil {
		err = fmt.Errorf("clear tcp recycle failed, err: %w", err)
		logger.Warn("startup, %s", err.Error())
	}
	for _, port := range i.InsPorts {
		logger.Info("will start %d", port)
		s := computil.StartMySQLParam{
			MediaDir:      i.MysqlInstallDir,
			MyCnfName:     util.GetMyCnfFileName(port),
			MySQLUser:     i.WorkUser,     // "root",
			MySQLPwd:      i.WorkPassword, // "",
			Socket:        i.InsSockets[port],
			SkipSlaveFlag: false,
		}
		pid, err := s.StartMysqlInstance()
		if err != nil {
			logger.Error("start %d failed err: %s", port, err.Error())
			return err
		}
		i.RollBackContext.AddKillProcess(pid)
	}
	return nil
}

// generateDefaultMysqlAccount TODO
/**
* @description:  生成初始化默认mysql 账户sql
* @receiver {string} realVersion: mysql 实际版本
* @return {*}
注意这里修改，考虑可能需要同步改动 generateDefaultSpiderAccount
*/
func (i *InstallMySQLComp) generateDefaultMysqlAccount(realVersion string) (initAccountsql []string) {
	i.Params.PartitionYWAccount.AccessHosts = []string{
		i.Params.Host,
		"localhost",
	}
	initAccountsql = append(initAccountsql, i.Params.SuperAccount.GetSuperUserAccount(realVersion)...)
	initAccountsql = append(initAccountsql, i.Params.DBHAAccount.GetDBHAAccount(realVersion)...)
	initAccountsql = append(initAccountsql, i.Params.WEBCONSOLERSAccount.GetWEBCONSOLERSAccount(realVersion)...)
	initAccountsql = append(initAccountsql, i.Params.PartitionYWAccount.GetPartitionYWAccount(realVersion)...)

	runp := i.GeneralParam.RuntimeAccountParam
	var privPairs []components.MySQLAccountPrivs
	privPairs = append(privPairs, runp.MySQLAdminAccount.GetAccountPrivs(i.Params.Host))
	// 这里做一个处理，传入的AdminUser 不一定是真正的ADMIN账号，如果不是则手动添加一个,保证新实例有ADMIN账号
	if runp.AdminUser != "ADMIN" {
		privPairs = append(privPairs, components.MySQLAdminAccount{
			AdminUser: "ADMIN",
			AdminPwd:  runp.AdminPwd,
		}.GetAccountPrivs(i.Params.Host))

	}
	privPairs = append(privPairs, runp.MySQLMonitorAccessAllAccount.GetAccountPrivs())
	privPairs = append(privPairs, runp.MySQLMonitorAccount.GetAccountPrivs(i.Params.Host))
	privPairs = append(privPairs, runp.MySQLYwAccount.GetAccountPrivs())
	privPairs = append(privPairs, runp.MySQLDbBackupAccount.GetAccountPrivs(realVersion, i.Params.Host))
	for _, v := range privPairs {
		initAccountsql = append(initAccountsql, v.GenerateInitSql(realVersion)...)
	}
	if cmutil.MySQLVersionParse(realVersion) >= cmutil.MySQLVersionParse("5.7.18") {
		s :=
			`REPLACE INTO mysql.db(Host,Db,User,Select_priv,Insert_priv,Update_priv,Delete_priv,Create_priv,Drop_priv,
                     Grant_priv,References_priv,Index_priv,Alter_priv,Create_tmp_table_priv,Lock_tables_priv,
                     Create_view_priv,Show_view_priv,Create_routine_priv,Alter_routine_priv,Execute_priv,
                     Event_priv,Trigger_priv)
VALUES ('%','test','','Y','Y','Y','Y','Y','Y','N','Y','Y','Y','Y','Y','Y','Y','Y','N','N','Y','Y');`
		initAccountsql = append(initAccountsql, s)
	} else if cmutil.MySQLVersionParse(i.Params.MysqlVersion) <= cmutil.MySQLVersionParse("5.6") {
		s := `alter table mysql.general_log change thread_id thread_id bigint(21) unsigned NOT NULL;`
		initAccountsql = append(initAccountsql, s)
	}
	initAccountsql = append(initAccountsql, "delete from mysql.user where user='root' or user='';")
	initAccountsql = append(initAccountsql, "update mysql.db set Insert_priv = 'Y' where db = 'test';")
	initAccountsql = append(initAccountsql, "flush privileges;")
	return initAccountsql
}

// AdditionalAccount  额外账户
type AdditionalAccount struct {
	User        string   `json:"user" validate:"required"`
	Pwd         string   `json:"pwd"  validate:"required"`
	AccessHosts []string `json:"access_hosts"`
}

// GetSuperUserAccount 获取超级账户授权语句
func (a *AdditionalAccount) GetSuperUserAccount(realVersion string) (initAccountsql []string) {
	for _, host := range cmutil.RemoveDuplicate(a.AccessHosts) {
		if cmutil.MySQLVersionParse(realVersion) >= cmutil.MySQLVersionParse("5.7.18") {
			initAccountsql = append(initAccountsql,
				fmt.Sprintf("CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED WITH mysql_native_password BY '%s' ;",
					a.User, host, a.Pwd))
			initAccountsql = append(initAccountsql, fmt.Sprintf("GRANT ALL PRIVILEGES ON *.* TO '%s'@'%s' WITH GRANT OPTION ; ",
				a.User, host))
		} else {
			initAccountsql = append(initAccountsql,
				fmt.Sprintf("GRANT ALL PRIVILEGES ON *.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION ;",
					a.User, host, a.Pwd))
		}
	}
	return
}

// GetPartitionYWAccount  获取分区管理运维账户授权语句
func (a *AdditionalAccount) GetPartitionYWAccount(realVersion string) (initAccountsql []string) {
	for _, host := range cmutil.RemoveDuplicate(a.AccessHosts) {
		if cmutil.MySQLVersionParse(realVersion) >= cmutil.MySQLVersionParse("5.7.18") {
			initAccountsql = append(
				initAccountsql,
				fmt.Sprintf(
					`CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED WITH mysql_native_password BY '%s';`,
					a.User, host, a.Pwd,
				),
			)
			initAccountsql = append(
				initAccountsql,
				fmt.Sprintf(
					`GRANT SELECT, INSERT, UPDATE, DELETE, 
								CREATE, DROP, ALTER, TRIGGER, 
								PROCESS, SUPER, REPLICATION SLAVE ON *.* TO '%s'@'%s';`,
					a.User, host,
				),
			)
		} else {
			initAccountsql = append(
				initAccountsql,
				fmt.Sprintf(
					`GRANT SELECT, INSERT, UPDATE, DELETE, 
								CREATE, DROP, ALTER, TRIGGER, 
								PROCESS, SUPER, REPLICATION SLAVE ON *.* TO '%s'@'%s' IDENTIFIED BY '%s';`,
					a.User, host, a.Pwd,
				),
			)
		}
	}
	return initAccountsql
}

// GetWEBCONSOLERSAccount 获取webconsole账户授权语句
func (a *AdditionalAccount) GetWEBCONSOLERSAccount(realVersion string) (initAccountsql []string) {
	for _, host := range cmutil.RemoveDuplicate(a.AccessHosts) {
		if cmutil.MySQLVersionParse(realVersion) >= cmutil.MySQLVersionParse("5.7.18") {
			initAccountsql = append(
				initAccountsql,
				fmt.Sprintf(
					`CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED WITH mysql_native_password BY '%s';`,
					a.User, host, a.Pwd,
				),
			)
			initAccountsql = append(
				initAccountsql,
				fmt.Sprintf(
					`GRANT SELECT, RELOAD, PROCESS, SHOW DATABASES ON *.* TO '%s'@'%s';`,
					a.User, host,
				),
			)
		} else {
			initAccountsql = append(
				initAccountsql,
				fmt.Sprintf(
					`GRANT SELECT, RELOAD, PROCESS, SHOW DATABASES ON *.* TO '%s'@'%s' IDENTIFIED BY '%s';`,
					a.User, host, a.Pwd))
		}
	}
	return
}

// GetDBHAAccount 获取生成DHBA-GM访问账号的生成语句
// 统一给%授权
func (a *AdditionalAccount) GetDBHAAccount(realVersion string) (initAccountsql []string) {
	if cmutil.MySQLVersionParse(realVersion) >= cmutil.MySQLVersionParse("5.7.18") {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf("CREATE USER IF NOT EXISTS '%s'@'%%' IDENTIFIED WITH mysql_native_password BY '%s' ;",
				a.User, a.Pwd))
		initAccountsql = append(initAccountsql, fmt.Sprintf(
			"GRANT RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW "+
				"ON *.* TO '%s'@'%%' WITH GRANT OPTION ;",
			a.User))
	} else {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(
				"GRANT RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW "+
					"ON *.* TO '%s'@'%%' IDENTIFIED BY '%s' WITH GRANT OPTION ;",
				a.User, a.Pwd))
	}

	initAccountsql = append(initAccountsql,
		fmt.Sprintf("GRANT SELECT, INSERT, DELETE ON `infodba_schema`.* TO '%s'@'%%' ;", a.User))

	initAccountsql = append(initAccountsql,
		fmt.Sprintf(" GRANT SELECT ON `mysql`.* TO '%s'@'%%' ;", a.User))
	return
}

// InitDefaultPrivAndSchemaWithResetMaster TODO
/**
 * @description: 执行初始化默认库表语句&初始化默认账户sql
 * @return {*}
 */
func (i *InstallMySQLComp) InitDefaultPrivAndSchemaWithResetMaster() (err error) {
	var bsql []byte
	var initSQLs []string

	// 拼接tdbctl session级命令，初始化session设置tc_admin=0
	if i.Params.GetPkgTypeName() == cst.PkgTypeTdbctl {
		logger.Info("on tdbctl")
		initSQLs = append(initSQLs, "set tc_admin = 0;")
	}

	if bsql, err = staticembed.DefaultSysSchemaSQL.ReadFile(staticembed.DefaultSysSchemaSQLFileName); err != nil {
		logger.Error("读取嵌入文件%s失败", staticembed.DefaultSysSchemaSQLFileName)
		return err
	}
	logger.Info("read embed sql success: %s", bsql)

	for _, value := range strings.SplitAfterN(string(bsql), ";", -1) {
		if !regexp.MustCompile(`^\\s*$`).MatchString(value) {
			initSQLs = append(initSQLs, value)
		}
	}
	// 剔除最后一个空字符，splits 会多分割出一个空字符
	if len(initSQLs) < 2 {
		return fmt.Errorf("初始化sql为空%v", initSQLs)
	}
	if i.Params.GetPkgTypeName() == cst.PkgTypeTdbctl {
		initSQLs = append(initSQLs, staticembed.SpiderInitSQL)
	}

	if bsql, err = staticembed.ProcedureSQL.ReadFile(staticembed.GrantProcedureSQLFileName); err != nil {
		logger.Error("读取存储过程嵌入文件%s失败", staticembed.ProcedureSQL)
		return err
	}
	logger.Info("read embed procedure sql success: %s", bsql)

	for _, value := range strings.SplitAfterN(string(bsql), `#`, -1) {
		if !regexp.MustCompile(`^\\s*$`).MatchString(value) {
			initSQLs = append(initSQLs, value)
		}
	}
	// 剔除最后一个空字符，splits 会多分割出一个空字符
	if len(initSQLs) < 2 {
		return fmt.Errorf("初始化sql为空%v", initSQLs)
	}

	if i.Params.GetPkgTypeName() == cst.PkgTypeTdbctl {
		initSQLs = append(initSQLs, staticembed.SpiderInitSQL)
	}

	// 调用 mysql-monitor 里的主从复制延迟检查心跳表, infodba_schema.master_slave_heartbeat
	initSQLs = append(initSQLs, masterslaveheartbeat.DropTableSQL, masterslaveheartbeat.CreateTableSQL)
	if i.Params.GetPkgTypeName() == cst.PkgTypeMysql { // 避免迁移实例时，新机器还没有这个表，会同步失败
		initSQLs = append(initSQLs, spider.GetGlobalBackupSchema("InnoDB", nil))
	}

	for _, port := range i.InsPorts {
		logger.Info("do init on %d", port)
		var dbWork *native.DbWorker
		if dbWork, err = native.NewDbWorker(
			native.DsnBySocket(i.InsSockets[port] /*"root", ""*/, i.WorkUser, i.WorkPassword)); err != nil {
			logger.Error("connect by %s failed,err:%s", port, err.Error())
			return err
		}

		// 初始化schema
		if _, err := dbWork.ExecMore(initSQLs); err != nil {
			logger.Error("init %d schema failed for %v", port, err)
			return err
		}
		version, err := dbWork.SelectVersion()
		if err != nil {
			logger.Error("get %d mysql version failed  %v", port, err)
			return err
		}

		// 初始化权限
		var initAccountSqls []string
		switch {
		case strings.Contains(version, "tspider"):
			// 对spider 初始化授权
			if err := i.createSpiderTable(i.InsSockets[port]); err != nil {
				return err
			}
			initAccountSqls = i.generateDefaultSpiderAccount(version)
			i.AvoidReset = true // spider 有可能没开 binlog，reset master 会报错
		case strings.Contains(version, "tdbctl"):
			// 对tdbctl 初始化权限
			logger.Info("tdbctl port %d need tc_admin=0, binlog_format=off", port)
			initAccountSqls = append(initAccountSqls, "set session tc_admin=0;", "set session sql_log_bin=off;")
			initAccountSqls = append(initAccountSqls, i.generateDefaultMysqlAccount(version)...)
		default:
			// 默认按照mysql的初始化权限的方式
			initAccountSqls = i.generateDefaultMysqlAccount(version)
		}
		// 初始化数据库之后，reset master，标记binlog重头开始，避免同步干扰
		// 新安装db, avoid == false, 表示需要做 reset
		if !i.AvoidReset {
			initAccountSqls = append(initAccountSqls, "reset master;")
		}

		if _, err := dbWork.ExecMore(initAccountSqls); err != nil {
			logger.Error("flush privileges failed for %d %v", port, err)
			return err
		}
	}
	logger.Info("flush privileges successfully")
	return nil
}

// CheckTimeZoneSetting 安装mysql实例之前增加对时区校验，如果mysql的设置时区和机器系统设置的不一致，则不允许安装
func (i *InstallMySQLComp) CheckTimeZoneSetting() (err error) {
	timeZoneKeyName := "default_time_zone"
	execCmd := "date +%:z"
	output, err := osutil.ExecShellCommand(false, execCmd)
	if err != nil {
		logger.Error("exec get date script failed %s", err.Error())
		return err
	}
	i.TimeZone = osutil.CleanExecShellOutput(output)
	for _, port := range i.InsPorts {
		instanceTimeZone, err := i.MyCnfTpls[port].GetMysqldKeyVaule(timeZoneKeyName)
		if err != nil {
			logger.Error("exec get instance config [%d] default_time_zone failed %s", port, err.Error())
			return err
		}
		// 如果传入参数没有设置到default_time_zone参数，mysql走默认值SYSTEM，则这里输出warning日志，但是允许安装
		if instanceTimeZone == "" {
			// 如果第一次查不到，则转换中划线查询一次
			instanceTimeZone, err = i.MyCnfTpls[port].GetMysqldKeyVaule(strings.ReplaceAll(timeZoneKeyName, "_", "-"))
			if err != nil {
				logger.Error("exec get instance config [%d] default_time_zone failed %s", port, err.Error())
				return err
			}
			if instanceTimeZone == "" {
				logger.Warn("[%d] default_time_zone cannot find a value, it is recommended to set a specific value", port)
				continue
			}
		}
		// 如果系统和实例配置不一致,且mysql实例设置不是SYSTEM，则退出
		if i.TimeZone != instanceTimeZone && instanceTimeZone != "SYSTEM" {
			return fmt.Errorf(
				"the time zone is inconsistent with the configuration of the operating system and mysqld[%d], check", port)
		}
	}
	return nil
}

// InstallRplSemiSyncPlugin 安装实例支持半同步复制插件（目前只有spider ctl实例需要）
func (i *InstallMySQLComp) InstallRplSemiSyncPlugin() (err error) {
	var execSQLs []string
	execSQLs = append(execSQLs, "INSTALL PLUGIN rpl_semi_sync_master SONAME 'semisync_master.so';")
	execSQLs = append(execSQLs, "INSTALL PLUGIN rpl_semi_sync_slave SONAME 'semisync_slave.so';")
	logger.Info("installing rpl_semi_sync plugin...")

	for _, port := range i.InsPorts {
		// 连接本地实例的db（
		dbConn, err := native.InsObject{
			Host: i.Params.Host,
			Port: port,
			User: i.GeneralParam.RuntimeAccountParam.AdminUser,
			Pwd:  i.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.Conn()
		if err != nil {
			logger.Error("Connect %d failed:%s", port, err.Error())
			return err
		}
		if _, err := dbConn.ExecMore(execSQLs); err != nil {
			logger.Error("install plugin failed:[%s]", err.Error())
			return err
		}
	}
	return nil
}

// DecompressTdbctlPkg 针对mysql-tdbctl的场景，解压并生成新的目录作为tdbctl运行目录
// mysql 安装包可能有 .tar.gz  .tar.xz 两种格式
func (i *InstallMySQLComp) DecompressTdbctlPkg() (err error) {
	if err = os.Chdir(i.InstallDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InstallDir, err)
	}
	// 判断 /usr/local/tdbctl 目录是否已经存在,如果存在则删除掉
	if cmutil.FileExists(i.TdbctlInstallDir) {
		if _, err = osutil.ExecShellCommand(false, "rm -r "+i.TdbctlInstallDir); err != nil {
			logger.Error("rm -r %s error: %w", i.TdbctlInstallDir, err)
			return err
		}
	}

	tdbctlBinaryFile := i.Params.Medium.GePkgBaseName()

	// 判断 tdbctl安装目录是否已经存在,如果存在则删除掉
	if cmutil.FileExists(tdbctlBinaryFile) {
		if _, err = osutil.ExecShellCommand(false, "rm -r "+tdbctlBinaryFile); err != nil {
			logger.Error("rm -r %s error: %w", tdbctlBinaryFile, err)
			return err
		}
	}

	pkgAbPath := i.Params.Medium.GetAbsolutePath()
	if output, ierr := osutil.ExecShellCommand(
		false,
		fmt.Sprintf("mkdir %s && tar -xf %s -C %s --strip-components 1 ", tdbctlBinaryFile, pkgAbPath,
			tdbctlBinaryFile)); ierr != nil {
		logger.Error("tar -xf %s error:%s,%s", pkgAbPath, output, ierr.Error())
		return ierr
	}

	extraCmd := fmt.Sprintf("ln -sf %s %s && chown -R mysql mysql*", tdbctlBinaryFile, i.TdbctlInstallDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	logger.Info("mysql binary directory: %s", tdbctlBinaryFile)
	if _, err := os.Stat(i.TdbctlInstallDir); err != nil {
		logger.Error("%s check failed, %v", i.TdbctlInstallDir, err)
		return err
	}
	logger.Info("decompress mysql pkg successfully")
	return nil
}

// TdbctlStartup TODO
/**
 * @description: 启动mysql-tdbctl实例 会重试连接判断是否启动成功
 * @return {*}
 */
func (i *InstallMySQLComp) TdbctlStartup() (err error) {
	if err = osutil.ClearTcpRecycle(); err != nil {
		err = fmt.Errorf("clear tcp recycle failed, err: %w", err)
		logger.Warn("startup, %s", err.Error())
	}
	for _, port := range i.InsPorts {
		logger.Info("will start %d", port)
		s := computil.StartMySQLParam{
			MediaDir:      i.TdbctlInstallDir,
			MyCnfName:     util.GetMyCnfFileName(port),
			MySQLUser:     i.WorkUser,     // "root",
			MySQLPwd:      i.WorkPassword, // "",
			Socket:        i.InsSockets[port],
			SkipSlaveFlag: false,
		}
		pid, err := s.StartMysqlInstance()
		if err != nil {
			logger.Error("start %d failed err: %s", port, err.Error())
			return err
		}
		i.RollBackContext.AddKillProcess(pid)
	}
	return nil
}

// generateDefaultSpiderAccount TODO
/**
 * @description:  spider专属生成初始化默认mysql 账户sql
 * @receiver {string} realVersion: mysql 实际版本
 * @return {*}
 */
func (i *InstallMySQLComp) generateDefaultSpiderAccount(realVersion string) (initAccountsql []string) {
	initAccountsql = i.getSuperUserAccountForSpider()
	runp := i.GeneralParam.RuntimeAccountParam
	var privPairs []components.MySQLAccountPrivs
	privPairs = append(privPairs, runp.MySQLAdminAccount.GetAccountPrivs(i.Params.Host))
	// 这里做一个处理，传入的AdminUser 不一定是真正的ADMIN账号，如果不是则手动添加一个,保证新实例有ADMIN账号
	if runp.AdminUser != "ADMIN" {
		privPairs = append(privPairs, components.MySQLAdminAccount{
			AdminUser: "ADMIN",
			AdminPwd:  runp.AdminPwd,
		}.GetAccountPrivs(i.Params.Host))

	}
	privPairs = append(privPairs, runp.MySQLMonitorAccessAllAccount.GetAccountPrivs())
	privPairs = append(privPairs, runp.MySQLMonitorAccount.GetAccountPrivs(i.Params.Host))
	privPairs = append(privPairs, runp.MySQLYwAccount.GetAccountPrivs())
	privPairs = append(privPairs, runp.MySQLDbBackupAccount.GetAccountPrivs(realVersion, i.Params.Host))
	for _, v := range privPairs {
		initAccountsql = append(initAccountsql, v.GenerateInitSql(realVersion)...)
	}
	if cmutil.MySQLVersionParse(realVersion) <= cmutil.MySQLVersionParse("5.6") {
		s := `alter table mysql.general_log change thread_id thread_id bigint(21) unsigned NOT NULL;`
		initAccountsql = append(initAccountsql, s)
	}
	// 不知道这里为什么执行不了source命令，暂时用执行shell命令代替
	// initAccountsql = append(initAccountsql, fmt.Sprintf("source %s/scripts/install_spider.sql;", i.MysqlInstallDir))
	initAccountsql = append(initAccountsql, "delete from mysql.user where user='root' or user='';")
	initAccountsql = append(initAccountsql, "update mysql.db set Insert_priv = 'Y' where db = 'test';")
	initAccountsql = append(initAccountsql, "flush privileges;")
	return
}

// getSuperUserAccountForSpider TODO
/**
 * @description: 为spider创建DRS、DBHA服务访问的账号白名单
 * @return {*}
 */
func (i *InstallMySQLComp) getSuperUserAccountForSpider() (initAccountsql []string) {
	for _, host := range i.Params.SuperAccount.AccessHosts {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf("GRANT ALL PRIVILEGES ON *.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION;",
				i.Params.SuperAccount.User, host, i.Params.SuperAccount.Pwd))
	}
	for _, host := range i.Params.DBHAAccount.AccessHosts {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(
				"GRANT RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW "+
					"ON *.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION;",
				i.Params.DBHAAccount.User, host, i.Params.DBHAAccount.Pwd))
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(
				"GRANT SELECT ON mysql.servers TO '%s'@'%s' ;", i.Params.DBHAAccount.User, host))
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(
				" GRANT SELECT, INSERT, DELETE ON `infodba_schema`.* TO '%s'@'%s';",
				i.Params.DBHAAccount.User, host))
	}
	for _, host := range i.Params.WEBCONSOLERSAccount.AccessHosts {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(`GRANT SELECT, RELOAD, PROCESS, SHOW DATABASES ON *.* TO '%s'@'%s' IDENTIFIED BY '%s';`,
				i.Params.WEBCONSOLERSAccount.User, host, i.Params.WEBCONSOLERSAccount.Pwd))
	}
	for _, host := range i.Params.PartitionYWAccount.AccessHosts {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(
				`GRANT SELECT, INSERT, UPDATE, DELETE, 
								CREATE, DROP, ALTER, TRIGGER, 
								PROCESS, SUPER, REPLICATION SLAVE ON *.* TO '%s'@'%s' IDENTIFIED BY '%s';`,
				i.Params.PartitionYWAccount.User, host, i.Params.PartitionYWAccount.Pwd,
			),
		)
	}
	return initAccountsql
}

func (i *InstallMySQLComp) createSpiderTable(socket string) (err error) {
	return mysqlutil.ExecuteSqlAtLocal{
		User:     i.WorkUser,     // "root",
		Password: i.WorkPassword, // "",
		Socket:   socket,
		Charset:  i.Params.CharSet,
	}.ExecuteSqlByMySQLClientOne(path.Join(i.MysqlInstallDir, "scripts/install_spider.sql"), "", true)
}

// CreateExporterCnf 根据mysql部署端口生成对应的exporter配置文件
// 回档也会调用 install_mysql，但可能不会 install_monitor，为了避免健康误报，这个 install_mysql 阶段也渲染 exporter cnf
func (i *InstallMySQLComp) CreateExporterCnf() (err error) {
	for _, port := range i.InsPorts {
		exporterConfigPath := filepath.Join(
			"/etc",
			fmt.Sprintf("exporter_%d.cnf", port),
		)

		err = util.CreateExporterConf(
			exporterConfigPath,
			i.Params.Host,
			port,
			i.GeneralParam.RuntimeAccountParam.MonitorUser,
			i.GeneralParam.RuntimeAccountParam.MonitorPwd,
		)
		if err != nil {
			logger.Error(err.Error())
			return err
		}

		_, err = osutil.ExecShellCommand(
			false,
			fmt.Sprintf("chown mysql %s", exporterConfigPath),
		)
		if err != nil {
			logger.Error(err.Error())
			return err
		}
	}

	return nil
}
