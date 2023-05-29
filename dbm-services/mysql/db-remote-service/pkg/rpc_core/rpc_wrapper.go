package rpc_core

// RPCWrapper RPC 对象
type RPCWrapper struct {
	addresses      []string
	commands       []string
	user           string
	password       string
	connectTimeout int
	queryTimeout   int
	force          bool
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
	force bool,
	em RPCEmbedInterface,
) *RPCWrapper {
	return &RPCWrapper{
		addresses:         addresses,
		commands:          commands,
		user:              user,
		password:          password,
		connectTimeout:    connectTimeout,
		queryTimeout:      queryTimeout,
		force:             force,
		RPCEmbedInterface: em,
	}
}
