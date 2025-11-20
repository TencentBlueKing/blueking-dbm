package websocket

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/jmoiron/sqlx"
)

func Handler(c *gin.Context) {
	_ = config.GlobalLimiter.Wait(context.Background())

	wsUpgrader := websocket.Upgrader{
		HandshakeTimeout: 10 * time.Second,
		ReadBufferSize:   1024,
		WriteBufferSize:  1024,
	}

	ws, err := wsUpgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		c.JSON(
			http.StatusBadRequest,
			gin.H{
				"code": 1,
				"data": "",
				"msg":  err.Error(),
			})
		return
	}
	defer func() {
		_ = ws.Close()
	}()

	var db *sqlx.DB
	var conn *sqlx.Conn
	var connId int64
	defer func() {
		impl.Clean(db, conn, connId)
	}()

	for {
		mt, message, err := ws.ReadMessage()
		if err != nil {
			_ = ws.WriteMessage(websocket.TextMessage, WSResponse{
				Result:       nil,
				RowsAffected: 0,
				Error:        err.Error(),
			}.Bytes())
			return
		}

		switch mt {
		case websocket.TextMessage:
			srs, n, err := doMessage(&db, &conn, &connId, message)
			if err != nil {
				_ = ws.WriteMessage(websocket.TextMessage, []byte(err.Error()))
			} else {
				_ = ws.WriteMessage(websocket.TextMessage, WSResponse{
					Result:       srs,
					RowsAffected: n,
					Error:        "",
				}.Bytes())
			}

		case websocket.CloseMessage:
			impl.Clean(db, conn, connId)
		default:
			return
		}
	}
}
