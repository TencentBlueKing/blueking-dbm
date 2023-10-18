package mysql

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"regexp"
	"strconv"
	"strings"
	"text/template"
	"time"

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
	installMySQLConfig `json:"-"`
	RollBackContext    rollback.RollBackObjects `json:"-"`
	TimeZone           string
}

// InstallMySQLParams TODO
type InstallMySQLParams struct {
	components.Medium
	// map[port]my.cnf
	MyCnfConfigs json.RawMessage `json:"mycnf_configs"  validate:"required" `
	// MySQLVerion 只需5.6 5.7 这样的大版本号
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
	SpiderAutoIncrModeMap    json.RawMessage   `json:"spider_auto_incr_mode_map"`
	AllowDiskFileSystemTypes []string
}

// InitDirs TODO
type InitDirs = []string

// Port TODO
type Port = int
type socket = string

// SpiderAutoIncrModeValue TODO
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
			MyCnfConfigs: []byte(`{
							"20000":{
								"client":{"port": "{{mysqld.port}}" },
								"mysql":{"socket": "{{mysqld.datadir}}/mysql.sock" },
								"mysqld":{"binlog_format": "ROW","innodb_io_capacity": "1000","innodb_read_io_threads": "8"}},
							"20001":{
								"client":{"port": "{{mysqld.port}}"},
								"mysql":{"socket": "{{mysqld.datadir}}/mysql.sock"},
								"mysqld":{"binlog_format": "ROW","innodb_io_capacity": "2000","innodb_read_io_threads": "10"}}}`),
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
	if err := i.initMySQLInstanceMem(); err != nil {
		return err
	}
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

	// 反序列化mycnf 配置
	var mycnfs map[Port]json.RawMessage
	if err = json.Unmarshal([]byte(i.Params.MyCnfConfigs), &mycnfs); err != nil {
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
		cnftpl, err := util.NewMyCnfObject(mycnf, "tpl")
		if err != nil {
			logger.Error("初始化mycnf ini 模版:%s", err.Error())
			return err
		}
		i.MyCnfTpls[port] = cnftpl
	}

	// 如果SpiderAutoIncrModeMap有传入，则渲染
	if i.Params.SpiderAutoIncrModeMap != nil {
		i.SpiderAutoIncrModeMap = make(map[int]SpiderAutoIncrModeValue)
		if err = json.Unmarshal([]byte(i.Params.SpiderAutoIncrModeMap), &i.SpiderAutoIncrModeMap); err != nil {
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
	i.Checkfunc = append(i.Checkfunc, i.Params.Medium.Check)
	i.Checkfunc = append(i.Checkfunc, i.precheckFilesystemType)
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
	mountInfo := osutil.GetMountPathInfo()
	for _, key := range util.UniqueStrings([]string{i.DataRootPath, i.LogRootPath}) {
		if v, exist := mountInfo[key]; exist {
			logger.Info("%s : %s", key, v.FileSystemType)
			if !util.StringsHas(i.Params.AllowDiskFileSystemTypes, v.FileSystemType) {
				return fmt.Errorf("The %s,Filesystem is %s,is not allowed", key, v.FileSystemType)
			}
		} else {
			return fmt.Errorf("The %s Not Found Filesystem Type", key)
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
		cnf, err := util.LoadMyCnfForFile(util.GetMyCnfFileName(port))
		if err != nil {
			return err
		}
		if err := cnf.GetInitDirItemTpl(initDirTpls); err != nil {
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
		if err = i.MyCnfTpls[port].SafeSaveFile(false); err != nil {
			logger.Error("保存模版文件失败:%s", err.Error())
			return err
		}
		// 防止过快读取到的是空文件
		if err = util.Retry(util.RetryConfig{Times: 3, DelayTime: 100 * time.Millisecond}, func() error {
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
		defer f.Close()
		if err := tmpl.Execute(f, i.RenderConfigs[port]); err != nil {
			return err
		}
		if _, err = osutil.ExecShellCommand(false, fmt.Sprintf("chown -R mysql %s", cnf)); err != nil {
			logger.Error("chown -R mysql %s %s", cnf, err.Error())
			return err
		}
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
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar -xf %s", pkgAbPath)); err != nil {
		logger.Error("tar -xf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
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
		var output string
		myCnf := util.GetMyCnfFileName(port)
		initialLogFile := fmt.Sprintf("/tmp/install_mysql_%d.log", port)

		// mysql5.7.18以下版本或者spider版本的初始化命令
		initialMysql = fmt.Sprintf(
			"su - mysql -c \"cd /usr/local/mysql && ./scripts/mysql_install_db --defaults-file=%s --user=mysql --force &>%s\"",
			myCnf, initialLogFile)

		// mysql5.7.18以上的版本
		if mysqlutil.MySQLVersionParse(i.Params.MysqlVersion) >= mysqlutil.MySQLVersionParse("5.7.18") &&
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

		if output, err = osutil.ExecShellCommand(isSudo, initialMysql); err != nil {
			logger.Error("%s execute failed, %s", initialMysql, output)
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

// Startup TODO
/**
 * @description: 启动mysqld实例 会重试连接判断是否启动成功
 * @return {*}
 */
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
			MySQLUser:     "root",
			MySQLPwd:      "",
			Socket:        i.InsSockets[port],
			SkipSlaveFlag: false,
		}
		pid, err := s.StartMysqlInstance()
		if err != nil {
			logger.Error("start %d faild err: %s", port, err.Error())
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
 */
func (i *InstallMySQLComp) generateDefaultMysqlAccount(realVersion string) (initAccountsql []string) {

	initAccountsql = append(i.Params.SuperAccount.GetSuperUserAccount(realVersion), i.Params.DBHAAccount.GetDBHAAccount(
		realVersion)...)

	runp := i.GeneralParam.RuntimeAccountParam
	privParis := []components.MySQLAccountPrivs{}
	privParis = append(privParis, runp.MySQLAdminAccount.GetAccountPrivs(i.Params.Host))
	// 这里做一个处理，传入的AdminUser 不一定是真正的ADMIN账号，如果不是则手动添加一个,保证新实例有ADMIN账号
	if runp.AdminUser != "ADMIN" {
		privParis = append(privParis, components.MySQLAdminAccount{
			AdminUser: "ADMIN",
			AdminPwd:  runp.AdminPwd,
		}.GetAccountPrivs(i.Params.Host))

	}
	privParis = append(privParis, runp.MySQLMonitorAccessAllAccount.GetAccountPrivs())
	privParis = append(privParis, runp.MySQLMonitorAccount.GetAccountPrivs(i.Params.Host))
	privParis = append(privParis, runp.MySQLYwAccount.GetAccountPrivs())
	for _, v := range privParis {
		initAccountsql = append(initAccountsql, v.GenerateInitSql(realVersion)...)
	}
	if mysqlutil.MySQLVersionParse(realVersion) >= mysqlutil.MySQLVersionParse("5.7.18") {
		s :=
			`INSERT INTO mysql.db(Host,Db,User,Select_priv,Insert_priv,Update_priv,Delete_priv,Create_priv,Drop_priv,
                     Grant_priv,References_priv,Index_priv,Alter_priv,Create_tmp_table_priv,Lock_tables_priv,
                     Create_view_priv,Show_view_priv,Create_routine_priv,Alter_routine_priv,Execute_priv,
                     Event_priv,Trigger_priv)
VALUES ('%','test','','Y','Y','Y','Y','Y','Y','N','Y','Y','Y','Y','Y','Y','Y','Y','N','N','Y','Y');`
		initAccountsql = append(initAccountsql, s)
	} else if mysqlutil.MySQLVersionParse(i.Params.MysqlVersion) <= mysqlutil.MySQLVersionParse("5.6") {
		s := `alter table mysql.general_log change thread_id thread_id bigint(21) unsigned NOT NULL;`
		initAccountsql = append(initAccountsql, s)
	}
	initAccountsql = append(initAccountsql, "delete from mysql.user where user='root' or user='';")
	initAccountsql = append(initAccountsql, "update mysql.db set Insert_priv = 'Y' where db = 'test';")
	initAccountsql = append(initAccountsql, "flush privileges;")
	return
}

// AdditionalAccount  额外账户
type AdditionalAccount struct {
	User        string   `json:"user" validate:"required"`
	Pwd         string   `json:"pwd"  validate:"required"`
	AccessHosts []string `json:"access_hosts"`
}

// GetSuperUserAccount TODO
func (a *AdditionalAccount) GetSuperUserAccount(realVersion string) (initAccountsql []string) {
	for _, host := range cmutil.RemoveDuplicate(a.AccessHosts) {
		if mysqlutil.MySQLVersionParse(realVersion) >= mysqlutil.MySQLVersionParse("5.7.18") {
			initAccountsql = append(initAccountsql,
				fmt.Sprintf("CREATE USER '%s'@'%s' IDENTIFIED WITH mysql_native_password BY '%s' ;",
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

// GetDBHAAccount TODO
// 获取生成DHBA-GM访问账号的生成语句
func (a *AdditionalAccount) GetDBHAAccount(realVersion string) (initAccountsql []string) {
	for _, host := range cmutil.RemoveDuplicate(a.AccessHosts) {
		if mysqlutil.MySQLVersionParse(realVersion) >= mysqlutil.MySQLVersionParse("5.7.18") {
			initAccountsql = append(initAccountsql,
				fmt.Sprintf("CREATE USER '%s'@'%s' IDENTIFIED WITH mysql_native_password BY '%s' ;",
					a.User, host, a.Pwd))
			initAccountsql = append(initAccountsql, fmt.Sprintf(
				"GRANT RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW "+
					"ON *.* TO '%s'@'%s' WITH GRANT OPTION ;",
				a.User, host))
		} else {
			initAccountsql = append(initAccountsql,
				fmt.Sprintf(
					"GRANT RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW "+
						"ON *.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION ;",
					a.User, host, a.Pwd))
		}
	}
	return
}

// InitDefaultPrivAndSchema TODO
/**
 * @description: 执行初始化默认库表语句&初始化默认账户sql
 * @return {*}
 */
func (i *InstallMySQLComp) InitDefaultPrivAndSchema() (err error) {
	var bsql []byte
	var initSQLs []string

	// 拼接tdbctl session级命令，初始化session设置tc_admin=0
	if i.Params.GetPkgTypeName() == cst.PkgTypeTdbctl {
		initSQLs = append(initSQLs, "set tc_admin = 0;")
	}

	if bsql, err = staticembed.DefaultSysSchemaSQL.ReadFile(staticembed.DefaultSysSchemaSQLFileName); err != nil {
		logger.Error("读取嵌入文件%s失败", staticembed.DefaultSysSchemaSQLFileName)
		return err
	}
	for _, value := range strings.SplitAfterN(string(bsql), ";", -1) {
		if !regexp.MustCompile(`^\\s*$`).MatchString(value) {
			initSQLs = append(initSQLs, value)
		}
	}
	// 剔除最后一个空字符，spilts 会多分割出一个空字符
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
		var dbWork *native.DbWorker
		if dbWork, err = native.NewDbWorker(native.DsnBySocket(i.InsSockets[port], "root", "")); err != nil {
			logger.Error("connenct by %s failed,err:%s", port, err.Error())
			return err
		}

		// 初始化schema
		if _, err := dbWork.ExecMore(initSQLs); err != nil {
			logger.Error("flush privileges failed %v", err)
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
			if err := i.create_spider_table(i.InsSockets[port]); err != nil {
				return err
			}
			initAccountSqls = i.generateDefaultSpiderAccount(version)
		case strings.Contains(version, "tdbctl"):
			// 对tdbctl 初始化权限
			initAccountSqls = append(initAccountSqls, "set tc_admin = 0;")
			initAccountSqls = append(initAccountSqls, i.generateDefaultMysqlAccount(version)...)
		default:
			// 默认按照mysql的初始化权限的方式
			initAccountSqls = i.generateDefaultMysqlAccount(version)

		}
		// 初始化数据库之后，reset master，标记binlog重头开始，避免同步干扰
		initAccountSqls = append(initAccountSqls, "reset master;")

		if _, err := dbWork.ExecMore(initAccountSqls); err != nil {
			logger.Error("flush privileges failed %v", err)
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
				"The time zone is inconsistent with the configuration of the operating system and mysqld[%d], check", port)
		}
	}
	return nil
}

// CreateExporterCnf 根据mysql部署端口生成对应的exporter配置文件
func (i *InstallMySQLComp) CreateExporterCnf() (err error) {
	for _, port := range i.InsPorts {
		exporterConfName := fmt.Sprintf("/etc/exporter_%d.cnf", port)
		if err = util.CreateExporterConf(
			exporterConfName,
			i.Params.Host,
			strconv.Itoa(port),
			i.GeneralParam.RuntimeAccountParam.MonitorUser,
			i.GeneralParam.RuntimeAccountParam.MonitorPwd,
		); err != nil {
			logger.Error("create exporter conf err : %s", err.Error())
			return err
		}
		// /etc/exporter_xxx.args is used to set mysqld_exporter collector args
		exporterArgsName := fmt.Sprintf("/etc/exporter_%d.args", port)
		if err = util.CreateMysqlExporterArgs(exporterArgsName, i.Params.GetPkgTypeName(), port); err != nil {
			logger.Error("create exporter collector args err : %s", err.Error())
			return err
		}
		if _, err = osutil.ExecShellCommand(false,
			fmt.Sprintf("chown -R mysql %s %s", exporterConfName, exporterArgsName)); err != nil {
			logger.Error("chown -R mysql %s %s : %s", exporterConfName, exporterArgsName, err.Error())
			return err
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
			logger.Error("isntall plugin failed:[%s]", err.Error())
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
	if output, err := osutil.ExecShellCommand(
		false,
		fmt.Sprintf("mkdir %s && tar -xf %s -C %s --strip-components 1 ", tdbctlBinaryFile, pkgAbPath,
			tdbctlBinaryFile)); err != nil {
		logger.Error("tar -xf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
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
			MySQLUser:     "root",
			MySQLPwd:      "",
			Socket:        i.InsSockets[port],
			SkipSlaveFlag: false,
		}
		pid, err := s.StartMysqlInstance()
		if err != nil {
			logger.Error("start %d faild err: %s", port, err.Error())
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
	privParis := []components.MySQLAccountPrivs{}
	privParis = append(privParis, runp.MySQLAdminAccount.GetAccountPrivs(i.Params.Host))
	// 这里做一个处理，传入的AdminUser 不一定是真正的ADMIN账号，如果不是则手动添加一个,保证新实例有ADMIN账号
	if runp.AdminUser != "ADMIN" {
		privParis = append(privParis, components.MySQLAdminAccount{
			AdminUser: "ADMIN",
			AdminPwd:  runp.AdminPwd,
		}.GetAccountPrivs(i.Params.Host))

	}
	privParis = append(privParis, runp.MySQLMonitorAccessAllAccount.GetAccountPrivs())
	privParis = append(privParis, runp.MySQLMonitorAccount.GetAccountPrivs(i.Params.Host))
	privParis = append(privParis, runp.MySQLYwAccount.GetAccountPrivs())
	for _, v := range privParis {
		initAccountsql = append(initAccountsql, v.GenerateInitSql(realVersion)...)
	}
	if mysqlutil.MySQLVersionParse(realVersion) <= mysqlutil.MySQLVersionParse("5.6") {
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
			fmt.Sprintf("GRANT ALL PRIVILEGES ON *.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION ;",
				i.Params.SuperAccount.User, host, i.Params.SuperAccount.Pwd))
	}
	for _, host := range i.Params.DBHAAccount.AccessHosts {
		initAccountsql = append(initAccountsql,
			fmt.Sprintf(
				"GRANT RELOAD, PROCESS, SHOW DATABASES, SUPER, REPLICATION CLIENT, SHOW VIEW "+
					"ON *.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION ;",
				i.Params.DBHAAccount.User, host, i.Params.DBHAAccount.Pwd))
	}
	return
}

func (i *InstallMySQLComp) create_spider_table(socket string) (err error) {
	return mysqlutil.ExecuteSqlAtLocal{
		User:     "root",
		Password: "",
		Socket:   socket,
		Charset:  i.Params.CharSet,
	}.ExcuteSqlByMySQLClientOne(path.Join(i.MysqlInstallDir, "scripts/install_spider.sql"), "")
}
