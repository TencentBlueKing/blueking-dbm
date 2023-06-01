package character_consistency

import (
	"context"
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var name = "character-consistency"

// Checker TODO
type Checker struct {
	db *sqlx.DB
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var characterSetServer string
	err = c.db.GetContext(ctx, &characterSetServer, `SELECT @@character_set_server`)
	if err != nil {
		return "", errors.Wrap(err, "get character_set_server") // ToDo 这里需要发告警么?
	}

	q, args, err := sqlx.In(
		`SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME 
					FROM INFORMATION_SCHEMA.SCHEMATA 
					WHERE DEFAULT_CHARACTER_SET_NAME <> ? AND SCHEMA_NAME NOT IN (?)`,
		characterSetServer,
		config.MonitorConfig.DBASysDbs,
	)
	if err != nil {
		return "", errors.Wrap(err, "build IN query db charset")
	}

	var res []struct {
		SchemaName    string `db:"SCHEMA_NAME"`
		SchemaCharset string `db:"DEFAULT_CHARACTER_SET_NAME"`
	}
	err = c.db.SelectContext(ctx, &res, c.db.Rebind(q), args...)
	if err != nil {
		return "", errors.Wrap(err, "query charset inconsistent dbs")
	}

	if len(res) > 0 {
		return fmt.Sprintf("%v charset inconsistent with server charset", res), nil
	} else {
		return "", nil
	}
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
