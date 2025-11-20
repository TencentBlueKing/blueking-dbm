package impl

import "github.com/jmoiron/sqlx"

func Clean(db *sqlx.DB, conn *sqlx.Conn, connId int64) {
	if connId != 0 {
		_, _ = db.Exec(`KILL ?`, connId)
	}

	if conn != nil {
		_ = conn.Close()
	}

	if db != nil {
		_ = db.Close()
	}
}
