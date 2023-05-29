package util

import (
	"fmt"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

// ConnectionParam TODO
type ConnectionParam struct {
	Addr     string `json:"addr"`
	Dbname   string `json:"dbname"`
	Username string `json:"username"`
	Password string `json:"password"`
}

// ConnectDB TODO
func (c *ConnectionParam) ConnectDB() (*sqlx.DB, error) {
	return ConnectSqlx(c.Addr, c.Username, c.Password, c.Dbname)
}

// ConnectSqlx TODO
func ConnectSqlx(user, password, address, dbName string) (*sqlx.DB, error) {

	config := fmt.Sprintf("%s:%s@tcp(%s)/%s?multiStatements=true&timeout=10s",
		user,
		password,
		address,
		dbName)
	db, err := sqlx.Connect("mysql", config)
	if err != nil {
		slog.Error(fmt.Sprintf("Database connection failed. user: %s, address: %v", user, address), err)
		return nil, err
	}
	if err := db.Ping(); err != nil {
		slog.Error("Database ping failed.", err)
		return nil, err
	}
	return db, nil
}
