package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"encoding/json"

	"regexp"

	"github.com/antlr4-go/antlr/v4"
)

type PrivStatementType string

const (
	PrivStatementGrant  PrivStatementType = "GRANT"
	PrivStatementCreate PrivStatementType = "CREATE"
)

type GrantStatementType string

const (
	GrantStatementTypeNormal GrantStatementType = "NORMAL"
	GrantStatementTypeProxy  GrantStatementType = "PROXY"
	GrantStatementTypeRole   GrantStatementType = "ROLE"
)

type AuthOptionStruct struct {
	Username   string `json:"username"`
	AuthClause string `json:"auth_clause"`
}

type PrivListener struct {
	RawSQL        string             `json:"raw_sql"`
	StatementType PrivStatementType  `json:"statement_type"`
	GrantType     GrantStatementType `json:"grant_type"`
	// GrantStatementTypeNormal
	authOptionStrings []string            // 为了效率的版本, 只用于 deep equal, 不要参与 sql 生成
	AuthOptions       []*AuthOptionStruct `json:"auth_options"` // create user 和 grant 都可能有
	PrivObject        string              `json:"priv_object"`  // [table, function, procedure], 好像大部分时间没啥用
	DBName            string              `json:"db_name"`
	TableName         string              `json:"table_name"`
	Privileges        string              `json:"privileges"`        // mysql 保证顺序
	WithGrantOption   bool                `json:"with_grant_option"` // grant proxy 也有这个
	ResourceOptions   []string            `json:"resource_option"`
	TlsNone           *bool               `json:"tls_none"`
	TlsOptions        []string            `json:"tls_options"` // create user
	RoleOption        string              `json:"role_option"`
	// GrantStatementTypeRole
	WithAdminOption bool     `json:"with_admin_option"`
	FromUserOrIds   []string `json:"from_user_or_ids"`
	ToUserOrIds     []string `json:"to_user_or_ids"`
	// GrantStatementTypeProxy
	FromUsername string   `json:"from_username"`
	ToUsernames  []string `json:"to_usernames"`
	// Create
	PasswordLockOption string `json:"option"`

	tokenStream *antlr.CommonTokenStream
	parsing.BaseMariaDBParserListener
}

func (c *PrivListener) String() string {
	b, _ := json.Marshal(c)
	return string(b)
}

func (c *PrivListener) Copy() *PrivListener {
	return &PrivListener{
		RawSQL:        c.RawSQL,
		StatementType: c.StatementType,
		GrantType:     c.GrantType,
		AuthOptions: func() (res []*AuthOptionStruct) {
			for _, ele := range c.AuthOptions {
				res = append(res, &AuthOptionStruct{Username: ele.Username, AuthClause: ele.AuthClause})
			}
			return
		}(),
		PrivObject:         c.PrivObject,
		DBName:             c.DBName,
		TableName:          c.TableName,
		Privileges:         c.Privileges,
		WithGrantOption:    c.WithGrantOption,
		ResourceOptions:    c.ResourceOptions,
		TlsNone:            c.TlsNone,
		TlsOptions:         c.TlsOptions,
		RoleOption:         c.RoleOption,
		WithAdminOption:    c.WithAdminOption,
		FromUserOrIds:      c.FromUserOrIds,
		ToUserOrIds:        c.ToUserOrIds,
		FromUsername:       c.FromUsername,
		ToUsernames:        c.ToUsernames,
		PasswordLockOption: c.PasswordLockOption,
		tokenStream:        c.tokenStream,
	}
}

func NewPrivListener(stream *antlr.CommonTokenStream) *PrivListener {
	return &PrivListener{tokenStream: stream}
}

var withGrantOptionPattern *regexp.Regexp

func init() {
	withGrantOptionPattern = regexp.MustCompile(`(?mi)with\s+grant\s+option`)
}
