package atommongodb

// NsFilterArg MongoDB Namespace过滤参数
type NsFilterArg struct {
	DbList        []string `json:"db_patterns"`
	IgnoreDbList  []string `json:"ignore_dbs"`
	ColList       []string `json:"table_patterns"`
	IgnoreColList []string `json:"ignore_tables"`
}
