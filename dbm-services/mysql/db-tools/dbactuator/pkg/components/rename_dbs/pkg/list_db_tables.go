package pkg

import (
	"context"
	"time"

	"github.com/jmoiron/sqlx"
)

func ListDBTables(conn *sqlx.Conn, dbName string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var tables []string
	err := conn.SelectContext(
		ctx,
		&tables,
		`SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_TYPE = 'BASE TABLE'`,
		dbName,
	)
	if err != nil {
		return nil, err
	}
	return tables, nil
}
