// Package checker 检查库
package checker

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"

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
		Config: config.ChecksumConfig,
		//reporter: reporter.NewReporter(config.ChecksumConfig),
		Mode: mode,
	}

	// checker 需要一个序列化器方便打日志

	splitR := strings.Split(checker.Config.PtChecksum.Replicate, ".")
	checker.resultDB = splitR[0]
	checker.resultTbl = splitR[1]
	checker.resultHistoryTable = fmt.Sprintf("%s_history", splitR[1])

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
	} else if checker.Mode == config.DemandMode {
		// demand 侧 pt 参数见 init.go demandForce* / demandDefault*（replicate-check、max-lag 等）
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
	} else {
		checker.applyForceSwitchStrategy(dtsForceSwitchStrategies)
		checker.applyDefaultSwitchStrategy(dtsDefaultSwitchStrategies)
		checker.applyForceKVStrategy(dtsForceKVStrategies)
		checker.applyDefaultKVStrategy(dtsDefaultKVStrategies)
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
		context.Background(), `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;`,
	)
	if err != nil {
		slog.Error("set transaction isolation level", slog.String("error", err.Error()))
		return err
	}

	_, err = r.conn.ExecContext(context.Background(), `SET BINLOG_FORMAT = 'STATEMENT'`)
	if err != nil {
		slog.Error(
			"set binlog format to statement before insert fake result", slog.String("error", err.Error()),
		)
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
	//for _, slave := range r.Config.Slaves {
	//	_, err := sqlx.Connect(
	//		"mysql",
	//		fmt.Sprintf(
	//			"%s:%s@tcp(%s:%d)/",
	//			slave.User,
	//			slave.Password,
	//			slave.Ip,
	//			slave.Port,
	//		),
	//	)
	//	if err != nil {
	//		slog.Error("validate slaves connect", slog.String("error", err.Error()))
	//		return err
	//	}
	//}
	return nil
}

//func (r *Checker) prepareReplicateTable(mode config.CheckMode) error {
//	if mode == config.GeneralMode && !r.Config.Enable {
//		slog.Info("checksum disabled, skip create replicate table")
//		return nil
//	}
//
//	ctSql := fmt.Sprintf(
//		`CREATE TABLE IF NOT EXISTS %s.%s (
//    master_ip      CHAR(32)     default '0.0.0.0',
//    master_port    INT          default 3306,
//    db             CHAR(64)     NOT NULL,
//    tbl            CHAR(64)     NOT NULL,
//    chunk          INT          NOT NULL,
//    chunk_time     FLOAT            NULL,
//    chunk_index    VARCHAR(200)     NULL,
//    lower_boundary BLOB             NULL,
//    upper_boundary BLOB             NULL,
//    this_crc       CHAR(40)     NOT NULL,
//    this_cnt       INT          NOT NULL,
//    master_crc     CHAR(40)         NULL,
//    master_cnt     INT              NULL,
//    ts             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
//    PRIMARY KEY (master_ip, master_port, db, tbl, chunk),
//    INDEX db_tbl_chunk (db, tbl, chunk),
//    INDEX ts_db_tbl (ts, db, tbl)
// ) ENGINE=InnoDB DEFAULT CHARSET=utf8;`, r.resultDB, r.resultTbl,
//	)
//	_, err := r.db.Exec(ctSql)
//	if err != nil {
//		slog.Error("prepare replicate table error", slog.String("error", err.Error()))
//		return err
//	}
//	return nil
//}

func (r *Checker) prepareDsnsTable() error {
	_, err := r.db.Exec(fmt.Sprintf(`DROP TABLE IF EXISTS %s.dsns`, r.resultDB))
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
			fmt.Sprintf(`INSERT INTO %s.dsns (dsn) VALUES (?)`, r.resultDB),
			fmt.Sprintf(`h=%s,u=%s,p=%s,P=%d`, slave.Ip, slave.User, slave.Password, slave.Port),
		)
		if err != nil {
			slog.Error("add slave dsn record", slog.String("error", err.Error()))
			return err
		}
	}
	return nil
}
