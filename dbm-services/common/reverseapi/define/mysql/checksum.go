package mysql

type ChecksumConfig struct {
	BkBizId        int      `json:"bk_biz_id"`
	IP             string   `json:"ip"`
	Port           int      `json:"port"`
	Role           string   `json:"role"`
	ClusterId      int      `json:"cluster_id"`
	ImmuteDomain   string   `json:"immute_domain"`
	DBModuleId     int      `json:"db_module_id"`
	Schedule       string   `json:"schedule"`
	SystemDbs      []string `json:"system_dbs"`
	ApiUrl         string   `json:"api_url"`
	StageDBHeader  string   `json:"stage_db_header"`
	RollbackDBTail string   `json:"rollback_db_tail"`
	User           string   `json:"user"`
	Password       string   `json:"password"`
}
