package scenesnapshot

import (
	"bytes"
	"database/sql"
	"log/slog"

	"github.com/jedib0t/go-pretty/v6/table"
	"github.com/jedib0t/go-pretty/v6/text"
	"github.com/jmoiron/sqlx"

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
		`SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO FROM INFORMATION_SCHEMA.PROCESSLIST ORDER BY TIME DESC`,
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
	tw := table.NewWriter()
	tw.SetOutputMirror(&b)
	tw.Style().Options.SeparateRows = true
	tw.Style().Format.Header = text.FormatDefault
	tw.AppendHeader(table.Row{"ID", "USER", "HOST", "DB", "COMMAND", "TIME", "INFO", "STATE"})
	tw.SetColumnConfigs([]table.ColumnConfig{
		{Number: 7, Name: "INFO", WidthMax: 60}, // wrap text
		{Number: 8, Name: "STATE", WidthMax: 40},
	})
	//tw.SetAllowedRowLength(120)
	for _, p := range processList {
		tw.AppendRow([]interface{}{
			p.Id.Int64,
			p.User.String,
			p.Host.String,
			p.Db.String,
			p.Command.String,
			p.Time.Int64,
			p.Info.String,
			p.State.String,
		})
	}

	tw.Render()

	err = archivescenes.Write(processListName, sceneBase, b.Bytes())
	if err != nil {
		return err
	}

	return nil
}
