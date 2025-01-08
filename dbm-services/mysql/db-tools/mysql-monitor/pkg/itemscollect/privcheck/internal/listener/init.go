package listener

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/parsing"

	"regexp"

	"github.com/antlr4-go/antlr/v4"
)

type PrivListener struct {
	RawSQL          string   `json:"raw_sql"`
	RawUsername     string   `json:"raw_username"`
	Username        string   `json:"username"`
	Host            string   `json:"host"`
	Password        string   `json:"password"`
	DBName          string   `json:"db_name"`
	TableName       string   `json:"table_name"`
	Privileges      []string `json:"privileges"`
	WithGrantOption bool     `json:"with_grant_option"`
	parsing.BaseMySqlParserListener
	tokenStream  *antlr.CommonTokenStream
	IsGrantPriv  bool
	IsCreateUser bool
}

func NewPrivListener(stream *antlr.CommonTokenStream) *PrivListener {
	return &PrivListener{tokenStream: stream}
}

var withGrantOptionPattern *regexp.Regexp

func init() {
	withGrantOptionPattern = regexp.MustCompile(`(?mi)with\s+grant\s+option`)
}
