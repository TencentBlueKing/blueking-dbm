package mysql

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"fmt"
	"log/slog"
	"strings"
)

const privSqlBuckSize = 1000

func ImportPriv(bkCloudId int64, address string, privs []string, logger *slog.Logger) (err error) {
	createSqls, privSqls := splitSql(privs)
	e := importSqls(bkCloudId, address, createSqls, logger)
	if e != nil {
		logger.Error(
			fmt.Sprintf("import mysql priv create user sql, err: %s", e.Error()),
		)
		err = errors.Join(err, e)
	} else {
		logger.Info("import mysql priv import create user success")
	}

	e = importSqls(bkCloudId, address, privSqls, logger)
	if e != nil {
		logger.Error(
			fmt.Sprintf("import mysql priv import grant sql, err: %s", e.Error()),
		)
		err = errors.Join(err, e)
	}

	if err != nil {
		return err
	}

	logger.Info("import mysql priv import grant success")
	return nil
}

func splitSql(privs []string) (createSqls []string, grantSqls []string) {
	for _, priv := range privs {
		priv = strings.TrimSpace(priv)
		if strings.HasPrefix(strings.ToUpper(priv), "CREATE") {
			createSqls = append(createSqls, priv)
		} else {
			grantSqls = append(grantSqls, priv)
		}
	}
	return createSqls, grantSqls
}

func importSqls(bkCloudId int64, address string, sqls []string, logger *slog.Logger) (err error) {
	var bulkSqls []string

	logger.Info(
		fmt.Sprintf("import mysql priv sql, buck size: %d, total sqls: %d", privSqlBuckSize, len(sqls)),
	)
	leftCount := len(sqls)
	for _, sql := range sqls {
		bulkSqls = append(bulkSqls, sql)
		if len(bulkSqls) > privSqlBuckSize {
			e := doImport(bkCloudId, address, bulkSqls, logger)
			if e != nil {
				logger.Error(
					fmt.Sprintf("import mysql priv sql one buck, err: %s", e.Error()),
				)
				err = errors.Join(err, e)
			}
			leftCount -= privSqlBuckSize
			logger.Info(
				fmt.Sprintf("import mysql priv sql one buck success, sql left: %d", leftCount),
			)
			bulkSqls = []string{}
		}
	}

	if len(bulkSqls) > 0 {
		e := doImport(bkCloudId, address, bulkSqls, logger)
		if e != nil {
			logger.Error(
				fmt.Sprintf("import mysql priv sql last buck, err: %s", e.Error()),
			)
			err = errors.Join(err, e)
		}

		logger.Info("import mysql priv sql last buck success")
	}

	return err
}

func doImport(bkCloudId int64, address string, sqls []string, logger *slog.Logger) (err error) {
	if len(sqls) == 0 {
		logger.Info("import mysql priv sql is empty")
		return nil
	}

	drsRes, err := drs.RPCMySQL(
		bkCloudId,
		[]string{address},
		sqls,
		//append(sqls, "FLUSH PRIVILEGES"),
		true,
		600,
	)
	if err != nil {
		logger.Error(
			fmt.Sprintf("import priv, address %s, err: %s", address, err.Error()),
		)
		return err
	}
	if drsRes[0].ErrorMsg != "" {
		logger.Error(
			fmt.Sprintf("import priv, address %s, err: %s", address, drsRes[0].ErrorMsg),
		)
		return errors.New(drsRes[0].ErrorMsg)
	}

	for _, cr := range drsRes[0].CmdResults {
		if cr.ErrorMsg != "" {
			logger.Error(
				fmt.Sprintf("import priv, address %s, cmd: %s, err: %s", address, cr.Cmd, cr.ErrorMsg),
			)
			err = errors.Join(err, errors.New(cr.ErrorMsg))
		}
	}
	return
}
