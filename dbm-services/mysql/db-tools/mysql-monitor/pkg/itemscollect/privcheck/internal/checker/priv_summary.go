package checker

type userPrivSummary struct {
	Username          string                      `json:"username"`
	HostPrivSummaries map[string]*hostPrivSummary `json:"host_priv_summaries"`
}

type hostPrivSummary struct {
	Host            string                    `json:"host"`
	Password        string                    `json:"password"`
	DBPrivSummaries map[string]*dbPrivSummary `json:"db_priv_summaries"`
}

type dbPrivSummary struct {
	DBName             string                       `json:"db_name"`
	WithGrantOption    bool                         `json:"with_grant_option"`
	TablePrivSummaries map[string]*tablePrivSummary `json:"table_priv_summaries"`
}

type tablePrivSummary struct {
	TableName  string   `json:"table_name"`
	Privileges []string `json:"privileges"`
}
