package scenesnapshot

/*
└> tar -tvf processlist.20231130.tar
-rw-------  0 0      0        1040  1  1  1970 20231130121345
-rw-------  0 0      0        1040  1  1  1970 20231130121547
-rw-------  0 0      0        1040  1  1  1970 20231130121932

└> tar xfO processlist.20231130.tar 20231130121932
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
|  ID   | USER |       HOST        | DB | COMMAND | TIME |   STATE   |              INFO              |
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
| 74590 | root | 10.45.39.34:54219 |    | Query   |    0 | executing | SELECT ID, USER,               |
|       |      |                   |    |         |      |           | HOST, DB, COMMAND,             |
|       |      |                   |    |         |      |           | TIME, STATE, INFO FROM         |
|       |      |                   |    |         |      |           | INFORMATION_SCHEMA.PROCESSLIST |
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
| 74572 | root | 10.45.39.34:62014 |    | Sleep   | 2865 |           |                                |
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
*/

import (
	"os"
	"path/filepath"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

var executable string
var sceneBase string

var name = "scene-snapshot"

func init() {
	executable, _ = os.Executable()
	sceneBase = filepath.Join(
		filepath.Dir(executable),
		"scenes",
	)

	_ = os.MkdirAll(sceneBase, 0755)
}

type Checker struct {
	db *sqlx.DB
}

func (c *Checker) Run() (msg string, err error) {
	err = processListScene(c.db)
	if err != nil {
		return "", err
	}

	err = engineInnodbStatusScene(c.db)
	if err != nil {
		return "", err
	}

	return "", nil
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db: cc.MySqlDB,
	}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}
