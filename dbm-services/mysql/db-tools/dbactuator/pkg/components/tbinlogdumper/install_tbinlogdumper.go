package tbinlogdumper

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"encoding/json"
	"fmt"
	"html/template"
	"os"
	"path"
	"regexp"
	"strconv"
	"time"

	"github.com/golang/glog"
	"github.com/pkg/errors"
)

// InstallTbinlogDumperComp TODO
// tbinlogdumper本质上是mysqld进程，可以继承一些方法
type InstallTbinlogDumperComp struct {
	RenderConfigs map[mysql.Port]renderDumperConfigs
	mysql.InstallMySQLComp
	DumperConfigs *DumperParams `json:"extend"`
}

// RenderDumperConfigs TODO
type DumperParams struct {
	DumperId uint64 `json:"dumper_id" validate:"required" `
	AreaName string `json:"area_name" validate:"required" `
}

// RenderDumperConfigs TODO
type renderDumperConfigs struct {
	Mysqld Mysqld
}

// Mysqld TODO
type Mysqld struct {
	Port               string `json:"port"`
	Basedir            string `json:"basedir"`
	Datadir            string `json:"datadir"`
	Logdir             string `json:"logdir"`
	CharacterSetServer string `json:"character_set_server"`
	BindAddress        string `json:"bind-address"`
	ServerId           uint64 `json:"server_id"`
	AreaName           string `json:"area_name"`
	Dumperid           uint64 `json:"dumper_id"`
}

// GetDumperDirName
// input "mysql-5.6.24-linux-x86_64-tbinlogdumper-2.14-gcs"
// output tbinlogdumper2.14
func GetDumperDirName(dumperVersion string) string {
	re := regexp.MustCompile(`(tbinlogdumper)-([\d]+)?.?([\d]+)?`)
	result := re.FindStringSubmatch(dumperVersion)
	if len(result) != 4 {
		glog.Errorf("parse dumper version failed:%s, %v", dumperVersion, result)
		return ""
	}
	return fmt.Sprintf("%s%s.%s", result[1], result[2], result[3])
}

func (i *InstallTbinlogDumperComp) InitDumperDefaultParam() error {
	dumperDirName := GetDumperDirName(i.Params.Medium.Pkg)
	i.InstallDir = cst.UsrLocal
	i.MysqlInstallDir = path.Join(cst.UsrLocal, dumperDirName)
	i.DataRootPath = cst.DumperDefaultDir
	i.LogRootPath = cst.DumperDefaultDir
	i.DefaultMysqlDataDirName = cst.DefaultMysqlDataBasePath
	i.DefaultMysqlLogDirName = cst.DefaultMysqlLogBasePath
	i.DataBaseDir = path.Join(cst.DumperDefaultDir, cst.DefaultMysqlDataBasePath)
	i.LogBaseDir = path.Join(cst.DumperDefaultDir, cst.DefaultMysqlLogBasePath)

	// 计算获取需要安装的ports
	i.InsPorts = i.Params.Ports
	i.MyCnfTpls = make(map[int]*util.CnfFile)

	// 反序列化mycnf 配置
	var mycnfs map[mysql.Port]json.RawMessage
	if err := json.Unmarshal([]byte(i.Params.MyCnfConfigs), &mycnfs); err != nil {
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
		if err := json.Unmarshal(cnfraw, &mycnf); err != nil {
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
	// 计算需要替换的参数配置
	if err := i.initInsReplaceConfigs(); err != nil {
		return err
	}

	i.Checkfunc = append(i.Checkfunc, i.Params.Medium.Check)
	i.Checkfunc = append(i.Checkfunc, i.precheckDir)
	i.Checkfunc = append(i.Checkfunc, i.precheckProcess)
	return nil
}

// precheckMysqlDir TODO
/*
	检查根路径下是已经存在tbinlogdumper相关的数据和日志目录
	eg:
	/data/idip_cache/mysqldata/{port}
	/data/idip_cache/mysqllog/{port}
*/
func (i *InstallTbinlogDumperComp) precheckDir() error {
	for _, port := range i.InsPorts {
		d := path.Join(i.DataBaseDir, strconv.Itoa(port))
		if osutil.FileExist(d) {
			return fmt.Errorf("%s 已经存在了", d)
		}
		l := path.Join(i.LogBaseDir, strconv.Itoa(port))
		if osutil.FileExist(l) {
			return fmt.Errorf("%s 已经存在了", l)
		}
	}
	return nil
}

// precheckProcess 判断机器是否已部署对应的进程
func (i *InstallTbinlogDumperComp) precheckProcess() (err error) {

	for _, port := range i.InsPorts {
		var output string
		var tbinlogDumperNum int

		checkCmd := fmt.Sprintf(
			"netstat -tnlp |grep -v grep|grep %d|wc -l",
			port,
		)
		if output, err = osutil.ExecShellCommand(false, checkCmd); err != nil {
			return errors.Wrap(err, "执行失败")
		}
		if tbinlogDumperNum, err = strconv.Atoi(osutil.CleanExecShellOutput(output)); err != nil {
			logger.Error("strconv.Atoi %s failed:%s", output, err.Error())
			return err
		}
		if tbinlogDumperNum > 0 {
			return errors.New(fmt.Sprintf(" listen [%d] have %d process running", port, tbinlogDumperNum))
		}
	}
	return nil

}

func (i *InstallTbinlogDumperComp) DumperInstall() (err error) {
	logger.Info("开始安装tbinlogdumper实例 ~  %v", i.InsPorts)
	var isSudo = mysqlutil.IsSudo()
	for _, port := range i.InsPorts {
		var initialMysql string
		var output string
		myCnf := util.GetMyCnfFileName(port)
		initialLogFile := fmt.Sprintf("/tmp/install_tbinlogdumper_%d.log", port)

		// mysql5.7.18以下版本初始化命令
		initialMysql = fmt.Sprintf(
			"su - mysql -c \"cd %s && ./scripts/mysql_install_db --defaults-file=%s --user=mysql --force &>%s\"",
			i.MysqlInstallDir, myCnf, initialLogFile)

		// mysql5.7.18以上的版本
		if mysqlutil.MySQLVersionParse(i.Params.MysqlVersion) >= mysqlutil.MySQLVersionParse("5.7.18") {
			initialMysql = fmt.Sprintf(
				"su - mysql -c \"cd %s && ./bin/mysqld --defaults-file=%s --initialize-insecure --user=mysql &>%s\"",
				i.MysqlInstallDir, myCnf, initialLogFile)
		}
		if output, err = osutil.ExecShellCommand(isSudo, initialMysql); err != nil {
			logger.Error("%s execute failed, %s", initialMysql, output)
			// 如果存在初始化的日志文件，才初始化错误的时间，将日志cat出来
			if osutil.FileExist(initialLogFile) {
				ldat, e := os.ReadFile(initialLogFile)
				if e != nil {
					logger.Warn("读取初始化tbinlogdumper日志失败%s", e.Error())
				} else {
					logger.Error("初始化tbinlogdumper失败日志： %s", string(ldat))
				}
			}
			return err
		}

		time.Sleep(5 * time.Second)
	}
	logger.Info("Init all mysqld successfully")
	return nil
}

func (i *InstallTbinlogDumperComp) initInsReplaceConfigs() error {
	i.RenderConfigs = make(map[int]renderDumperConfigs)
	i.InsInitDirs = make(map[int]mysql.InitDirs)
	i.InsSockets = make(map[int]string)
	for _, port := range i.InsPorts {
		insBaseDataDir := path.Join(i.DataBaseDir, strconv.Itoa(port))
		insBaseLogDir := path.Join(i.LogBaseDir, strconv.Itoa(port))
		serverId, err := mysqlutil.GenMysqlServerId(i.Params.Host, port)
		if err != nil {
			logger.Error("%s:%d generation serverId Failed %s", i.Params.Host, port, err.Error())
			return err
		}
		i.RenderConfigs[port] = renderDumperConfigs{Mysqld{
			Basedir:            i.MysqlInstallDir,
			Datadir:            insBaseDataDir,
			Logdir:             insBaseLogDir,
			ServerId:           serverId,
			Port:               strconv.Itoa(port),
			CharacterSetServer: i.Params.CharSet,
			BindAddress:        i.Params.Host,
			AreaName:           i.DumperConfigs.AreaName,
			Dumperid:           i.DumperConfigs.DumperId,
		}}

		i.InsInitDirs[port] = append(i.InsInitDirs[port], []string{insBaseDataDir, insBaseLogDir}...)
	}
	return nil
	//	return i.calInsInitDirs()
}

func (i *InstallTbinlogDumperComp) GenerateDumperMycnf() (err error) {
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
			return errors.WithMessage(err, "template ParseFiles failed")
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

// DecompressDumperPkg TODO
/**
 * @description:  校验、解压tbinlogdumper安装包,考虑需要支持追加部署的方式，怎解压需要判断机器是否对应的版本包
 * @return {*}
 */
func (i *InstallTbinlogDumperComp) DecompressDumperPkg() (err error) {
	if err = os.Chdir(i.InstallDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InstallDir, err)
	}
	// 判断 对应版本的安装目录是否已经存在,如果存在，则判断是否有对应版本的进程部署，如果没有则重建，有则沿用
	if cmutil.FileExists(i.MysqlInstallDir) {
		// 检查是否存在这个版本部署dumper进程
		err, result := i.isInstallDumperWithInstallDir()
		if err != nil {
			return err
		}
		if result {
			// 表示有对应版本的进程部署，如果无需执行下面逻辑，沿用这套二进制
			logger.Warn(
				"This version [%s] already has a corresponding deployment process on the machine",
				i.MysqlInstallDir,
			)
			return nil
		}

		// 如果没有对应进程部署，则重建使用传下来的版本
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

// isInstallDumperWithInstallDir 根据
func (i *InstallTbinlogDumperComp) isInstallDumperWithInstallDir() (err error, result bool) {
	var output string
	var dumperNum int
	checkCMD := fmt.Sprintf("ps -efwww|grep -w %s |grep -v grep | wc -l", i.MysqlInstallDir)

	if output, err = osutil.ExecShellCommand(false, checkCMD); err != nil {
		return errors.Wrap(err, fmt.Sprintf("执行失败[%s]", checkCMD)), false
	}
	if dumperNum, err = strconv.Atoi(osutil.CleanExecShellOutput(output)); err != nil {
		logger.Error("strconv.Atoi %s failed:%s", output, err.Error())
		return err, false
	}
	if dumperNum > 0 {
		return nil, true
	}
	return nil, false
}
