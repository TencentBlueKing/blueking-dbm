package mysql

import (
	"strings"

	"github.com/samber/lo"
)

// Response TODO
type Response struct {
	Command         string      `json:"command"`
	QueryString     string      `json:"query_string"`
	QueryDigestText string      `json:"query_digest_text"`
	QueryDigestMd5  string      `json:"query_digest_md5"`
	DbName          string      `json:"db_name"`
	TableName       string      `json:"table_name"`
	TableReferences QueryTables `json:"-"`
	HasSubquery     bool        `json:"has_subquery"`
	QueryLength     int         `json:"query_length"`
}

type QueryTables []*TableRef

func (q *QueryTables) String() string {
	parts := make([]string, 0, len(*q))
	for _, t := range *q {
		parts = append(parts, t.String())
	}
	return strings.Join(lo.Uniq(parts), ",")
}

type TableRef struct {
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}

func (t *TableRef) String() string {
	if t.DbName == "" {
		return t.TableName
	}
	return t.DbName + "." + t.TableName
}
