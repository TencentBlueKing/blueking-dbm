package truncate

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate/pkg"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"fmt"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动
	"github.com/jmoiron/sqlx"
)

type PreDropStageOnRemoteParam struct {
	Host           string      `json:"host" validate:"required,ip"`
	PortShardIdMap map[int]int `json:"port_shard_id_map" validate:"required"`
	FlowTimeStr    string      `json:"flow_timestr" validate:"required"`
	StageDBHeader  string      `json:"stage_db_header" validate:"required"`
	RollbackDBTail string      `json:"rollback_db_tail" validate:"required"`
	DBPatterns     []string    `json:"db_patterns" validate:"required"`
	IgnoreDBs      []string    `json:"ignore_dbs" validate:"required"`
	TablePatterns  []string    `json:"table_patterns" validate:"required"`
	IgnoreTables   []string    `json:"ignore_tables" validate:"required"`
	SystemDBs      []string    `json:"system_dbs" validate:"required"`
}

type PreDropStageOnRemoteComponent struct {
	GeneralParam               *components.GeneralParam   `json:"general"`
	Param                      *PreDropStageOnRemoteParam `json:"extend"`
	tools                      *tools.ToolSet
	preDropOnRemoteInstanceCtx `json:"-"`
}

type preDropOnRemoteInstanceCtx struct {
	dbTablesMap map[string][]string
	dbConn      *sqlx.Conn
}

func (c *PreDropStageOnRemoteComponent) Init() error {
	return nil
}

func (c *PreDropStageOnRemoteComponent) Do() error {
	for port := range c.Param.PortShardIdMap {
		err := c.oneInstance(port)
		if err != nil {
			logger.Error("pre drop stage %s:%d failed: ", c.Param.Host, port, err.Error())
			return err
		}
		logger.Info("pre drop stage %s:%d finished", c.Param.Host, port)
	}

	logger.Info("pre drop %s finished", c.Param.Host)
	return nil
}

func (c *PreDropStageOnRemoteComponent) oneInstance(port int) error {
	err := c.instanceInit(port)
	if err != nil {
		logger.Error("init instance %d pre drop failed: %s", port, err.Error())
		return err
	}

	err = c.instanceGetTarget(port)
	if err != nil {
		logger.Error("get target on instance %d pre drop failed: %s", port, err.Error())
		return err
	}

	err = c.instanceDropStageDBs(port)
	if err != nil {
		logger.Error("drop stage dbs on instance %d truncate failed: %s", port, err.Error())
		return err
	}

	return nil
}

func (c *PreDropStageOnRemoteComponent) instanceInit(port int) error {
	c.preDropOnRemoteInstanceCtx = preDropOnRemoteInstanceCtx{}

	c.dbTablesMap = make(map[string][]string)

	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf("%s:%s@tcp(%s:%d)/",
			c.GeneralParam.RuntimeAccountParam.AdminUser,
			c.GeneralParam.RuntimeAccountParam.AdminPwd,
			c.Param.Host,
			port,
		),
	)
	if err != nil {
		logger.Error("connect MySQL instance %s:%d failed: %s", c.Param.Host, port, err.Error())
		return err
	}
	logger.Info("connecting mysql db %s:%d success", c.Param.Host, port)
	conn, err := db.Connx(context.Background())
	if err != nil {
		logger.Error("get connection from mysql db failed: %s", err.Error())
		return err
	}
	c.dbConn = conn

	logger.Info("init pre drop on %s:%d success", c.Param.Host, port)
	return nil
}

func (c *PreDropStageOnRemoteComponent) instanceGetTarget(port int) error {
	target, err := pkg.GetTarget(
		c.dbConn,
		c.Param.DBPatterns, c.Param.IgnoreDBs, c.Param.TablePatterns, c.Param.IgnoreTables, c.Param.SystemDBs,
		c.Param.StageDBHeader, c.Param.RollbackDBTail,
		c.Param.PortShardIdMap[port], true,
	)
	if err != nil {
		logger.Error("get instance %d db-tables failed: %s", port, err.Error())
		return err
	}
	logger.Info("get instance %d db-tables success: %v", port, target)

	if target == nil || len(target) == 0 {
		err = fmt.Errorf("got empty db-tables target")
		logger.Error("get db-tables failed: %s", err.Error())
		return err
	}

	c.dbTablesMap = target
	return nil
}

func (c *PreDropStageOnRemoteComponent) instanceDropStageDBs(port int) error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		err := c.instanceDropStageDB(port, stageDBName) // 不用太安全
		if err != nil {
			logger.Error("drop stage db %s on instance %d failed: %s", stageDBName, port, err.Error())
			return err
		}
	}
	logger.Info("drop stage dbs on instance %d finished", port)
	return nil
}

func (c *PreDropStageOnRemoteComponent) instanceDropStageDB(port int, dbName string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Second)
	defer cancel()

	_, err := c.dbConn.ExecContext(
		ctx,
		fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", dbName),
	)
	if err != nil {
		logger.Error("drop stage db %s on instance %d failed: %s", dbName, port, err.Error())
		return err
	}
	logger.Info("drop stage db %s on instance %d finished", dbName, port)
	return nil
}

func (c *PreDropStageOnRemoteComponent) Example() interface{} {
	return PreDropStageOnRemoteComponent{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
		Param: &PreDropStageOnRemoteParam{
			Host: "127.0.0.1",
			PortShardIdMap: map[int]int{
				20000: 0,
				20001: 1,
			},
			FlowTimeStr:    "19700102040506",
			StageDBHeader:  "stage_truncate",
			RollbackDBTail: "rollback",
			DBPatterns:     []string{"db%"},
			IgnoreDBs:      []string{"db1"},
			TablePatterns:  []string{"*"},
			IgnoreTables:   []string{"*"},
			SystemDBs:      []string{"mysql", "test"},
		},
	}
}
