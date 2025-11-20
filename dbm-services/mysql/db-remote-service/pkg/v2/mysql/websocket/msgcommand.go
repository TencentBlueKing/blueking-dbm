package websocket

import (
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
	"encoding/json"
	"strings"

	"github.com/jmoiron/sqlx"
)

func msgCommand(conn *sqlx.Conn, b []byte) ([]byte, int64, error) {
	wcr := WSCommandRequest{}
	err := json.Unmarshal(b, &wcr)
	if err != nil {
		return nil, 0, err
	}

	if strings.TrimSpace(wcr.Command) == "" {
		return []byte(""), 0, nil
	}

	return impl.DoSQL(conn, wcr.Command, wcr.Timeout)
}
