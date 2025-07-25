package mysql

type ChecksumConfig struct {
	BkBizId      int    `json:"bk_biz_id"`
	IP           string `json:"ip"`
	Port         int    `json:"port"`
	Role         string `json:"role"`
	ClusterId    int    `json:"cluster_id"`
	ImmuteDomain string `json:"immute_domain"`
	DBModuleId   int    `json:"db_module_id"`
	Schedule     string `json:"schedule"`
	ApiUrl       string `json:"api_url"`
	User         string `json:"user"`
	Password     string `json:"password"`
	Enable       *bool  `json:"enable"`
	Filter       struct {
		Databases            []string `json:"databases"`
		IgnoreDatabases      []string `json:"ignore_databases"`
		Tables               []string `json:"tables"`
		IgnoreTables         []string `json:"ignore_tables"`
		DatabasesRegex       []string `json:"databases_regex"`
		IgnoreDatabasesRegex []string `json:"ignore_databases_regex"`
		TablesRegex          []string `json:"tables_regex"`
		IgnoreTablesRegex    []string `json:"ignore_tables_regex"`
	} `json:"filter"`
	Runtime string `json:"run-time"`
}
