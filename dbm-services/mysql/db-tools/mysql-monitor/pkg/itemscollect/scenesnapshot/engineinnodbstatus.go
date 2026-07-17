package scenesnapshot

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"fmt"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/scenesnapshot/internal/archivescenes"
)

type engineInnodbStatus struct {
	Type   string `db:"Type"`
	Name   string `db:"Name"`
	Status string `db:"Status"`
}

var engineInnodbStatusName = "engine-innodb-status"

func engineInnodbStatusScene(db *pkg.MySQLMonitorDBH) error {
	err := archivescenes.DeleteOld(engineInnodbStatusName, sceneBase, 1)
	if err != nil {
		return err
	}

	res, err := queryEngineInnodbStatus(db)
	if err != nil {
		return err
	}

	content := fmt.Sprintf("Type:%s\nName:%s\nStatus:%s", res[0].Type, res[0].Name, res[0].Status)

	err = archivescenes.Write(engineInnodbStatusName, sceneBase, []byte(content))
	if err != nil {
		return err
	}

	return nil
}

func queryEngineInnodbStatus(db *pkg.MySQLMonitorDBH) (res []*engineInnodbStatus, err error) {
	err = db.Select(
		&res,
		`SHOW ENGINE INNODB STATUS`,
	)
	if err != nil {
		return nil, err
	}

	return
}
