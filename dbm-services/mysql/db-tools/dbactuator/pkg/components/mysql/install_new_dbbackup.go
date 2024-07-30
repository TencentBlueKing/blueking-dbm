package mysql

import (
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
	"text/template"
	"time"

	"gopkg.in/ini.v1"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
)

// InstallNewDbBackupComp TODO
type InstallNewDbBackupComp struct {
	GeneralParam *components.GeneralParam
	Params       *InstallNewDbBackupParam
	runtimeContext
}

type logicBackupDataOption struct {
	// "grant,schema,data"
	DataSchemaGrant string `json:"DataSchemaGrant"`
}

// InstallNewDbBackupParam TODO
type InstallNewDbBackupParam struct {
	components.Medium
	// Configs BackupConfig
	Configs        map[string]map[string]string `json:"configs" validate:"required"`         // 模板配置
	Options        map[Port]BackupOptions       `json:"options" validate:"required"`         // 选项参数配置
	Host           string                       `json:"host"  validate:"required,ip"`        // 当前实例的主机地址
	Ports          []int                        `json:"ports" validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口
	Role           string                       `json:"role" validate:"required"`            // 当前主机安装的mysqld的角色
	ClusterType    string                       `json:"cluster_type"`
	BkBizId        int                          `json:"bk_biz_id" validate:"required"` // bkbizid
	BkCloudId      int                          `json:"bk_cloud_id"`                   // bk_cloud_id
	ClusterAddress map[Port]string              `json:"cluster_address"`               // cluster addresss
	ClusterId      map[Port]int                 `json:"cluster_id"`                    // cluster id
	ShardValue     map[Port]int                 `json:"shard_value"`                   // shard value for spider
	ExecUser       string                       `json:"exec_user"`                     // 执行Job的用户
	UntarOnly      bool                         `json:"untar_only"`                    // 只解压，不校验不渲染配置，不连接 db
}

type runtimeContext struct {
	installPath string                       // dbbackupInstallPath
	dbConn      map[Port]*native.DbWorker    // db连接池
	versionMap  map[Port]string              // 当前机器数据库实例版本
	renderCnf   map[Port]config.BackupConfig // 绝对不能改成指针数组

	backupOpt  map[Port]BackupOptions
	ignoreDbs  map[Port][]string
	ignoreTbls map[Port][]string
}

// BackupOptions TODO
type BackupOptions struct {
	BackupType  string `json:"BackupType" validate:"required"`
	CrontabTime string `json:"CrontabTime" validate:"required,crontabexpr"`
	IgnoreObjs  struct {
		// "mysql,test,db_infobase,information_schema,performance_schema,sys"
		IgnoreDatabases string `json:"ExcludeDatabases"`
		IgnoreTables    string `json:"ExcludeTables"`
	} `json:"Logical"`
	Master logicBackupDataOption `json:"Master" validate:"required"`
	Slave  logicBackupDataOption `json:"Slave"`
}

// Example TODO
func (i *InstallNewDbBackupComp) Example() interface{} {
	comp := InstallNewDbBackupComp{
		Params: &InstallNewDbBackupParam{
			Medium: components.Medium{
				Pkg:    "dbbackup-go.tar.gz",
				PkgMd5: "90e5be347c606218b055a61f990ecdf4",
			},
			Host:  "127.0.0.1",
			Ports: []int{20000, 20001},
			Options: map[Port]BackupOptions{
				20000: BackupOptions{
					CrontabTime: "09:00:00",
					BackupType:  "logical",
					Master:      logicBackupDataOption{DataSchemaGrant: "grant"},
					Slave:       logicBackupDataOption{DataSchemaGrant: "grant"},
				},
				20001: BackupOptions{
					BackupType: "physical",
				},
			},
			Configs: map[string]map[string]string{
				"Public": map[string]string{
					"BackupType":      "logical",
					"DataSchemaGrant": "all",
					"ClusterId":       "123",
					"BkBizId":         "456",
				},
				"LogicalBackup": {
					"Threads":       "4",
					"ChunkFilesize": "2048",
				},
				"PhysicalBackup": {
					"DefaultsFile": "/xx/yy/my.cnf.12006",
					"Throttle":     "100",
				},
			},
			Role:           "slave",
			ClusterAddress: map[Port]string{20000: "testdb1.xx.a1.db", 20001: "testdb2.xx.a1.db"},
			ClusterId:      map[Port]int{20000: 111, 20001: 112},
		},
	}
	return comp
}

// Init TODO
func (i *InstallNewDbBackupComp) Init() (err error) {
	i.Params.Role = strings.ToUpper(i.Params.Role)

	i.initBackupOptions()
	i.installPath = path.Join(cst.MYSQL_TOOL_INSTALL_PATH, cst.BackupDir)
	i.dbConn = make(map[int]*native.DbWorker) // not use
	i.versionMap = make(map[int]string)       // not use
	i.renderCnf = make(map[int]config.BackupConfig)
	if i.Params.UntarOnly {
		logger.Info("untar_only=true do not try to connect")
		return nil
	}
	for _, port := range i.Params.Ports {
		/*
			dbwork, err := native.InsObject{
				Host: i.Params.Host,
				Port: port,
				User: i.GeneralParam.RuntimeAccountParam.AdminUser,
				Pwd:  i.GeneralParam.RuntimeAccountParam.AdminPwd,
			}.Conn()
			if err != nil {
				return fmt.Errorf("init db conn %d failed err:%w", port, err)
			}
			i.dbConn[port] = dbwork
			version, err := dbwork.SelectVersion()
			if err != nil {
				return err
			}
			i.versionMap[port] = version
		*/
		if i.Params.Role == cst.BackupRoleSpiderMaster {
			tdbctlPort := mysqlcomm.GetTdbctlPortBySpider(port)
			tdbctlWork, err := native.InsObject{
				Host: i.Params.Host,
				Port: tdbctlPort,
				User: i.GeneralParam.RuntimeAccountParam.AdminUser,
				Pwd:  i.GeneralParam.RuntimeAccountParam.AdminPwd,
			}.Conn()
			if err != nil {
				return fmt.Errorf("init tdbcl conn %d failed:%w", tdbctlPort, err)
			}
			i.dbConn[tdbctlPort] = tdbctlWork
			version, err := tdbctlWork.SelectVersion()
			if err != nil {
				return err
			}
			i.versionMap[tdbctlPort] = version
		}
	}
	logger.Info("config %v", i.Params.Configs)
	return nil
}

func (i *InstallNewDbBackupComp) initBackupOptions() {
	i.backupOpt = i.Params.Options

	i.ignoreDbs = make(map[Port][]string)
	i.ignoreTbls = make(map[Port][]string)
	for _, port := range i.Params.Ports {
		opt, ok := i.Params.Options[port]
		if !ok {
			i.Params.Options[port] = BackupOptions{} // unknown
			continue
		}
		logger.Info("options %v", opt)
		var ignoreTbls, ignoreDbs []string
		ignoreDbs = strings.Split(opt.IgnoreObjs.IgnoreDatabases, ",")
		ignoreDbs = append(ignoreDbs, native.DBSys...)
		// 默认备份需要 infodba_schema 库
		ignoreDbs = cmutil.StringsRemove(ignoreDbs, native.INFODBA_SCHEMA)
		ignoreTbls = strings.Split(opt.IgnoreObjs.IgnoreTables, ",")

		i.ignoreDbs[port] = util.UniqueStrings(cmutil.RemoveEmpty(ignoreDbs))
		i.ignoreTbls[port] = util.UniqueStrings(cmutil.RemoveEmpty(ignoreTbls))
		if len(i.ignoreTbls[port]) <= 0 {
			i.ignoreTbls[port] = []string{"*"}
		}
		logger.Info("port %d ignore dbs %v", port, i.ignoreDbs[port])
		logger.Info("port %d ignore tables %v", port, i.ignoreTbls[port])
	}
}

func (i *InstallNewDbBackupComp) getInsDomainAddr(port int) string {
	if i.Params.ClusterAddress == nil {
		return ""
	}
	if len(i.Params.ClusterAddress) == 0 {
		return ""
	}
	if v, ok := i.Params.ClusterAddress[port]; ok {
		return v
	}
	return ""
}
func (i *InstallNewDbBackupComp) getInsClusterId(port int) int {
	if i.Params.ClusterId == nil {
		return 0
	}
	if len(i.Params.ClusterId) == 0 {
		return 0
	}
	if v, ok := i.Params.ClusterId[port]; ok {
		return v
	}
	return 0
}
func (i *InstallNewDbBackupComp) getInsShardValue(port int) int {
	if i.Params.ShardValue == nil {
		return 0
	}
	if len(i.Params.ShardValue) == 0 {
		return 0
	}
	if v, ok := i.Params.ShardValue[port]; ok {
		return v
	}
	return 0
}

// getInsHostCrontabTime 获取最大的时间，作为机器备份的开始时间
func (i *InstallNewDbBackupComp) getInsHostCrontabTime() string {
	cronTime := ""
	for _, opt := range i.Params.Options {
		if opt.CrontabTime > cronTime {
			cronTime = opt.CrontabTime
		}
	}
	return cronTime
}

// InitRenderData 初始化待渲染的配置变量 renderCnf[port]: backup_configs
func (i *InstallNewDbBackupComp) InitRenderData() (err error) {
	if i.Params.UntarOnly {
		logger.Info("untar_only=true do not need InitRenderData")
		return nil
	}

	bkuser := i.GeneralParam.RuntimeAccountParam.DbBackupUser
	bkpwd := i.GeneralParam.RuntimeAccountParam.DbBackupPwd

	for _, port := range i.Params.Ports {
		regexfunc, err := db_table_filter.BuildMydumperRegex([]string{"*"}, []string{"*"},
			i.ignoreDbs[port], i.ignoreTbls[port])
		if err != nil {
			return err
		}
		regexStr := regexfunc.TableFilterRegex()
		logger.Info("regexStr %v", regexStr)
		// 根据role 选择备份参数选项
		var dsg string
		switch i.Params.Role {
		case cst.BackupRoleMaster, cst.BackupRoleRepeater:
			dsg = i.backupOpt[port].Master.DataSchemaGrant
		case cst.BackupRoleSlave:
			dsg = i.backupOpt[port].Slave.DataSchemaGrant
		case cst.BackupRoleOrphan:
			// orphan 使用的是 tendbsingle Master.DataSchemaGrant
			dsg = i.backupOpt[port].Master.DataSchemaGrant
		case cst.BackupRoleSpiderMaster, cst.BackupRoleSpiderSlave, cst.BackupRoleSpiderMnt:
			// spider 只在 spider_master and tdbctl_master 上，备份schema,grant
			dsg = "schema,grant"
		default:
			return fmt.Errorf("未知的备份角色%s", i.Params.Role)
		}
		cfg := config.BackupConfig{
			Public: config.Public{
				MysqlHost:       i.Params.Host,
				MysqlPort:       port,
				MysqlUser:       bkuser,
				MysqlPasswd:     bkpwd,
				MysqlRole:       strings.ToLower(i.Params.Role),
				BkBizId:         i.Params.BkBizId,
				BkCloudId:       i.Params.BkCloudId,
				ClusterAddress:  i.getInsDomainAddr(port),
				ClusterId:       i.getInsClusterId(port),
				ShardValue:      i.getInsShardValue(port),
				BackupType:      i.backupOpt[port].BackupType,
				DataSchemaGrant: dsg,
			},
			BackupClient: config.BackupClient{},
			LogicalBackup: config.LogicalBackup{
				TableFilter: config.TableFilter{
					Regex: regexStr,
				},
			},
			PhysicalBackup: config.PhysicalBackup{
				DefaultsFile: util.GetMyCnfFileName(port),
			},
		}

		i.renderCnf[port] = cfg

		if i.Params.Role == cst.BackupRoleSpiderMaster {
			tdbctlPort := mysqlcomm.GetTdbctlPortBySpider(port)
			cfg.Public.MysqlPort = tdbctlPort
			cfg.Public.MysqlRole = cst.BackupRoleTdbctl
			cfg.PhysicalBackup.DefaultsFile = util.GetMyCnfFileName(tdbctlPort)
			i.renderCnf[tdbctlPort] = cfg
		}
	}
	return nil
}

// InitBackupDir 判断备份目录是否存在,不存在的话则创建
func (i *InstallNewDbBackupComp) InitBackupDir() (err error) {
	if i.Params.UntarOnly {
		logger.Info("untar_only=true do not need InitBackupDir")
		return nil
	}
	backupdir := i.Params.Configs["Public"]["BackupDir"]
	if _, err := os.Stat(backupdir); os.IsNotExist(err) {
		logger.Warn("backup dir %s is not exist. will make it", backupdir)
		cmd := fmt.Sprintf("mkdir -p %s", backupdir)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			return fmt.Errorf("execute [%s] get an error:%s,%w", cmd, output, err)
		}
	}
	cmd := fmt.Sprintf("chown -R mysql.mysql %s", backupdir)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		return fmt.Errorf("execute [%s] get an error:%s,%w", cmd, output, err)
	}
	return
}

// DecompressPkg TODO
func (i *InstallNewDbBackupComp) DecompressPkg() (err error) {
	if err = i.Params.Medium.Check(); err != nil {
		return err
	}
	cmd := fmt.Sprintf(
		"tar zxf %s -C %s && mkdir -p %s &&  chown -R mysql.mysql %s", i.Params.Medium.GetAbsolutePath(),
		path.Dir(i.installPath), filepath.Join(i.installPath, "logs"), i.installPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}

// InitBackupUserPriv 创建备份用户
// TODO 用户初始化考虑在部署 mysqld 的时候进行
func (i *InstallNewDbBackupComp) InitBackupUserPriv() (err error) {
	if i.Params.UntarOnly {
		logger.Info("untar_only=true do not need InitBackupUserPriv")
		return nil
	}
	for _, port := range i.Params.Ports {
		err := i.initPriv(port, false)
		if err != nil {
			return err
		}

		if i.Params.Role == cst.BackupRoleSpiderMaster {
			err := i.initPriv(mysqlcomm.GetTdbctlPortBySpider(port), true)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func (i *InstallNewDbBackupComp) initPriv(port int, isTdbCtl bool) (err error) {
	ver := i.versionMap[port]
	privs := i.GeneralParam.RuntimeAccountParam.MySQLDbBackupAccount.GetAccountPrivs(ver, i.Params.Host)
	var sqls []string
	if isTdbCtl {
		logger.Info("tdbctl port %d need tc_admin=0, binlog_format=off", port)
		sqls = append(sqls, "set session tc_admin=0;", "set session sql_log_bin=off;")
	}
	sqls = append(sqls, privs.GenerateInitSql(ver)...)
	dc, ok := i.dbConn[port]
	if !ok {
		return fmt.Errorf("from dbConns 获取%d连接失败", port)
	}
	if _, err = dc.ExecMore(sqls); err != nil {
		logger.Error("初始化备份账户失败%s", err.Error())
		return
	}
	return err
}

// GenerateDbbackupConfig TODO
func (i *InstallNewDbBackupComp) GenerateDbbackupConfig() (err error) {
	if i.Params.UntarOnly {
		logger.Info("untar_only=true do not need GenerateDbbackupConfig")
		return nil
	}
	// 先渲染模版配置文件
	templatePath := path.Join(i.installPath, fmt.Sprintf("%s.tpl", cst.BackupFile))
	if err := i.saveTplConfigfile(templatePath); err != nil {
		return err
	}

	cnfTemp, err := template.ParseFiles(templatePath)
	if err != nil {
		return errors.WithMessage(err, "template ParseFiles failed")
	}

	for _, port := range i.Params.Ports {
		_, err := i.writeCnf(port, cnfTemp)
		if err != nil {
			return err
		}

		if i.Params.Role == cst.BackupRoleSpiderMaster {
			cnfPath, err := i.writeCnf(mysqlcomm.GetTdbctlPortBySpider(port), cnfTemp)
			if err != nil {
				return err
			}

			tdbCtlCnfIni, err := ini.Load(cnfPath)
			if err != nil {
				return err
			}

			var tdbCtlCnf config.BackupConfig
			err = tdbCtlCnfIni.MapTo(&tdbCtlCnf)
			if err != nil {
				return err
			}

			tdbCtlCnf.LogicalBackup.DefaultsFile = filepath.Join(i.installPath, "mydumper_for_tdbctl.cnf")
			err = tdbCtlCnfIni.ReflectFrom(&tdbCtlCnf)
			if err != nil {
				return err
			}
			err = tdbCtlCnfIni.SaveTo(cnfPath)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

func (i *InstallNewDbBackupComp) writeCnf(port int, tpl *template.Template) (cnfPath string, err error) {
	cnfPath = path.Join(i.installPath, cst.GetNewConfigByPort(port))
	cnfFile, err := os.OpenFile(cnfPath, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755) // os.Create(cnfPath)
	if err != nil {
		return "", errors.WithMessage(err, fmt.Sprintf("create %s failed", cnfPath))
	}
	defer func() {
		_ = cnfFile.Close()
	}()

	if data, ok := i.renderCnf[port]; ok {
		if err = tpl.Execute(cnfFile, data); err != nil {
			return "", errors.WithMessage(err, "渲染%d的备份配置文件失败")
		}
	} else {
		return "", fmt.Errorf("not found %d render data", port)
	}

	return cnfPath, nil
}

// ChownGroup 更改安装目录的所属组
func (i *InstallNewDbBackupComp) ChownGroup() (err error) {
	// run dbbackup migrateold
	_, errStr, err := cmutil.ExecCommandReturnBytes(false,
		i.installPath,
		filepath.Join(i.installPath, "dbbackup"),
		"migrateold")
	if err != nil {
		logger.Info("run dbbackup migrateold failed: %s", errStr)
		//we ignore this error
	} else {
		logger.Info("run dbbackup migrateold success")
	}

	cmd := fmt.Sprintf(
		" chown -R mysql.mysql %s ; chmod +x %s/*.sh ; chmod +x %s/dbbackup",
		path.Dir(i.installPath), i.installPath, i.installPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}

// saveTplConfigfile 渲染ini模板
// todo: 将 Configs 转换成 struct，再把 struct 转换成 ini. 方便渲染 Public.EncryptOpt
func (i *InstallNewDbBackupComp) saveTplConfigfile(tmpl string) (err error) {
	f, err := os.OpenFile(tmpl, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755)
	if err != nil {
		return errors.WithMessage(err, "新建文件失败")
	}
	defer func() {
		_ = f.Close()
	}()
	var encryptOpt = make(map[string]string)
	var encryptOptPrefix = "EncryptOpt"
	for key, val := range i.Params.Configs {
		_, err := fmt.Fprintf(f, "[%s]\n", key)
		if err != nil {
			return errors.WithMessagef(err, "写配置模版 %s 失败", key)
		}
		for k, v := range val {
			if strings.HasPrefix(k, encryptOptPrefix+".") {
				encryptOpt[strings.TrimPrefix(k, encryptOptPrefix+".")] = v
				continue
			}
			_, err := fmt.Fprintf(f, "%s\t=\t%s\n", k, v)
			if err != nil {
				return errors.WithMessagef(err, "写配置模版 %s, %s 失败", k, v)
			}
		}
		fmt.Fprintf(f, "\n")
	}
	if len(encryptOpt) > 0 {
		fmt.Fprintf(f, "[%s]\n", encryptOptPrefix)
		for k, v := range encryptOpt {
			fmt.Fprintf(f, "%s\t=\t%s\n", k, v)
		}
	}
	return
}

// AddCrontab TODO
func (i *InstallNewDbBackupComp) AddCrontab() error {
	if i.Params.UntarOnly {
		logger.Info("untar_only=true do not need AddCrontab")
		return nil
	}
	if i.Params.ClusterType == cst.TendbCluster {
		return i.addCrontabSpider()
	} else {
		return i.addCrontabLegacy()
	}
}

func (i *InstallNewDbBackupComp) addCrontabLegacy() (err error) {
	crondManager := ma.NewManager("http://127.0.0.1:9999")
	var jobItem ma.JobDefine
	logFile := path.Join(i.installPath, "logs/main.log")
	jobItem = ma.JobDefine{
		Name:     "dbbackup-schedule",
		Command:  filepath.Join(i.installPath, "dbbackup_main.sh"),
		WorkDir:  i.installPath,
		Args:     []string{">", logFile, "2>&1"},
		Schedule: i.getInsHostCrontabTime(),
		Creator:  i.Params.ExecUser,
		Enable:   true,
	}
	logger.Info("adding job_item to crond: %+v", jobItem)
	if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
		return err
	}
	return nil
}

func (i *InstallNewDbBackupComp) addCrontabSpider() (err error) {
	crondManager := ma.NewManager("http://127.0.0.1:9999")
	var jobItem ma.JobDefine
	if i.Params.Role == cst.BackupRoleSpiderMaster {
		dbbckupConfFile := fmt.Sprintf("dbbackup.%d.ini", i.Params.Ports[0])
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-schedule",
			Command:  filepath.Join(i.installPath, "dbbackup"),
			WorkDir:  i.installPath,
			Args:     []string{"spiderbackup", "schedule", "--config", dbbckupConfFile},
			Schedule: i.getInsHostCrontabTime(),
			Creator:  i.Params.ExecUser,
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
			return err
		}
	}
	if !(i.Params.Role == cst.BackupRoleSpiderMnt || i.Params.Role == cst.BackupRoleSpiderSlave) { // MASTER,SLAVE,REPEATER
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-check",
			Command:  filepath.Join(i.installPath, "dbbackup"),
			WorkDir:  i.installPath,
			Args:     []string{"spiderbackup", "check", "--run"},
			Schedule: "*/1 * * * *",
			Creator:  i.Params.ExecUser,
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
			return err
		}
	}
	return nil
}

func (i *InstallNewDbBackupComp) addCrontabOld() (err error) {
	var newCrontab []string
	err = osutil.RemoveSystemCrontab("dbbackup")
	if err != nil {
		return fmt.Errorf("删除原备份crontab任务失败(\"dbbackup\") get an error:%w", err)
	}
	entryshell := path.Join(i.installPath, "dbbackup_main.sh")
	logfile := path.Join(i.installPath, "dbbackup.log")
	newCrontab = append(
		newCrontab,
		fmt.Sprintf(
			"#dbbackup/dbbackup_main.sh: backup database every day, distribute at %s by %s",
			time.Now().Format(cst.TIMELAYOUT), i.Params.ExecUser,
		),
	)
	newCrontab = append(
		newCrontab,
		fmt.Sprintf(
			"%s %s 1>>%s 2>&1\n",
			i.getInsHostCrontabTime(), entryshell, logfile,
		),
	)
	crontabStr := strings.Join(newCrontab, "\n")
	return osutil.AddCrontab(crontabStr)
}

// BackupBackupIfExist  如如果已经存在备份程序，则先备份，在删除
func (i *InstallNewDbBackupComp) BackupBackupIfExist() (err error) {
	bakInstallPath := i.installPath + "-backup"
	if _, err := os.Stat(i.installPath); !os.IsNotExist(err) {
		cmd := fmt.Sprintf("rm -rf %s; mv %s %s", bakInstallPath, i.installPath, bakInstallPath)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			err = fmt.Errorf("execute %s get an error:%s,%w", cmd, output, err)
			return err
		}
	}
	return
}
