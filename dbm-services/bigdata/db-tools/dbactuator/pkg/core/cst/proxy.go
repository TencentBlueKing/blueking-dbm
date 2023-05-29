package cst

// proxy related
const (
	ProxyAdminPortInc = 1000
	// string array, split by comma
	// 初始化mysql会增加这个账户
	ProxyUserMonitorAccessAll = "MONITOR@%"
	// Proxy
	ProxyInstallPath             = "/usr/local/mysql-proxy"
	DefaultProxyDataRootPath     = "/data"
	AlterNativeProxyDataRootPath = "/data1"
	DefaultProxyCnfName          = "/etc/proxy.cnf"
	DefaultProxyUserCnfName      = "/etc/proxy_user.cnf"
	DefaultAdminScripyLua        = "/usr/local/mysql-proxy/lib/mysql-proxy/lua/admin.lua"
	DefaultBackend               = "1.1.1.1:3306"
	DefaultProxyLogBasePath      = "mysql-proxy"
)
