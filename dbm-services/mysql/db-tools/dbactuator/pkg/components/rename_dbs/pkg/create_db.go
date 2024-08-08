package pkg

import (
	"context"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

func CreateDB(conn *sqlx.Conn, dbName string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err := conn.ExecContext(
		ctx,
		fmt.Sprintf("CREATE DATABASE IF NOT EXISTS %s", dbName),
	)
	return err
}
