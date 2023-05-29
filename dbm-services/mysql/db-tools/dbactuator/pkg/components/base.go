package components

// BaseInputParam TODO
type BaseInputParam struct {
	GeneralParam *GeneralParam `json:"general"`
	ExtendParam  interface{}   `json:"extend"`
}

// GeneralParam TODO
type GeneralParam struct {
	RuntimeAccountParam RuntimeAccountParam `json:"runtime_account"`
	RuntimeExtend       RuntimeExtend       `json:"runtime_extend"`
}

// RuntimeExtend TODO
type RuntimeExtend struct {
	MySQLSysUsers []string `json:"mysql_sys_users"`
}

// RuntimeAccountParam TODO
type RuntimeAccountParam struct {
	MySQLAccountParam
	ProxyAccountParam
	TdbctlAccoutParam
}

// GetAccountRepl TODO
func GetAccountRepl(g *GeneralParam) MySQLReplAccount {
	Repl := MySQLReplAccount{}
	if g == nil {
		return Repl
	} else if &g.RuntimeAccountParam == nil {
		return Repl
	} else if &g.RuntimeAccountParam.MySQLAccountParam == nil {
		return Repl
	} else {
		return g.RuntimeAccountParam.MySQLAccountParam.MySQLReplAccount
	}
}
