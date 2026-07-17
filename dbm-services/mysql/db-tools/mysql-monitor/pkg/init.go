package pkg

import "github.com/jmoiron/sqlx"

type MySQLMonitorDBH struct {
	*sqlx.DB
	Host string `json:"host"`
	Port int    `json:"port"`
	User string `json:"user"`
}
