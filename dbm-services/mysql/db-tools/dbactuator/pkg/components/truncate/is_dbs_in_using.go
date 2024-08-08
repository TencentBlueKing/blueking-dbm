package truncate

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/truncate/pkg"
	"fmt"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动

	"github.com/jmoiron/sqlx"
)

type IsDBsInUsingParams struct {
	Host           string   `json:"host" validate:"required,ip"`
	Port           int      `json:"port" validate:"required,gte=3306,lte=65535"`
	StageDBHeader  string   `json:"stage_db_header" validate:"required"`
	RollbackDBTail string   `json:"rollback_db_tail" validate:"required"`
	DBPatterns     []string `json:"db_patterns" validate:"required"`
	IgnoreDBs      []string `json:"ignore_dbs" validate:"required"`
	TablePatterns  []string `json:"table_patterns" validate:"required"`
	IgnoreTables   []string `json:"ignore_tables" validate:"required"`
	SystemDBs      []string `json:"system_dbs" validate:"required"`
}

type IsDBsInUsingComponent struct {
	GeneralParam    *components.GeneralParam `json:"general"`
	Param           *IsDBsInUsingParams      `json:"extend"`
	isDBsInUsingCtx `json:"-"`
}

type isDBsInUsingCtx struct {
	dbConn *sqlx.Conn
}

func (c *IsDBsInUsingComponent) Init() error {
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
	return nil
}

func (c *IsDBsInUsingComponent) IsDBsInUsing() error {
	reOpened, err := pkg.IsDBsInUsing(
		c.dbConn,
		c.Param.DBPatterns, c.Param.IgnoreDBs,
		c.Param.TablePatterns, c.Param.IgnoreTables,
		c.Param.SystemDBs, c.Param.StageDBHeader, c.Param.RollbackDBTail)
	if err != nil {
		return err
	}

	if len(reOpened) > 0 {
		err := fmt.Errorf("dbs %s is using", reOpened)
		return err
	}
	return nil
}

func (c *IsDBsInUsingComponent) Example() interface{} {
	return IsDBsInUsingComponent{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountAdminExample,
			},
		},
		Param: &IsDBsInUsingParams{
			Host:           "127.0.0.1",
			Port:           12345,
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
