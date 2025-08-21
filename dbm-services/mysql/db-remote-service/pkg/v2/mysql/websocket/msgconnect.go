package websocket

import (
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
	"encoding/json"

	"github.com/jmoiron/sqlx"
)

func msgConnect(b []byte) (*sqlx.DB, *sqlx.Conn, int64, error) {
	wcr := WSConnectRequest{}
	err := json.Unmarshal(b, &wcr)
	if err != nil {
		return nil, nil, 0, err
	}
	return impl.Prepare(
		wcr.Address, config.RuntimeConfig.WebConsoleUser, config.RuntimeConfig.WebConsolePassword,
		wcr.Timezone, wcr.Charset, wcr.Timeout,
	)
}
