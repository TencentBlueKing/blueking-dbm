package rename_dbs

import (
	"context"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	"fmt"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动

	"dbm-services/common/go-pubpkg/logger"

	"github.com/jmoiron/sqlx"
)

type IsDBsInUsingParams struct {
	Host string   `json:"host" validate:"required,ip"`
	Port int      `json:"port" validate:"required,gte=3306,lte=65535"`
	DBs  []string `json:"dbs" validate:"required"`
}

type IsDBsInUsingComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *IsDBsInUsingParams      `json:"extend"`
	isDBsInUsingCtx
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
	reOpened, err := pkg.IsDBsInUsing(c.dbConn, c.Param.DBs)
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
			Host: "127.0.0.1",
			Port: 12345,
			DBs:  []string{"db1", "db2"},
		},
	}
}
