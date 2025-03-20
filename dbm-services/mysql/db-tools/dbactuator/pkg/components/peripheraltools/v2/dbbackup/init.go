package dbbackup

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
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
	c.renderCnf = make(map[int]config.BackupConfig)

	logger.Info("config %v", c.Params.Configs)
	return nil
}

func (c *NewDbBackupComp) initBackupOptions() {
	c.ignoreDbs = make([]string, 0)
	c.ignoreTbls = make([]string, 0)

	var ignoreTbls, ignoreDbs []string
	ignoreDbs = strings.Split(c.Params.Options.IgnoreObjs.IgnoreDatabases, ",")
	ignoreDbs = append(ignoreDbs, native.DBSys...)
	// 默认备份需要 infodba_schema 库
	ignoreDbs = cmutil.StringsRemove(ignoreDbs, native.INFODBA_SCHEMA)
	ignoreTbls = strings.Split(c.Params.Options.IgnoreObjs.IgnoreTables, ",")

	c.ignoreDbs = util.UniqueStrings(cmutil.RemoveEmpty(ignoreDbs))
	c.ignoreTbls = util.UniqueStrings(cmutil.RemoveEmpty(ignoreTbls))

	logger.Info("ignore dbs %v", c.ignoreDbs)
	logger.Info("ignore tables %v", c.ignoreTbls)

}

type NewDbBackupParam struct {
	// Configs BackupConfig
	Configs      map[string]map[string]string `json:"configs" validate:"required"`         // 模板配置
	Options      *BackupOptions               `json:"options" validate:"required"`         // 选项参数配置
	Host         string                       `json:"host"  validate:"required,ip"`        // 当前实例的主机地址
	Ports        []int                        `json:"ports" validate:"required,gt=0,dive"` // 被监控机器的上所有需要监控的端口
	Role         string                       `json:"role" validate:"required"`            // 当前主机安装的mysqld的角色
	ClusterType  string                       `json:"cluster_type"`
	BkBizId      int                          `json:"bk_biz_id" validate:"required"`
	BkCloudId    int                          `json:"bk_cloud_id"`
	ImmuteDomain string                       `json:"immute_domain"`
	ClusterId    int                          `json:"cluster_id"`  // cluster id
	ShardValue   map[int]int                  `json:"shard_value"` // shard value for spider
	ExecUser     string                       `json:"exec_user"`   // 执行Job的用户

}

type newDbBackupContext struct {
	renderCnf  map[int]config.BackupConfig // 绝对不能改成指针数组
	ignoreDbs  []string
	ignoreTbls []string
}

type BackupOptions struct {
	BackupType  string `json:"BackupType" validate:"required"`
	CrontabTime string `json:"CrontabTime" validate:"required"`
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
