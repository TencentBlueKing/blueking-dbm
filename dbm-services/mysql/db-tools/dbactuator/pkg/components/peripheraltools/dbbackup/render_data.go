package dbbackup

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"fmt"
	"strings"
)

func (c *NewDbBackupComp) InitRenderData() (err error) {
	if c.Params.UntarOnly {
		logger.Info("untar_only=true do not need InitRenderData")
		return nil
	}

	bkuser := c.GeneralParam.RuntimeAccountParam.DbBackupUser
	bkpwd := c.GeneralParam.RuntimeAccountParam.DbBackupPwd

	for _, port := range c.Params.Ports {
		pf, err := db_table_filter.NewFilter([]string{"*"}, []string{"*"}, c.ignoreDbs[port], c.ignoreTbls[port])
		if err != nil {
			return err
		}
		regexStr := pf.TableFilterRegex()
		logger.Info("include db: %v, include table: %v, exclude db: %v, exclude table: %v",
			pf.IncludeDbPatterns, pf.IncludeTablePatterns, pf.ExcludeDbPatterns, pf.ExcludeTablePatterns)
		logger.Info("regexStr %v", regexStr)
		// 根据role 选择备份参数选项
		var dsg string
		switch c.Params.Role {
		case cst.BackupRoleMaster, cst.BackupRoleRepeater:
			dsg = c.backupOpt[port].Master.DataSchemaGrant
		case cst.BackupRoleSlave:
			dsg = c.backupOpt[port].Slave.DataSchemaGrant
		case cst.BackupRoleOrphan:
			// orphan 使用的是 tendbsingle Master.DataSchemaGrant
			dsg = c.backupOpt[port].Master.DataSchemaGrant
		case cst.BackupRoleSpiderMaster, cst.BackupRoleSpiderSlave, cst.BackupRoleSpiderMnt:
			// spider 只在 spider_master and tdbctl_master 上，备份schema,grant
			dsg = "schema,grant"
		default:
			return fmt.Errorf("未知的备份角色%s", c.Params.Role)
		}
		cfg := config.BackupConfig{
			Public: config.Public{
				MysqlHost:       c.Params.Host,
				MysqlPort:       port,
				MysqlUser:       bkuser,
				MysqlPasswd:     bkpwd,
				MysqlRole:       strings.ToLower(c.Params.Role),
				BkBizId:         c.Params.BkBizId,
				BkCloudId:       c.Params.BkCloudId,
				ClusterAddress:  c.getInsDomainAddr(port),
				ClusterId:       c.getInsClusterId(port),
				ShardValue:      c.getInsShardValue(port),
				BackupType:      c.backupOpt[port].BackupType,
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

		c.renderCnf[port] = cfg

		if c.Params.Role == cst.BackupRoleSpiderMaster {
			tdbctlPort := mysqlcomm.GetTdbctlPortBySpider(port)
			cfg.Public.MysqlPort = tdbctlPort
			cfg.Public.MysqlRole = cst.BackupRoleTdbctl
			cfg.PhysicalBackup.DefaultsFile = util.GetMyCnfFileName(tdbctlPort)
			c.renderCnf[tdbctlPort] = cfg
		}
	}
	return nil
}

func (c *NewDbBackupComp) getInsDomainAddr(port int) string {
	if c.Params.ClusterAddress == nil {
		return ""
	}
	if len(c.Params.ClusterAddress) == 0 {
		return ""
	}
	if v, ok := c.Params.ClusterAddress[port]; ok {
		return v
	}
	return ""
}
func (c *NewDbBackupComp) getInsClusterId(port int) int {
	if c.Params.ClusterId == nil {
		return 0
	}
	if len(c.Params.ClusterId) == 0 {
		return 0
	}
	if v, ok := c.Params.ClusterId[port]; ok {
		return v
	}
	return 0
}
func (c *NewDbBackupComp) getInsShardValue(port int) int {
	if c.Params.ShardValue == nil {
		return 0
	}
	if len(c.Params.ShardValue) == 0 {
		return 0
	}
	if v, ok := c.Params.ShardValue[port]; ok {
		return v
	}
	return 0
}
