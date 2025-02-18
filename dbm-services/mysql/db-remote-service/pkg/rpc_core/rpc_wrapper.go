package rpc_core

import "log/slog"

// RPCWrapper RPC 对象
type RPCWrapper struct {
	addresses      []string
	commands       []string
	user           string
	password       string
	connectTimeout int
	queryTimeout   int
	timezone       string
	force          bool
	logger         *slog.Logger
	RPCEmbedInterface
}

// NewRPCWrapper 新建 RPC 对象
func NewRPCWrapper(
	addresses []string,
	commands []string,
	user string,
	password string,
	connectTimeout int,
	queryTimeout int,
	timezone string,
	force bool,
	em RPCEmbedInterface,
	requestId string,
) *RPCWrapper {
	w := &RPCWrapper{
		addresses:         addresses,
		commands:          commands,
		user:              user,
		password:          password,
		connectTimeout:    connectTimeout,
		queryTimeout:      queryTimeout,
		timezone:          timezone,
		force:             force,
		RPCEmbedInterface: em,
	}

	w.logger = slog.Default().With("request-id", requestId)

	return w
}
