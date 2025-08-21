package websocket

import (
	"encoding/json"
	"errors"
	"strings"

	"github.com/jmoiron/sqlx"
)

func doMessage(db **sqlx.DB, conn **sqlx.Conn, connId *int64, msg []byte) (srs []byte, n int64, err error) {
	wbr := WSBaseRequest{}
	err = json.Unmarshal(msg, &wbr)
	if err != nil {
		return nil, 0, err
	}

	switch strings.ToUpper(wbr.RequestType) {
	case "CONNECT":
		*db, *conn, *connId, err = msgConnect(wbr.Body)
		if err != nil {
			return nil, 0, err
		}
	case "COMMAND":
		srs, n, err = msgCommand(*conn, wbr.Body)
		if err != nil {
			return nil, 0, err
		}
	default:
		return nil, 0, errors.New("invalid request type")
	}

	return srs, n, nil
}
