package rpc_core

import (
	"dbm-services/mysql/db-remote-service/pkg/parser"

	"github.com/jmoiron/sqlx"
)

// RPCEmbedInterface 实现 interface
type RPCEmbedInterface interface {
	MakeConnection(
		address string,
		user string,
		password string,
		timeout int,
	) (*sqlx.DB, error)
	ParseCommand(command string) (*parser.ParseQueryBase, error)
	IsQueryCommand(*parser.ParseQueryBase) bool
	IsExecuteCommand(*parser.ParseQueryBase) bool
	User() string
	Password() string
}
