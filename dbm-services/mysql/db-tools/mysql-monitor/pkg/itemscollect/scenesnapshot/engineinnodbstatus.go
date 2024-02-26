package scenesnapshot

import (
	"context"
	"fmt"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/scenesnapshot/internal/tarball"
)

type engineInnodbStatus struct {
	Type   string `db:"Type"`
	Name   string `db:"Name"`
	Status string `db:"Status"`
}

var engineInnodbStatusName = "engine-innodb-status"

func engineInnodbStatusScene(db *sqlx.DB) error {
	err := tarball.DeleteOld(engineInnodbStatusName, sceneBase, 1)
	if err != nil {
		return err
	}

	res, err := queryEngineInnodbStatus(db)
	if err != nil {
		return err
	}

	content := fmt.Sprintf("Type:%s\nName:%s\nStatus:%s", res[0].Type, res[0].Name, res[0].Status)

	err = tarball.Write(engineInnodbStatusName, sceneBase, []byte(content))
	if err != nil {
		return err
	}

	return nil
}

func queryEngineInnodbStatus(db *sqlx.DB) (res []*engineInnodbStatus, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	err = db.SelectContext(
		ctx,
		&res,
		`SHOW ENGINE INNODB STATUS`,
	)
	if err != nil {
		return nil, err
	}

	return
}
