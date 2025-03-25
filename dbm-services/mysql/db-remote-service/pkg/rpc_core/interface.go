package rpc_core

import (
	"github.com/jmoiron/sqlx"
)

// RPCEmbedInterface 实现 interface
type RPCEmbedInterface interface {
	MakeConnection(
		address string,
		user string,
		password string,
		timeout int,
		timezone string,
	) (*sqlx.DB, error)
	ParseCommand(command string) (*ParseQueryBase, error)
	IsQueryCommand(*ParseQueryBase) bool
	IsExecuteCommand(*ParseQueryBase) bool
	User() string
	Password() string
	//Close()
}
