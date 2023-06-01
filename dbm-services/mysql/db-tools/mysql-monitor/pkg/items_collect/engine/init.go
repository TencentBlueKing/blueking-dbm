package engine

import (
	"context"
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var name = "engine"

type tableEngineInfo struct {
	TableSchema string `db:"TABLE_SCHEMA"`
	TableName   string `db:"TABLE_NAME"`
	Engine      string `db:"ENGINE"`
}

// Checker TODO
type Checker struct {
	db    *sqlx.DB
	infos []tableEngineInfo
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	q, args, err := sqlx.In(
		`SELECT TABLE_SCHEMA, TABLE_NAME, ENGINE 
					FROM information_schema.TABLES 
					WHERE TABLE_SCHEMA NOT IN (?) 
					AND 
					    TABLE_TYPE = ?`,
		config.MonitorConfig.DBASysDbs,
		"BASE TABLE",
	)
	if err != nil {
		return "", errors.Wrap(err, "build IN query table engine")
	}

	var infos []tableEngineInfo
	err = c.db.SelectContext(ctx, &infos, c.db.Rebind(q), args...)
	if err != nil {
		return "", errors.Wrap(err, "query table engine")
	}
	c.infos = infos

	myisamTables := c.myisam()
	if len(myisamTables) > 0 {
		msg = fmt.Sprintf("%d myisam-like talbe found", len(myisamTables))
	}

	engineCountMap := c.hyperEngine()
	var engineCountSlice []string
	for k, v := range engineCountMap {
		engineCountSlice = append(engineCountSlice, fmt.Sprintf("%d %s tables", v, k))
	}
	if len(engineCountSlice) > 1 {
		msg = fmt.Sprintf(
			"%s. hyper engine found: %s",
			msg, strings.Join(engineCountSlice, ","),
		)
	}

	return msg, nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{db: cc.MySqlDB}
}

// Register TODO
func Register() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return name, New
}
