package dbbackup

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"path/filepath"
	"strings"
)

type NewDbBackupComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *NewDbBackupParam        `json:"extend"`
	newDbBackupContext
}

func (c *NewDbBackupComp) Init() (err error) {
	c.Params.Role = strings.ToUpper(c.Params.Role)

	c.initBackupOptions()
	c.installPath = filepath.Join(cst.MYSQL_TOOL_INSTALL_PATH, cst.BackupDir)
	c.versionMap = make(map[int]string) // not use
	c.renderCnf = make(map[int]config.BackupConfig)
	if c.Params.UntarOnly {
		logger.Info("untar_only=true do not try to connect")
		return nil
	}

	logger.Info("config %v", c.Params.Configs)
	return nil
}

func (c *NewDbBackupComp) initBackupOptions() {
	c.backupOpt = c.Params.Options

	c.ignoreDbs = make(map[int][]string)
	c.ignoreTbls = make(map[int][]string)
	for _, port := range c.Params.Ports {
		opt, ok := c.Params.Options[port]
		if !ok {
			c.Params.Options[port] = BackupOptions{} // unknown
			continue
		}
		logger.Info("options %v", opt)
		var ignoreTbls, ignoreDbs []string
		ignoreDbs = strings.Split(opt.IgnoreObjs.IgnoreDatabases, ",")
		ignoreDbs = append(ignoreDbs, native.DBSys...)
		// 默认备份需要 infodba_schema 库
		ignoreDbs = cmutil.StringsRemove(ignoreDbs, native.INFODBA_SCHEMA)
		ignoreTbls = strings.Split(opt.IgnoreObjs.IgnoreTables, ",")

		c.ignoreDbs[port] = util.UniqueStrings(cmutil.RemoveEmpty(ignoreDbs))
		c.ignoreTbls[port] = util.UniqueStrings(cmutil.RemoveEmpty(ignoreTbls))
		//if len(c.ignoreTbls[port]) <= 0 {
		//	c.ignoreTbls[port] = []string{"*"}
		//}
		logger.Info("port %d ignore dbs %v", port, c.ignoreDbs[port])
		logger.Info("port %d ignore tables %v", port, c.ignoreTbls[port])
	}
}

type NewDbBackupParam struct {
	components.Medium
	// Configs BackupConfig
	Configs        map[string]map[string]string `json:"configs" validate:"required"`         // 模板配置
	Options        map[int]BackupOptions        `json:"options" validate:"required"`         // 选项参数配置
	Host           string                       `json:"host"  validate:"required,ip"`        // 当前实例的主机地址
	Ports          []int                        `json:"ports" validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口
	Role           string                       `json:"role" validate:"required"`            // 当前主机安装的mysqld的角色
	ClusterType    string                       `json:"cluster_type"`
	BkBizId        int                          `json:"bk_biz_id" validate:"required"` // bkbizid
	BkCloudId      int                          `json:"bk_cloud_id"`                   // bk_cloud_id
	ClusterAddress map[int]string               `json:"cluster_address"`               // cluster addresss
	ClusterId      map[int]int                  `json:"cluster_id"`                    // cluster id
	ShardValue     map[int]int                  `json:"shard_value"`                   // shard value for spider
	ExecUser       string                       `json:"exec_user"`                     // 执行Job的用户
	UntarOnly      bool                         `json:"untar_only"`                    // 只解压，不校验不渲染配置，不连接 db
}

type newDbBackupContext struct {
	installPath string                      // dbbackupInstallPath
	versionMap  map[int]string              // 当前机器数据库实例版本
	renderCnf   map[int]config.BackupConfig // 绝对不能改成指针数组
	backupOpt   map[int]BackupOptions
	ignoreDbs   map[int][]string
	ignoreTbls  map[int][]string
}

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

type logicBackupDataOption struct {
	// "grant,schema,data"
	DataSchemaGrant string `json:"DataSchemaGrant"`
}
