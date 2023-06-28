package mysql

import (
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
	"text/template"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
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
	Configs        map[string]map[string]string `json:"configs" validate:"required"`         // 模板配置
	Options        BackupOptions                `json:"options" validate:"required"`         // 选项参数配置
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
}

type runtimeContext struct {
	installPath string                    // dbbackupInstallPath
	dbConn      map[Port]*native.DbWorker // db连接池
	versionMap  map[Port]string           // 当前机器数据库实例版本
	renderCnf   map[Port]config.BackupConfig
	ignoredbs   []string
	ignoretbls  []string
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
			Options: BackupOptions{
				CrontabTime: "09:00:00",
				BackupType:  "logical",
				Master:      logicBackupDataOption{DataSchemaGrant: "grant"},
				Slave:       logicBackupDataOption{DataSchemaGrant: "grant"},
			},
			Configs:        nil, //&config.BackupConfig{},
			Role:           "slave",
			ClusterAddress: map[Port]string{20000: "testdb1.xx.a1.db", 20001: "testdb2.xx.a1.db"},
			ClusterId:      map[Port]int{20000: 111, 20001: 112},
		},
	}
	return comp
}

// Init TODO
func (i *InstallNewDbBackupComp) Init() (err error) {
	i.initBackupOptions()
	i.installPath = path.Join(cst.MYSQL_TOOL_INSTALL_PATH, cst.BackupDir)
	i.dbConn = make(map[int]*native.DbWorker)
	i.versionMap = make(map[int]string)
	i.renderCnf = make(map[int]config.BackupConfig)
	for _, port := range i.Params.Ports {
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
	}

	logger.Info("config %v", i.Params.Configs)
	return nil
}

func (i *InstallNewDbBackupComp) initBackupOptions() {
	logger.Info("options %v", i.Params.Options)
	var ignoretbls, ignoredbs []string
	ignoredbs = strings.Split(i.Params.Options.IgnoreObjs.IgnoreDatabases, ",")
	ignoredbs = append(ignoredbs, native.DBSys...)
	ignoretbls = strings.Split(i.Params.Options.IgnoreObjs.IgnoreTables, ",")

	i.ignoredbs = util.UniqueStrings(util.RemoveEmpty(ignoredbs))
	i.ignoretbls = util.UniqueStrings(util.RemoveEmpty(ignoretbls))
	if len(i.ignoretbls) <= 0 {
		i.ignoretbls = []string{"*"}
	}
	logger.Info("ignore dbs %v", i.ignoredbs)
	logger.Info("ignore ignoretbls %v", i.ignoretbls)
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

// InitRenderData 初始化待渲染的配置变量
func (i *InstallNewDbBackupComp) InitRenderData() (err error) {
	bkuser := i.GeneralParam.RuntimeAccountParam.DbBackupUser
	bkpwd := i.GeneralParam.RuntimeAccountParam.DbBackupPwd
	regexfunc, err := db_table_filter.NewDbTableFilter([]string{"*"}, []string{"*"}, i.ignoredbs, i.ignoretbls)
	if err != nil {
		return err
	}
	regexStr := regexfunc.TableFilterRegex()
	logger.Info("regexStr %v", regexStr)
	// 根据role 选择备份参数选项
	var dsg string
	i.Params.Role = strings.ToUpper(i.Params.Role)
	switch i.Params.Role {
	case cst.BackupRoleMaster, cst.BackupRoleRepeater:
		dsg = i.Params.Options.Master.DataSchemaGrant
	case cst.BackupRoleSlave:
		dsg = i.Params.Options.Slave.DataSchemaGrant
	case cst.BackupRoleOrphan:
		// orphan 使用的是 tendbsingle Master.DataSchemaGrant
		dsg = i.Params.Options.Master.DataSchemaGrant
	case cst.BackupRoleSpiderMaster, cst.BackupRoleSpiderSlave:
		// spider 只在 spider_master and tdbctl_master 上，备份schema,grant
		dsg = "schema,grant"
	default:
		return fmt.Errorf("未知的备份角色%s", i.Params.Role)
	}
	for _, port := range i.Params.Ports {
		i.renderCnf[port] = config.BackupConfig{
			Public: config.Public{
				MysqlHost:       i.Params.Host,
				MysqlPort:       port,
				MysqlUser:       bkuser,
				MysqlPasswd:     bkpwd,
				MysqlRole:       strings.ToLower(i.Params.Role),
				BkBizId:         i.Params.BkBizId,
				ClusterAddress:  i.getInsDomainAddr(port),
				ClusterId:       i.getInsClusterId(port),
				ShardValue:      i.getInsShardValue(port),
				DataSchemaGrant: dsg,
			},
			BackupClient: config.BackupClient{},
			LogicalBackup: config.LogicalBackup{
				Regex: regexStr,
			},
			PhysicalBackup: config.PhysicalBackup{
				DefaultsFile: util.GetMyCnfFileName(port),
			},
		}
	}
	return nil
}

// InitBackupDir 判断备份目录是否存在,不存在的话则创建
func (i *InstallNewDbBackupComp) InitBackupDir() (err error) {
	backupdir := i.Params.Configs["Public"]["BackupDir"]

	if _, err := os.Stat(backupdir); os.IsNotExist(err) {
		logger.Warn("backup dir %s is not exist. will make it", backupdir)
		cmd := fmt.Sprintf("mkdir -p %s", backupdir)
		output, err := osutil.ExecShellCommand(false, cmd)
		if err != nil {
			return fmt.Errorf("execute [%s] get an error:%s,%w", cmd, output, err)
		}
	}
	cmd := fmt.Sprintf("chown -R mysql %s", backupdir)
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
		"tar zxf %s -C %s &&  chown -R mysql %s", i.Params.Medium.GetAbsolutePath(),
		path.Dir(i.installPath), i.installPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}

// InitBackupUserPriv TODO
func (i *InstallNewDbBackupComp) InitBackupUserPriv() (err error) {
	for _, port := range i.Params.Ports {
		ver := i.versionMap[port]
		var isMysql80 = mysqlutil.MySQLVersionParse(ver) >= mysqlutil.MySQLVersionParse("8.0") &&
			!strings.Contains(ver, "tspider")
		privs := i.GeneralParam.RuntimeAccountParam.MySQLDbBackupAccount.GetAccountPrivs(isMysql80, i.Params.Host)
		sqls := privs.GenerateInitSql(ver)
		dc, ok := i.dbConn[port]
		if !ok {
			return fmt.Errorf("from dbConns 获取%d连接失败", port)
		}
		if _, err = dc.ExecMore(sqls); err != nil {
			logger.Error("初始化备份账户失败%s", err.Error())
			return
		}
	}
	return
}

// GenerateDbbackupConfig TODO
func (i *InstallNewDbBackupComp) GenerateDbbackupConfig() (err error) {
	// 先渲染模版配置文件
	templatePath := path.Join(i.installPath, fmt.Sprintf("%s.tpl", cst.BackupFile))
	if err := i.saveTplConfigfile(templatePath); err != nil {
		return err
	}

	cnfTemp, err := template.ParseFiles(templatePath)
	if err != nil {
		return errors.WithMessage(err, "template ParseFiles failed")
	}

	var cnfFiles []*os.File
	defer func() {
		for _, f := range cnfFiles {
			_ = f.Close()
		}
	}()

	for _, port := range i.Params.Ports {
		cnfPath := path.Join(i.installPath, cst.GetNewConfigByPort(port))
		cnfFile, err := os.Create(cnfPath)
		if err != nil {
			return errors.WithMessage(err, fmt.Sprintf("create %s failed", cnfPath))
		}

		cnfFiles = append(cnfFiles, cnfFile)

		if data, ok := i.renderCnf[port]; ok {
			if err = cnfTemp.Execute(cnfFile, data); err != nil {
				return errors.WithMessage(err, "渲染%d的备份配置文件失败")
			}
		} else {
			return fmt.Errorf("not found %d render data", port)
		}
	}
	return nil
}

// ChownGroup 更改安装目录的所属组
func (i *InstallNewDbBackupComp) ChownGroup() (err error) {
	cmd := fmt.Sprintf(
		" chown -R mysql %s ; chmod +x %s/*.sh ; chmod +x %s/dbbackup",
		path.Dir(i.installPath), i.installPath, i.installPath,
	)
	output, err := osutil.ExecShellCommand(false, cmd)
	if err != nil {
		err = fmt.Errorf("execute %s error:%w,%s", cmd, err, output)
		return err
	}
	return nil
}

//func (i *InstallNewDbBackupComp) saveTplConfigfile(tmpl string) (err error) {
//	cfg := ini.Empty()
//	if err = cfg.ReflectFrom(&i.Params.Configs); err != nil {
//		return errors.WithMessage(err, "参数反射ini失败")
//	}
//	if err := cfg.SaveTo(tmpl); err != nil {
//		return errors.WithMessage(err, "保存模版配置失败")
//	}
//	fileinfo, err := os.Stat(tmpl)
//	if err != nil {
//		return errors.WithMessage(err, fmt.Sprintf("os stats file %s failed", tmpl))
//	}
//	if fileinfo.Size() <= 0 {
//		return fmt.Errorf("渲染的配置为空！！！")
//	}
//	if err := cfg.SaveTo(tmpl); err != nil {
//		return errors.WithMessage(err, "保存模版配置失败")
//	}
//	return
//}

func (i *InstallNewDbBackupComp) saveTplConfigfile(tmpl string) (err error) {
	f, err := os.OpenFile(tmpl, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755)
	if err != nil {
		return errors.WithMessage(err, "新建文件失败")
	}
	defer func() {
		_ = f.Close()
	}()

	for k, v := range i.Params.Configs {
		_, err := fmt.Fprintf(f, "[%s]\n", k)
		if err != nil {
			return errors.WithMessagef(err, "写配置模版 %s 失败", k)
		}
		for k, v := range v {
			_, err := fmt.Fprintf(f, "%s=%s\n", k, v)
			if err != nil {
				return errors.WithMessagef(err, "写配置模版 %s, %s 失败", k, v)
			}
		}
	}
	return
}

// AddCrontab TODO
func (i *InstallNewDbBackupComp) AddCrontab() error {
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
		Schedule: i.Params.Options.CrontabTime,
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
	if i.Params.Role == cst.RoleSpiderMaster {
		dbbckupConfFile := fmt.Sprintf("dbbackup.%d.ini", i.Params.Ports[0])
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-schedule",
			Command:  filepath.Join(i.installPath, "dbbackup"),
			WorkDir:  i.installPath,
			Args:     []string{"spiderbackup", "--schedule", "--config", dbbckupConfFile},
			Schedule: i.Params.Options.CrontabTime,
			Creator:  i.Params.ExecUser,
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		if _, err = crondManager.CreateOrReplace(jobItem, true); err != nil {
			return err
		}
	}
	if !(i.Params.Role == cst.RoleSpiderMnt || i.Params.Role == cst.RoleSpiderSlave) { // MASTER,SLAVE,REPEATER
		jobItem = ma.JobDefine{
			Name:     "spiderbackup-check-run",
			Command:  filepath.Join(i.installPath, "dbbackup"),
			WorkDir:  i.installPath,
			Args:     []string{"spiderbackup", "--check", "--run"},
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
			i.Params.Options.CrontabTime, entryshell, logfile,
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
