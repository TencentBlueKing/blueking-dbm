package scenesnapshot

import (
	"bytes"
	"database/sql"
	"log/slog"

	"github.com/jmoiron/sqlx"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/scenesnapshot/internal/archivescenes"
)

type mysqlProcess struct {
	Id      sql.NullInt64  `db:"ID" json:"id"`
	User    sql.NullString `db:"USER" json:"user"`
	Host    sql.NullString `db:"HOST" json:"host"`
	Db      sql.NullString `db:"DB" json:"db"`
	Command sql.NullString `db:"COMMAND" json:"command"`
	Time    sql.NullInt64  `db:"TIME" json:"time"`
	State   sql.NullString `db:"STATE" json:"state"`
	Info    sql.NullString `db:"INFO" json:"info"`
}

var processListName = "processlist"

func queryProcesslist(db *sqlx.DB) (res []*mysqlProcess, err error) {
	err = db.Select(
		&res,
		`SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO FROM INFORMATION_SCHEMA.PROCESSLIST`,
	)
	if err != nil {
		slog.Error("show full processlist", slog.String("error", err.Error()))
		return nil, err
	}

	return
}

func processListScene(db *sqlx.DB) error {
	err := archivescenes.DeleteOld(processListName, sceneBase, 1)
	if err != nil {
		return err
	}

	processList, err := queryProcesslist(db)
	if err != nil {
		return err
	}

	var b bytes.Buffer
	table := tablewriter.NewWriter(&b)
	table.SetAutoWrapText(true)
	table.SetRowLine(true)
	table.SetAutoFormatHeaders(false)
	table.SetHeader([]string{"ID", "USER", "HOST", "DB", "COMMAND", "TIME", "STATE", "INFO"})

	for _, p := range processList {
		table.Append([]string{
			cast.ToString(p.Id.Int64),
			p.User.String,
			p.Host.String,
			p.Db.String,
			p.Command.String,
			cast.ToString(p.Time.Int64),
			p.State.String,
			p.Info.String,
		})
	}

	table.Render()

	err = archivescenes.Write(processListName, sceneBase, b.Bytes())
	if err != nil {
		return err
	}

	return nil
}
