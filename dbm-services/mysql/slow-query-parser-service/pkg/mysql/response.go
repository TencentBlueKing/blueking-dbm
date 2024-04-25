package mysql

// Response TODO
type Response struct {
	Command         string `json:"command"`
	QueryString     string `json:"query_string"`
	QueryDigestText string `json:"query_digest_text"`
	QueryDigestMd5  string `json:"query_digest_md5"`
	DbName          string `json:"db_name"`
	TableName       string `json:"table_name"`
	QueryLength     int    `json:"query_length"`
}
