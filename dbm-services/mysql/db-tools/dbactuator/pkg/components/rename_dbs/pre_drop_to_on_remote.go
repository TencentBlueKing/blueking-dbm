package rename_dbs

import (
	"context"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"fmt"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql 驱动

	"github.com/jmoiron/sqlx"
)

type PreDropToOnRemoteParam struct {
	Host           string          `json:"host" validate:"required,ip"`
	PortShardIdMap map[int]int     `json:"port_shard_id_map" validate:"required"`
	Requests       []renameRequest `json:"requests" validate:"required"`
}

type PreDropToOnRemoteComponent struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Param        *PreDropToOnRemoteParam  `json:"extend"`
	preDropToOnRemoteCtx
}

type preDropToOnRemoteCtx struct {
	dbConn *sqlx.Conn
}

func (c *PreDropToOnRemoteComponent) Do() error {
	for port := range c.Param.PortShardIdMap {
		err := c.oneInstance(port)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *PreDropToOnRemoteComponent) oneInstance(port int) error {
	err := c.instanceInit(port)
	if err != nil {
		return err
	}

	err = c.instanceDropToDBs(port)
	return err
}

func (c *PreDropToOnRemoteComponent) instanceInit(port int) error {
	c.preDropToOnRemoteCtx = preDropToOnRemoteCtx{}

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
		return err
	}

	conn, err := db.Connx(context.Background())
	if err != nil {
		return err
	}
	c.dbConn = conn

	return nil
}

func (c *PreDropToOnRemoteComponent) instanceDropToDBs(port int) error {
	for _, req := range c.Param.Requests {
		err := c.instanceDropToDB(port, req.ToDatabase)
		if err != nil {
			return err
		}
	}
	return nil
}

func (c *PreDropToOnRemoteComponent) instanceDropToDB(port int, dbName string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err := c.dbConn.ExecContext(
		ctx,
		fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", dbName),
	)
	return err
}

func (c *PreDropToOnRemoteComponent) Example() interface{} {
	return OnMySQLComponent{
		Param: &OnMySQLParam{
			Host: "127.0.0.1",
			PortShardIdMap: map[int]int{
				20000: 0,
				20001: 1,
			},
			Requests: []renameRequest{
				{
					FromDatabase: "old_db1",
					ToDatabase:   "new_db1",
				},
				{
					FromDatabase: "old_db2",
					ToDatabase:   "new_db2",
				},
			},
		},
	}
}
