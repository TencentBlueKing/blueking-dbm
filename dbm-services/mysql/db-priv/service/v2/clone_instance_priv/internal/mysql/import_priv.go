package mysql

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"errors"
	"log/slog"
	"strings"
)

const privSqlBuckSize = 1000

func ImportPriv(bkCloudId int64, address string, privs []string) (err error) {
	createSqls, privSqls := splitSql(privs)
	e := importSqls(bkCloudId, address, createSqls)
	if e != nil {
		slog.Error(
			"import mysql priv create user sql",
			slog.String("error", e.Error()),
		)
		err = errors.Join(err, e)
	} else {
		slog.Info("import mysql priv import create user success")
	}

	e = importSqls(bkCloudId, address, privSqls)
	if e != nil {
		slog.Error(
			"import mysql priv import grant sql",
			slog.String("error", e.Error()),
		)
		err = errors.Join(err, e)
	}

	if err != nil {
		return err
	}

	slog.Info("import mysql priv import grant success")
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

func importSqls(bkCloudId int64, address string, sqls []string) (err error) {
	var bulkSqls []string

	slog.Info(
		"import mysql priv sql",
		slog.Int("buck size", privSqlBuckSize),
		slog.Int("total sqls", len(sqls)),
	)
	leftCount := len(sqls)
	for _, sql := range sqls {
		bulkSqls = append(bulkSqls, sql)
		if len(bulkSqls) > privSqlBuckSize {
			e := doImport(bkCloudId, address, bulkSqls)
			if e != nil {
				slog.Error(
					"import mysql priv sql one buck",
					slog.String("error", e.Error()),
				)
				err = errors.Join(err, e)
			}
			leftCount -= privSqlBuckSize
			slog.Info(
				"import mysql priv sql one buck success",
				slog.Int("sql left", leftCount),
			)
			bulkSqls = []string{}
		}
	}

	if len(bulkSqls) > 0 {
		e := doImport(bkCloudId, address, bulkSqls)
		if e != nil {
			slog.Error(
				"import mysql priv sql last buck",
				slog.String("error", e.Error()),
			)
			err = errors.Join(err, e)
		}

		slog.Info("import mysql priv sql last buck success")
	}

	return err
}

func doImport(bkCloudId int64, address string, sqls []string) (err error) {
	drsRes, err := drs.RPCMySQL(
		bkCloudId,
		[]string{address},
		append(sqls, "FLUSH PRIVILEGES"),
		true,
		600,
	)
	if err != nil {
		slog.Error(
			"import priv",
			slog.String("address", address),
			slog.String("error", err.Error()),
		)
		return err
	}
	if drsRes[0].ErrorMsg != "" {
		slog.Error(
			"import priv",
			slog.String("address", address),
			slog.String("error", drsRes[0].ErrorMsg),
		)
		return errors.New(drsRes[0].ErrorMsg)
	}

	for _, cr := range drsRes[0].CmdResults {
		if cr.ErrorMsg != "" {
			slog.Error(
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
