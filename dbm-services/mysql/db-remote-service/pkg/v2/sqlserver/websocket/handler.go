package websocket

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/mysql/db-remote-service/pkg/apm"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/sqlserver/internal/impl"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/jmoiron/sqlx"
)

const (
	pingInterval          = 30 * time.Second
	idleTimeout           = 10 * time.Minute
	pongWait              = 60 * time.Second
	defaultConnectTimeout = 2
	defaultCommandTimeout = 600
	maxWSMessageSize      = 1 << 20 // 1 MB
	commandAcquireTimeout = 30 * time.Second
)

type wsSession struct {
	ws         *websocket.Conn
	writeMu    sync.Mutex
	done       chan struct{}
	bgWG       sync.WaitGroup
	idleTimer  *time.Timer
	db         *sqlx.DB
	conn       *sqlx.Conn
	user       string
	password   string
	classifier *impl.CommandClassifier
}

func (s *wsSession) writeError(errMsg string) {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	_ = s.ws.WriteMessage(websocket.TextMessage, WSResponse{
		Result:       nil,
		RowsAffected: 0,
		Error:        errMsg,
	}.Bytes())
}

func (s *wsSession) writeResponse(result []byte, rowsAffected int64) {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	_ = s.ws.WriteMessage(websocket.TextMessage, WSResponse{
		Result:       result,
		RowsAffected: rowsAffected,
		Error:        "",
	}.Bytes())
}

func (s *wsSession) startHeartbeat() {
	defer s.bgWG.Done()

	ticker := time.NewTicker(pingInterval)
	defer ticker.Stop()

	for {
		select {
		case <-s.done:
			return
		case <-ticker.C:
			s.writeMu.Lock()
			err := s.ws.WriteControl(websocket.PingMessage, []byte{}, time.Now().Add(10*time.Second))
			s.writeMu.Unlock()
			if err != nil {
				return
			}
		}
	}
}

func (s *wsSession) startIdleTimeoutWatcher() {
	defer s.bgWG.Done()

	select {
	case <-s.done:
		return
	case <-s.idleTimer.C:
		slog.Info("v2 sqlserver ws session idle timeout, closing")
		s.writeMu.Lock()
		_ = s.ws.WriteControl(
			websocket.CloseMessage,
			websocket.FormatCloseMessage(websocket.CloseNormalClosure, "idle timeout"),
			time.Now().Add(10*time.Second),
		)
		s.writeMu.Unlock()
		_ = s.ws.Close()
	}
}

func (s *wsSession) resetIdleTimer() {
	if !s.idleTimer.Stop() {
		select {
		case <-s.idleTimer.C:
		default:
		}
	}
	s.idleTimer.Reset(idleTimeout)
	_ = s.ws.SetReadDeadline(time.Now().Add(pongWait))
}

func (s *wsSession) handleConnect(body json.RawMessage) ([]byte, error) {
	impl.Clean(s.db, s.conn)
	s.db, s.conn = nil, nil

	var connectReq WSConnectRequest
	if err := json.Unmarshal(body, &connectReq); err != nil {
		return nil, err
	}

	if connectReq.Timeout <= 0 {
		connectReq.Timeout = defaultConnectTimeout
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(connectReq.Timeout)*time.Second)
	defer cancel()

	var err error
	s.db, s.conn, err = impl.Prepare(ctx, connectReq.Address, s.user, s.password, connectReq.Timeout)
	if err != nil {
		slog.Error("v2 sqlserver ws connect failed",
			slog.String("addr", connectReq.Address),
			slog.String("error", err.Error()),
		)
		return nil, err
	}

	slog.Info("v2 sqlserver ws connect established",
		slog.String("addr", connectReq.Address),
	)
	return []byte(fmt.Sprintf(`{"address":"%s"}`, connectReq.Address)), nil
}

func (s *wsSession) handleCommandWithSemaphore(body json.RawMessage) ([]byte, int64, error) {
	if s.conn == nil {
		return nil, 0, fmt.Errorf("connection not established, please send CONNECT first")
	}

	ctx, cancel := context.WithTimeout(context.Background(), commandAcquireTimeout)
	defer cancel()

	if err := config.GlobalSemaphore.Acquire(ctx, 1); err != nil {
		metric.Id(apm.AddressesTotal).Inc("throttled")
		slog.Warn("v2 sqlserver ws command throttled",
			slog.String("error", err.Error()),
		)
		return nil, 0, fmt.Errorf("server overloaded, please retry: %w", err)
	}
	defer config.GlobalSemaphore.Release(1)

	metric.Id(apm.InflightAddresses).Add(1)
	defer metric.Id(apm.InflightAddresses).Add(-1)

	result, n, err := handleCommand(s.conn, body, s.classifier)
	if err != nil {
		metric.Id(apm.AddressesTotal).Inc("error")
		slog.Error("v2 sqlserver ws command failed",
			slog.String("error", err.Error()),
		)
	} else {
		metric.Id(apm.AddressesTotal).Inc("success")
	}
	return result, n, err
}

func (s *wsSession) handleTextMessage(message []byte) {
	var req WSBaseRequest
	if err := json.Unmarshal(message, &req); err != nil {
		s.writeError(err.Error())
		return
	}

	var resultData []byte
	var rowsAffected int64
	var err error

	switch strings.ToUpper(req.RequestType) {
	case "CONNECT":
		resultData, err = s.handleConnect(req.Body)
		if err != nil {
			s.writeError(err.Error())
			return
		}
	case "COMMAND":
		resultData, rowsAffected, err = s.handleCommandWithSemaphore(req.Body)
		if err != nil {
			s.writeError(err.Error())
			return
		}
	default:
		s.writeError("invalid request type")
		return
	}

	s.writeResponse(resultData, rowsAffected)
}

func (s *wsSession) cleanup() {
	close(s.done)
	s.bgWG.Wait()
	_ = s.ws.Close()
	impl.Clean(s.db, s.conn)
}

// AdminHandler SQLServer admin 全权限 WS
var AdminHandler = makeHandler(
	func() (string, string) {
		return config.RuntimeConfig.SqlserverAdminUser, config.RuntimeConfig.SqlserverAdminPassword
	},
	impl.AdminCommands,
)

// DataReadHandler SQLServer 业务数据只读 WS
var DataReadHandler = makeHandler(
	func() (string, string) {
		return config.RuntimeConfig.SqlserverDataReadUser, config.RuntimeConfig.SqlserverDataReadPassword
	},
	impl.ReadOnlyCommands,
)

// SySReadHandler SQLServer 系统库只读 WS
var SySReadHandler = makeHandler(
	func() (string, string) {
		return config.RuntimeConfig.SqlserverSySReadUser, config.RuntimeConfig.SqlserverSySReadPassword
	},
	impl.ReadOnlyCommands,
)

func makeHandler(account func() (user, password string), classifier *impl.CommandClassifier) gin.HandlerFunc {
	return func(c *gin.Context) {
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

		ws.SetReadLimit(maxWSMessageSize)

		user, password := account()
		session := &wsSession{
			ws:         ws,
			done:       make(chan struct{}),
			idleTimer:  time.NewTimer(idleTimeout),
			user:       user,
			password:   password,
			classifier: classifier,
		}

		slog.Info("v2 sqlserver ws session started",
			slog.String("remote", c.ClientIP()),
		)
		defer func() {
			session.cleanup()
			slog.Info("v2 sqlserver ws session ended",
				slog.String("remote", c.ClientIP()),
			)
		}()
		defer session.idleTimer.Stop()

		ws.SetPongHandler(func(string) error {
			_ = ws.SetReadDeadline(time.Now().Add(pongWait))
			return nil
		})

		session.bgWG.Add(2)
		go session.startHeartbeat()
		go session.startIdleTimeoutWatcher()

		_ = ws.SetReadDeadline(time.Now().Add(pongWait))

		for {
			msgType, message, err := ws.ReadMessage()
			if err != nil {
				if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
					return
				}
				session.writeError(err.Error())
				return
			}

			session.resetIdleTimer()

			switch msgType {
			case websocket.TextMessage:
				session.handleTextMessage(message)
			case websocket.CloseMessage:
				return
			default:
				session.writeError("unsupported message type")
			}
		}
	}
}
