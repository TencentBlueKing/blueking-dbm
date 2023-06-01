// Package checker 检查库
package checker

import (
	"database/sql"
	"fmt"
	"os"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/reporter"

	_ "github.com/go-sql-driver/mysql" // mysql
	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slices"
	"golang.org/x/exp/slog"
)

// NewChecker 新建检查器
func NewChecker(mode config.CheckMode) (*Checker, error) {
	if mode == config.GeneralMode {
		err := os.MkdirAll(config.ChecksumConfig.ReportPath, 0755)
		if err != nil {
			slog.Error("new checker create report path", err)
			return nil, err
		}
	}

	checker := &Checker{
		Config:   config.ChecksumConfig,
		reporter: reporter.NewReporter(config.ChecksumConfig),
		Mode:     mode,
	}

	// checker 需要一个序列化器方便打日志

	splitR := strings.Split(checker.Config.PtChecksum.Replicate, ".")
	checker.resultDB = splitR[0]
	checker.resultTbl = splitR[1]
	checker.resultHistoryTable = fmt.Sprintf("%s_history", splitR[1])

	if err := checker.connect(); err != nil {
		slog.Error("connect host", err)
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

		if err := checker.validateHistoryTable(); err != nil {
			return nil, err
		}
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
			r.resultDB,
			time.Local.String(),
		),
	)
	return err
}

func (r *Checker) validateSlaves() error {
	if len(r.Config.Slaves) < 1 {
		err := fmt.Errorf("demand checksum need at least 1 slave")
		slog.Error("validate slaves counts", err)
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
			slog.Error("validate slaves connect", err)
			return err
		}
	}
	return nil
}

func (r *Checker) prepareDsnsTable() error {
	_, err := r.db.Exec(`DROP TABLE IF EXISTS dsns`)
	if err != nil {
		slog.Error("drop exists dsns table", err)
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
		slog.Error("create dsns table", err)
		return err
	}

	for _, slave := range r.Config.Slaves {
		_, err := r.db.Exec(
			`INSERT INTO dsns (dsn) VALUES (?)`,
			fmt.Sprintf(`h=%s,u=%s,p=%s,P=%d`, slave.Ip, slave.User, slave.Password, slave.Port),
		)
		if err != nil {
			slog.Error("add slave dsn record", err)
			return err
		}
	}
	return nil
}

func (r *Checker) validateHistoryTable() error {
	r.hasHistoryTable = false

	var _r interface{}
	err := r.db.Get(
		&_r,
		`SELECT 1 FROM INFORMATION_SCHEMA.TABLES `+
			`WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND TABLE_TYPE='BASE TABLE'`,
		r.resultDB,
		r.resultHistoryTable,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			slog.Info("history table not found")
			if r.Config.InnerRole == config.RoleSlave {
				slog.Info("no need create history table", slog.String("inner role", string(r.Config.InnerRole)))
				return nil
			} else {
				slog.Info("create history table", slog.String("inner role", string(r.Config.InnerRole)))

				err := r.db.Get(
					&_r,
					`SELECT 1 FROM INFORMATION_SCHEMA.TABLES `+
						`WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND TABLE_TYPE='BASE TABLE'`,
					r.resultDB,
					r.resultTbl,
				)

				if err != nil {
					if err == sql.ErrNoRows {
						slog.Info("checksum result table not found")
						return nil
					} else {
						slog.Error("try to find checksum result table failed", err)
						return err
					}
				}

				_, err = r.db.Exec(
					fmt.Sprintf(
						`CREATE TABLE IF NOT EXISTS %s LIKE %s`,
						r.resultHistoryTable,
						r.resultTbl,
					),
				)
				if err != nil {
					slog.Error("create history table", err)
					return err
				}
				_, err = r.db.Exec(
					fmt.Sprintf(
						`ALTER TABLE %s ADD reported int default 0, `+
							`ADD INDEX idx_reported(reported), `+
							`DROP PRIMARY KEY, `+
							`MODIFY ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP, `+
							`ADD PRIMARY KEY(master_ip, master_port, db, tbl, chunk, ts)`,
						r.resultHistoryTable,
					),
				)
				if err != nil {
					slog.Error("add column and index to history table", err)
					return err
				}
			}
		} else {
			slog.Error("check history table exists", err)
			return err
		}
	}
	r.hasHistoryTable = true

	/*
		1. 对比结果表和历史表结构, 历史表应该多出一个 reported int default 0
		2. 历史表主键检查
	*/
	var diffColumn struct {
		TableName       string `db:"TABLE_NAME"`
		ColumnName      string `db:"COLUMN_NAME"`
		OrdinalPosition int    `db:"ORDINAL_POSITION"`
		DataType        string `db:"DATA_TYPE"`
		ColumnType      string `db:"COLUMN_TYPE"`
		RowCount        int    `db:"ROW_COUNT"`
	}
	err = r.db.Get(
		&diffColumn,
		fmt.Sprintf(
			`SELECT `+
				`TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, COLUMN_TYPE, COUNT(1) as ROW_COUNT `+
				`FROM INFORMATION_SCHEMA.COLUMNS WHERE `+
				`TABLE_SCHEMA = '%s' AND TABLE_NAME in ('%s', '%s') `+
				`GROUP BY COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, COLUMN_TYPE HAVING ROW_COUNT <> 2`,
			r.resultDB,
			r.resultTbl,
			r.resultHistoryTable,
		),
	)
	if err != nil {
		slog.Error("compare result table column", err)
		return err
	}

	if diffColumn.TableName != r.resultHistoryTable ||
		diffColumn.ColumnName != "reported" ||
		diffColumn.DataType != "int" {
		err = fmt.Errorf("%s need column as 'reported int default 0'", r.resultHistoryTable)
		slog.Error("check history table reported column", err)
		return nil
	}

	var pkColumns []string
	err = r.db.Select(
		&pkColumns,
		fmt.Sprintf(
			`SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.STATISTICS `+
				`WHERE TABLE_SCHEMA = '%s' AND TABLE_NAME = '%s' AND INDEX_NAME = 'PRIMARY' `+
				`ORDER BY SEQ_IN_INDEX`,
			r.resultDB,
			r.resultHistoryTable,
		),
	)
	if err != nil {
		slog.Error("check history table primary key", err)
		return err
	}

	if slices.Compare(pkColumns, []string{"master_ip", "master_port", "db", "tbl", "chunk", "ts"}) != 0 {
		err = fmt.Errorf("history table must has primary as (master_ip, master_port, db, tbl, chunk, ts])")
		slog.Error("check history table primary key", err)
		return err
	}

	return nil
}
