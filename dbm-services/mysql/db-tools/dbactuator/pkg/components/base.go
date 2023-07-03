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

// GetAllSysAccount TODO
func (g *RuntimeAccountParam) GetAllSysAccount() (accounts []string) {
	accounts = append(accounts, g.AdminUser)
	accounts = append(accounts, g.DbBackupUser)
	accounts = append(accounts, g.MonitorAccessAllUser)
	accounts = append(accounts, g.MonitorUser)
	accounts = append(accounts, g.ReplUser)
	accounts = append(accounts, g.YwUser)
	accounts = append(accounts, g.TdbctlUser)
	return
}

// GetAccountRepl TODO
func GetAccountRepl(g *GeneralParam) MySQLReplAccount {
	Repl := MySQLReplAccount{}
	switch {
	case g == nil:
		return Repl
	case g.RuntimeAccountParam == RuntimeAccountParam{}:
		return Repl
	case g.RuntimeAccountParam.MySQLAccountParam == MySQLAccountParam{}:
		return Repl
	default:
		return g.RuntimeAccountParam.MySQLReplAccount
	}
}
