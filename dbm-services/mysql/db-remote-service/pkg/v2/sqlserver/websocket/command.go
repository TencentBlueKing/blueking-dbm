package websocket

import (
	"encoding/json"
	"strings"

	"dbm-services/mysql/db-remote-service/pkg/v2/sqlserver/internal/impl"

	"github.com/jmoiron/sqlx"
)

func handleCommand(conn *sqlx.Conn, b []byte, classifier *impl.CommandClassifier) ([]byte, int64, error) {
	var wcr WSCommandRequest
	if err := json.Unmarshal(b, &wcr); err != nil {
		return nil, 0, err
	}

	if strings.TrimSpace(wcr.Command) == "" {
		return []byte(""), 0, nil
	}

	if wcr.Timeout <= 0 {
		wcr.Timeout = defaultCommandTimeout
	}

	return impl.DoSQL(conn, wcr.Command, wcr.Timeout, classifier)
}
