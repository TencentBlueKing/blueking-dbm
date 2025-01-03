package truncate

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	rpkg "dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	tpkg "dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate/pkg"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动
	"github.com/jmoiron/sqlx"
)

type ViaCtlParam struct {
	Host             string   `json:"host" validate:"required,ip"`
	Port             int      `json:"port" validate:"required,gte=3306,lte=65535"`
	FlowTimeStr      string   `json:"flow_timestr" validate:"required"`
	StageDBHeader    string   `json:"stage_db_header" validate:"required"`
	RollbackDBTail   string   `json:"rollback_db_tail" validate:"required"`
	DBPatterns       []string `json:"db_patterns" validate:"required"`
	IgnoreDBs        []string `json:"ignore_dbs" validate:"required"`
	TablePatterns    []string `json:"table_patterns" validate:"required"`
	IgnoreTables     []string `json:"ignore_tables" validate:"required"`
	SystemDBs        []string `json:"system_dbs" validate:"required"`
	TruncateDataType string   `json:"truncate_data_type" validate:"required" enums:"truncate_table,drop_database,drop_table"`
}

type ViaCtlComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *ViaCtlParam             `json:"extend"`
	viaCtlCtx    `json:"-"`
}

type viaCtlCtx struct {
	dbTablesMap map[string][]string
	dbConn      *sqlx.Conn
}

func (c *ViaCtlComponent) Init() error {
	c.dbTablesMap = make(map[string][]string)

	db, err := sqlx.Connect(
		"mysql",
		fmt.Sprintf("%s:%s@tcp(%s:%d)/",
			c.GeneralParam.RuntimeAccountParam.AdminUser, c.GeneralParam.RuntimeAccountParam.AdminPwd,
			c.Param.Host, c.Param.Port,
		),
	)
	if err != nil {
		logger.Error("connecting mysql db failed: ", err.Error())
		return err
	}
	logger.Info("connecting mysql db %s:%d success", c.Param.Host, c.Param.Port)
	conn, err := db.Connx(context.Background())
	if err != nil {
		logger.Error("get connection from mysql db failed: ", err.Error())
		return err
	}
	c.dbConn = conn

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err = c.dbConn.ExecContext(ctx, `SET TC_ADMIN=1`)
	if err != nil {
		logger.Error("setting tc_admin failed: ", err.Error())
		return err
	}

	return nil
}

func (c *ViaCtlComponent) GetTarget() error {
	target, err := tpkg.GetTarget(
		c.dbConn,
		c.Param.DBPatterns, c.Param.IgnoreDBs, c.Param.TablePatterns, c.Param.IgnoreTables, c.Param.SystemDBs,
		c.Param.StageDBHeader, c.Param.RollbackDBTail,
		0, false,
	)
	if err != nil {
		logger.Error("get target db-tables failed: ", err.Error())
		return err
	}
	logger.Info("get target db-tables success: %v", target)
	if target == nil || len(target) == 0 {
		err = fmt.Errorf("got empty db-tables target")
		logger.Error("get db-tables failed: %s", err.Error())
		return err
	}
	c.dbTablesMap = target
	return nil
}

func (c *ViaCtlComponent) CreateStageDBs() error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		err := rpkg.CreateDB(c.dbConn, stageDBName)
		if err != nil {
			logger.Error("create stage for db: %s failed: ", db, err.Error())
			return err
		}
	}

	return nil
}

// CreateStageTables
// 这一步只为了中控和 spider 上有表结构
// remote 上的其实还要 drop 表
// 清档不考虑备份非表对象
func (c *ViaCtlComponent) CreateStageTables() error {
	for dbName, tables := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, dbName)
		err := rpkg.CreateTablesLike(c.dbConn, dbName, stageDBName, tables)
		if err != nil {
			return err
		}
	}
	return nil
}

// Truncate truncate table 不需要任何处理
func (c *ViaCtlComponent) Truncate() error {
	/*
			v1 版本中, 这一步操作是直接 drop db, 而且写法是 drop db if exists
			所以可以不用关心 remote 上这个 db 在不在
			v2 版本优化了 dropSourceDBs, 会先定向删除 db 中表, 能减少超时
			但是当 remote 的 db 不存在时 (实际确实没了), 会报错
			所以需要在这里单独把 tcadmin 设置为 0, 不转发 drop 命令
		    只能在这个函数内设置, 因为这个函数只在最后的 中控清档 步骤执行
		    如果在前面设置会影响其他步骤
	*/
	_, err := c.dbConn.ExecContext(context.Background(), `SET TC_ADMIN=0`)
	if err != nil {
		logger.Error("truncate on ctl set tc admin failed: ", err.Error())
		return err
	}

	if c.Param.TruncateDataType == "drop_database" {
		err := c.dropSourceDBs()
		if err != nil {
			logger.Error("drop source dbs failed: ", err.Error())
			return err
		}
	} else if c.Param.TruncateDataType == "drop_table" {
		err := c.dropSourceTables()
		if err != nil {
			logger.Error("drop source table failed: ", err.Error())
			return err
		}
	}
	return nil
}

func (c *ViaCtlComponent) GenerateDropStageSQL() error {
	var dropSQLs []string
	for dbName := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, dbName)
		dropSQL := fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", stageDBName)
		dropSQLs = append(dropSQLs, dropSQL)
	}

	b, err := json.Marshal(dropSQLs)
	if err != nil {
		return err
	}

	logger.Info(string(b))
	fmt.Println(components.WrapperOutputString(strings.TrimSpace(string(b))))
	return nil
}

func (c *ViaCtlComponent) dropSourceTables() error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)
		err := tpkg.SafeDropSourceTables(c.dbConn, db, stageDBName, c.dbTablesMap[db])
		if err != nil {
			logger.Error("drop source tables %v failed: ", c.dbTablesMap[db], err.Error())
			return err
		}
		logger.Info("drop source tables %v success", c.dbTablesMap[db])
	}
	logger.Info("drop source table success")
	return nil
}

// 如果库下面有很多表, 直接 drop database 很容易超时
// 得循环起来先一个一个把表 drop 了
func (c *ViaCtlComponent) dropSourceDBs() error {
	for db := range c.dbTablesMap {
		stageDBName := generateStageDBName(c.Param.StageDBHeader, c.Param.FlowTimeStr, db)

		logger.Info(fmt.Sprintf("drop source dbs %v should drop it's tables", c.dbTablesMap[db]))

		err := tpkg.SafeDropSourceTables(c.dbConn, db, stageDBName, c.dbTablesMap[db])
		if err != nil {
			logger.Error("drop source tables %v failed: ", c.dbTablesMap[db], err.Error())
			return err
		}
		logger.Info("drop source tables %v success", c.dbTablesMap[db])

		err = rpkg.DropDB(c.dbConn, db, stageDBName, true)
		if err != nil {
			logger.Error(
				"drop db %s failed: %s", db, err.Error(),
			)
			return err
		}
		logger.Info("drop db %s success", db)
	}
	logger.Info("drop db success")
	return nil
}

func (c *ViaCtlComponent) Example() interface{} {
	return ViaCtlComponent{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
		Param: &ViaCtlParam{
			Host:           "127.0.0.1",
			Port:           12345,
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
