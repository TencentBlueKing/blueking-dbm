package mysql

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"log/slog"
	"strings"
)

const privSqlBuckSize = 1000

func ImportPriv(bkCloudId int64, address string, privs []string, logger *slog.Logger) (err error) {
	createSqls, privSqls := splitSql(privs)
	e := importSqls(bkCloudId, address, createSqls, logger)
	if e != nil {
		logger.Error(
			"import mysql priv create user sql",
			slog.String("error", e.Error()),
		)
		err = errors.Join(err, e)
	} else {
		logger.Info("import mysql priv import create user success")
	}

	e = importSqls(bkCloudId, address, privSqls, logger)
	if e != nil {
		logger.Error(
			"import mysql priv import grant sql",
			slog.String("error", e.Error()),
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
		"import mysql priv sql",
		slog.Int("buck size", privSqlBuckSize),
		slog.Int("total sqls", len(sqls)),
	)
	leftCount := len(sqls)
	for _, sql := range sqls {
		bulkSqls = append(bulkSqls, sql)
		if len(bulkSqls) > privSqlBuckSize {
			e := doImport(bkCloudId, address, bulkSqls, logger)
			if e != nil {
				logger.Error(
					"import mysql priv sql one buck",
					slog.String("error", e.Error()),
				)
				err = errors.Join(err, e)
			}
			leftCount -= privSqlBuckSize
			logger.Info(
				"import mysql priv sql one buck success",
				slog.Int("sql left", leftCount),
			)
			bulkSqls = []string{}
		}
	}

	if len(bulkSqls) > 0 {
		e := doImport(bkCloudId, address, bulkSqls, logger)
		if e != nil {
			logger.Error(
				"import mysql priv sql last buck",
				slog.String("error", e.Error()),
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
			"import priv",
			slog.String("address", address),
			slog.String("error", err.Error()),
		)
		return err
	}
	if drsRes[0].ErrorMsg != "" {
		logger.Error(
			"import priv",
			slog.String("address", address),
			slog.String("error", drsRes[0].ErrorMsg),
		)
		return errors.New(drsRes[0].ErrorMsg)
	}

	for _, cr := range drsRes[0].CmdResults {
		if cr.ErrorMsg != "" {
			logger.Error(
				"import priv",
				slog.String("address", address),
				slog.String("error", cr.ErrorMsg),
				slog.String("cms", cr.Cmd),
			)
			err = errors.Join(err, errors.New(cr.ErrorMsg))
		}
	}
	return
}
