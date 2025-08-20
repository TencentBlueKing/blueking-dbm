// Package checker 检查库
package checker

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/reporter"

	_ "github.com/go-sql-driver/mysql" // mysql
	"github.com/jmoiron/sqlx"
)

// NewChecker 新建检查器
func NewChecker(mode config.CheckMode) (*Checker, error) {
	if mode == config.GeneralMode {
		err := os.MkdirAll(config.ChecksumConfig.ReportPath, 0755)
		if err != nil {
			slog.Error("new checker create report path", slog.String("error", err.Error()))
			return nil, err
		}
	}

	checker := &Checker{
		Config:   config.ChecksumConfig,
		reporter: reporter.NewReporter(config.ChecksumConfig),
		Mode:     mode,
	}

	if err := checker.connect(); err != nil {
		slog.Error("connect host", slog.String("error", err.Error()))
		return nil, err
	}

	if err := checker.ptPrecheck(); err != nil {
		return nil, err
	}

	checker.applyForceSwitchStrategy(commonForceSwitchStrategies)
	checker.applyDefaultSwitchStrategy(commonDefaultSwitchStrategies)
	checker.applyForceKVStrategy(commonForceKVStrategies)
	checker.applyDefaultKVStrategy(commonDefaultKVStrategies)

	if checker.Mode == config.GeneralMode {
		checker.applyForceSwitchStrategy(generalForceSwitchStrategies)
		checker.applyDefaultSwitchStrategy(generalDefaultSwitchStrategies)
		checker.applyForceKVStrategy(generalForceKVStrategies)
		checker.applyDefaultKVStrategy(generalDefaultKVStrategies)

		//if err := checker.validateHistoryTable(); err != nil {
		//	return nil, err
		//}
	} else {
		checker.applyForceSwitchStrategy(demandForceSwitchStrategies)
		checker.applyDefaultSwitchStrategy(demandDefaultSwitchStrategies)
		checker.applyForceKVStrategy(demandForceKVStrategies)
		checker.applyDefaultKVStrategy(demandDefaultKVStrategies)

		if err := checker.validateSlaves(); err != nil {
			return nil, err
		}

		if err := checker.prepareDsnsTable(); err != nil {
			return nil, err
		}
	}

	checker.buildCommandArgs()

	return checker, nil
}

func (r *Checker) connect() (err error) {
	r.db, err = sqlx.Connect(
		"mysql",
		fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/%s?parseTime=true&loc=%s",
			r.Config.User,
			r.Config.Password,
			r.Config.Ip,
			r.Config.Port,
			config.ResultDb,
			time.Local.String(),
		),
	)
	if err != nil {
		slog.Error("connect host", slog.String("error", err.Error()))
		return err
	}

	r.conn, err = r.db.Connx(context.Background())
	if err != nil {
		slog.Error("get conn from sqlx.db", slog.String("error", err.Error()))
		return err
	}
	_, err = r.conn.ExecContext(
		context.Background(), `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;`)
	if err != nil {
		slog.Error("set transaction isolation level", slog.String("error", err.Error()))
		return err
	}

	_, err = r.conn.ExecContext(context.Background(), `SET BINLOG_FORMAT = 'STATEMENT'`)
	if err != nil {
		slog.Error(
			"set binlog format to statement before insert fake result", slog.String("error", err.Error()))
		return err
	}

	return nil
}

func (r *Checker) validateSlaves() error {
	if len(r.Config.Slaves) < 1 {
		err := fmt.Errorf("demand checksum need at least 1 slave")
		slog.Error("validate slaves counts", slog.String("error", err.Error()))
		return err
	}

	/*
		实际是要能 select 所有库表, 但是权限不好查
		这里只查下能不能连接
	*/
	for _, slave := range r.Config.Slaves {
		_, err := sqlx.Connect(
			"mysql",
			fmt.Sprintf(
				"%s:%s@tcp(%s:%d)/",
				slave.User,
				slave.Password,
				slave.Ip,
				slave.Port,
			),
		)
		if err != nil {
			slog.Error("validate slaves connect", slog.String("error", err.Error()))
			return err
		}
	}
	return nil
}

func (r *Checker) prepareDsnsTable() error {
	_, err := r.db.Exec(`DROP TABLE IF EXISTS dsns`)
	if err != nil {
		slog.Error("drop exists dsns table", slog.String("error", err.Error()))
		return err
	}

	_, err = r.db.Exec(
		`CREATE TABLE dsns (` +
			`id int NOT NULL AUTO_INCREMENT,` +
			`parent_id int DEFAULT NULL,` +
			`dsn varchar(255) NOT NULL,` +
			`PRIMARY KEY(id)) ENGINE=InnoDB`,
	)
	if err != nil {
		slog.Error("create dsns table", slog.String("error", err.Error()))
		return err
	}

	for _, slave := range r.Config.Slaves {
		_, err := r.conn.ExecContext(
			context.Background(),
			`INSERT INTO dsns (dsn) VALUES (?)`,
			fmt.Sprintf(`h=%s,u=%s,p=%s,P=%d`, slave.Ip, slave.User, slave.Password, slave.Port),
		)
		if err != nil {
			slog.Error("add slave dsn record", slog.String("error", err.Error()))
			return err
		}
	}
	return nil
}
