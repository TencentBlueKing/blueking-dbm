package mysql

// Response TODO
type Response struct {
	Command         string      `json:"command"`
	QueryString     string      `json:"query_string"`
	QueryDigestText string      `json:"query_digest_text"`
	QueryDigestMd5  string      `json:"query_digest_md5"`
	DbName          string      `json:"db_name"`
	TableName       string      `json:"table_name"`
	TableReferences []*TableRef `json:"-"`
	HasSubquery     bool        `json:"has_subquery"`
	QueryLength     int         `json:"query_length"`
}

type TableRef struct {
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}

func (t *TableRef) String() string {
	return t.DbName + "." + t.TableName
}
