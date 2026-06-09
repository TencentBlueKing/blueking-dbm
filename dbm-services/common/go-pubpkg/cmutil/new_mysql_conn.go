package cmutil

import (
	"database/sql"
	"fmt"
	"net/url"
	"strings"

	"github.com/samber/lo"
	"github.com/spf13/cast"
)

type InstanceDsn struct {
	User             string                 `yaml:"user"`
	Password         string                 `yaml:"password"`
	Address          string                 `yaml:"address"`
	Database         string                 `yaml:"database"`
	Charset          string                 `yaml:"charset"`
	SessionVariables map[string]interface{} `yaml:"session_variables" mapstructure:"session_variables"`
}

// GetConn 内置 var: charset,parseTime,loc,time_zone
func GetConn(dsn *InstanceDsn, sessionVars map[string]interface{}) (db *sql.DB, err error) {
	if sessionVars == nil {
		sessionVars = map[string]interface{}{}
	}
	dsn.SessionVariables = lo.Assign(sessionVars, dsn.SessionVariables)
	sessionParams := toUrlParams(dsn.SessionVariables)
	if dsn.Charset == "" {
		dsn.Charset = "utf8mb4"
	}
	//slog.Info("session variables", slog.String("db", dsn.Address), slog.Any("sessionVars", dsn.SessionVariables))

	dsnUrl := fmt.Sprintf("%s:%s@tcp(%s)/%s?charset=%s&%s",
		dsn.User,
		dsn.Password,
		dsn.Address,
		dsn.Database,
		dsn.Charset,
		strings.Join(sessionParams, "&"),
	)

	dbc, err := sql.Open("mysql", dsnUrl)
	if err != nil {
		//log.Fatalf("connect to mysql failed %s", err.Error())
		return nil, err
	}
	return dbc, nil
}

func toUrlParams(sessionVars map[string]interface{}) []string {
	params := []string{}
	for k, v := range sessionVars {
		if val := cast.ToString(v); strings.Contains(val, "%") {
			params = append(params, fmt.Sprintf("%s=%s", k, val))
		} else {
			params = append(params, fmt.Sprintf("%s=%s", k, url.QueryEscape(val)))
		}
	}
	return params
}
