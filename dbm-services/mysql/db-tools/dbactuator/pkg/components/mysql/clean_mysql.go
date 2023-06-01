package mysql

import (
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"

	"github.com/pkg/errors"
)

// CleanMysqlComp 需要将 BaseInputParam 转换成 Comp 参数
type CleanMysqlComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       CleanMysqlParam          `json:"extend"`
}

// Example TODO
func (c *CleanMysqlComp) Example() interface{} {
	comp := CleanMysqlComp{
		Params: CleanMysqlParam{
			StopSlave:   true,
			ResetSlave:  true,
			Force:       false,
			TgtInstance: &common.InstanceExample,
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
	}
	return comp
}

// CleanMysqlParam 删除目标实例里面的所有 database
// 保留系统库，如 mysql,infodba_schema, sys 等
type CleanMysqlParam struct {
	// 是否执行 stop slave
	StopSlave bool `json:"stop_slave"`
	// 是否执行 reset slave all
	ResetSlave bool `json:"reset_slave"`
	// drop_database 之后是否重启实例
	Restart bool `json:"restart"`
	// 当实例不空闲时是否强制清空
	Force bool `json:"force"`
	// 是否执行 drop database，这里是确认行为. 如果 false 则只把 drop 命令打印到输出
	DropDatabase     bool `json:"drop_database"`
	CheckIntervalSec int  `json:"check_interval_sec"`
	// 清空目标实例
	TgtInstance *native.Instance `json:"tgt_instance" validate:"required"`

	checkDuration time.Duration

	myCnf    *util.CnfFile
	dbworker *native.DbWorker
	instObj  *native.InsObject
	// account  *components.RuntimeAccountParam
}

// Init TODO
func (c *CleanMysqlComp) Init() error {
	f := util.GetMyCnfFileName(c.Params.TgtInstance.Port)
	c.Params.myCnf = &util.CnfFile{FileName: f}
	if err := c.Params.myCnf.Load(); err != nil {
		return err
	}
	dbSocket, err := c.Params.myCnf.GetMySQLSocket()
	if err != nil {
		return err
	}
	c.Params.instObj = &native.InsObject{
		Host:   c.Params.TgtInstance.Host,
		Port:   c.Params.TgtInstance.Port,
		User:   c.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:    c.GeneralParam.RuntimeAccountParam.AdminPwd,
		Socket: dbSocket,
	}
	if dbw, err := c.Params.instObj.ConnBySocket(); err != nil {
		return err
	} else {
		c.Params.dbworker = dbw
	}
	if c.Params.CheckIntervalSec == 0 {
		c.Params.CheckIntervalSec = 31
	}
	c.Params.checkDuration = time.Duration(c.Params.CheckIntervalSec) * time.Second
	return nil
}

// PreCheck 前置检查
// 会初始化 needRestart
func (c *CleanMysqlComp) PreCheck() error {
	if err := c.Params.instObj.CheckInstanceConnIdle(c.GeneralParam.RuntimeExtend.MySQLSysUsers,
		c.Params.checkDuration); err != nil {
		logger.Warn("clean_mysql precheck error %w", err)
		if c.Params.Force {
			return nil
		}
		return err
	}
	return nil
}

// Start TODO
func (c *CleanMysqlComp) Start() error {
	if c.Params.StopSlave {
		if err := c.Params.dbworker.StopSlave(); err != nil {
			return errors.WithMessage(err, "stop slave")
		}
	}
	if c.Params.ResetSlave {
		if err := c.Params.dbworker.ResetSlave(); err != nil {
			return errors.WithMessage(err, "reset slave")
		}
	}

	// 计划删除的 databases 列表
	inStr, _ := mysqlutil.UnsafeBuilderStringIn(native.DBSys, "'")
	dbsSql := fmt.Sprintf("select SCHEMA_NAME from information_schema.SCHEMATA where SCHEMA_NAME not in (%s)", inStr)

	if databases, err := c.Params.dbworker.Query(dbsSql); err != nil {
		if c.Params.dbworker.IsNotRowFound(err) {
			return nil
		} else {
			return err
		}
	} else {
		for _, dbName := range databases {
			dropSQL := fmt.Sprintf("DROP DATABASE `%s`;", dbName["SCHEMA_NAME"])
			logger.Warn("run sql %s", dropSQL)
			if c.Params.DropDatabase {
				if _, err := c.Params.dbworker.Exec(dropSQL); err != nil {
					return errors.WithMessage(err, dropSQL)
				}
			} else {
				fmt.Printf("%s -- not run because drop_database=false\n", dropSQL)
			}
		}
		if c.Params.DropDatabase && c.Params.Restart {
			if err := computil.RestartMysqlInstanceNormal(*c.Params.instObj); err != nil {
				return err
			}
		}
	}
	return nil
}
