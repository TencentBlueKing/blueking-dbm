package websocket

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"log/slog"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/mysql/db-remote-service/pkg/apm"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/jmoiron/sqlx"
)

const (
	// pingInterval 心跳发送间隔
	pingInterval = 30 * time.Second
	// idleTimeout 空闲超时时间，超过此时间无消息活动将关闭连接
	idleTimeout = 10 * time.Minute
	// pongWait 等待 pong 响应的超时时间
	pongWait = 60 * time.Second
	// defaultConnectTimeout CONNECT 请求未指定 timeout 时的默认值（秒）
	defaultConnectTimeout = 2
	// defaultCommandTimeout COMMAND 请求未指定 timeout 时的默认值（秒）
	defaultCommandTimeout = 600
	// maxWSMessageSize 单条 WebSocket 文本消息的最大字节数; 防止恶意客户端 OOM
	maxWSMessageSize = 1 << 20 // 1 MB
	// commandAcquireTimeout 单条 COMMAND 等待全局信号量的最长时间;
	//   超过则返回 throttled 错误, 避免长连接 session 被永久阻塞
	commandAcquireTimeout = 30 * time.Second
)

// wsSession 封装 WebSocket 会话的所有状态
type wsSession struct {
	ws        *websocket.Conn
	writeMu   sync.Mutex
	done      chan struct{}
	bgWG      sync.WaitGroup
	idleTimer *time.Timer
	db        *sqlx.DB
	conn      *sqlx.Conn
	connID    int64
	user      string
	password  string
}

// writeError 向 WebSocket 客户端发送错误响应
func (s *wsSession) writeError(errMsg string) {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	_ = s.ws.WriteMessage(websocket.TextMessage, WSResponse{
		Result:       nil,
		RowsAffected: 0,
		Error:        errMsg,
	}.Bytes())
}

// writeResponse 向 WebSocket 客户端发送成功响应
func (s *wsSession) writeResponse(result []byte, rowsAffected int64) {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	_ = s.ws.WriteMessage(websocket.TextMessage, WSResponse{
		Result:       result,
		RowsAffected: rowsAffected,
		Error:        "",
	}.Bytes())
}

// startHeartbeat 启动心跳 goroutine，定期发送 ping 消息保持连接活跃
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

// startIdleTimeoutWatcher 启动空闲超时检测 goroutine，超时后关闭连接
func (s *wsSession) startIdleTimeoutWatcher() {
	defer s.bgWG.Done()

	select {
	case <-s.done:
		return
	case <-s.idleTimer.C:
		slog.Info("v2 ws session idle timeout, closing")
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

// resetIdleTimer 重置空闲计时器和读取超时
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

// handleConnect 处理连接请求，建立数据库连接
func (s *wsSession) handleConnect(body json.RawMessage) ([]byte, error) {
	// 清理旧会话: 必须 KILL 旧 connection, 否则 server 端可能残留 zombie session
	impl.Clean(s.db, s.conn, s.connID)
	s.db, s.conn, s.connID = nil, nil, 0

	var connectReq WSConnectRequest
	if err := json.Unmarshal(body, &connectReq); err != nil {
		return nil, err
	}

	if connectReq.Timeout <= 0 {
		connectReq.Timeout = defaultConnectTimeout
	}

	// 给建连套一个 timeout, 防止 driver 卡死. WS 没有"客户端取消"信号源,
	// 用 connectReq.Timeout 兜底已经足够 (DSN 里 timeout 也是同一个值).
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(connectReq.Timeout)*time.Second)
	defer cancel()

	var err error
	s.db, s.conn, s.connID, err = impl.Prepare(
		ctx,
		connectReq.Address, s.user, s.password,
		connectReq.Timezone, connectReq.Charset, connectReq.Timeout, connectReq.PreHookCmds, connectReq.SkipSetNames,
	)
	if err != nil {
		slog.Error("v2 ws connect failed",
			slog.String("addr", connectReq.Address),
			slog.String("error", err.Error()),
		)
		return nil, err
	}

	slog.Info("v2 ws connect established",
		slog.String("addr", connectReq.Address),
		slog.Int64("conn_id", s.connID),
	)
	return []byte(fmt.Sprintf(`{"connection_id":%d,"address":"%s"}`, s.connID, connectReq.Address)), nil
}

// handleCommandWithSemaphore COMMAND 路径包了一层全局信号量, 防止 ws session 绕过反压
func (s *wsSession) handleCommandWithSemaphore(body json.RawMessage) ([]byte, int64, error) {
	if s.conn == nil {
		return nil, 0, fmt.Errorf("connection not established, please send CONNECT first")
	}

	ctx, cancel := context.WithTimeout(context.Background(), commandAcquireTimeout)
	defer cancel()

	if err := config.GlobalSemaphore.Acquire(ctx, 1); err != nil {
		metric.Id(apm.AddressesTotal).Inc("throttled")
		slog.Warn("v2 ws command throttled",
			slog.String("error", err.Error()),
		)
		return nil, 0, fmt.Errorf("server overloaded, please retry: %w", err)
	}
	defer config.GlobalSemaphore.Release(1)

	metric.Id(apm.InflightAddresses).Add(1)
	defer metric.Id(apm.InflightAddresses).Add(-1)

	result, n, err := handleCommand(s.conn, body)
	if err != nil {
		metric.Id(apm.AddressesTotal).Inc("error")
		slog.Error("v2 ws command failed",
			slog.String("error", err.Error()),
		)
	} else {
		metric.Id(apm.AddressesTotal).Inc("success")
	}
	return result, n, err
}

// handleTextMessage 处理文本消息，根据请求类型分发处理
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
		// CONNECT 不占用全局执行信号量, 它只是建连; 真正消耗资源的是 COMMAND
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

// cleanup 清理会话资源
//
// 顺序很关键:
//  1. close(done): 通知后台 goroutine 退出
//  2. bgWG.Wait(): 等心跳 / idleWatcher 真正退出, 避免它们和后续 ws.Close 竞争 writeMu
//  3. ws.Close(): 关 socket
//  4. impl.Clean: KILL 远端 conn 并归还连接池
func (s *wsSession) cleanup() {
	close(s.done)
	s.bgWG.Wait()
	_ = s.ws.Close()
	impl.Clean(s.db, s.conn, s.connID)
}

// AdminHandler 用 mysql admin 账号
var AdminHandler = makeHandler(func() (string, string) {
	return config.RuntimeConfig.MySQLAdminUser, config.RuntimeConfig.MySQLAdminPassword
})

// WebConsoleHandler 用 webconsole 只读账号
var WebConsoleHandler = makeHandler(func() (string, string) {
	return config.RuntimeConfig.WebConsoleUser, config.RuntimeConfig.WebConsolePassword
})

func makeHandler(account func() (user, password string)) gin.HandlerFunc {
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
			ws:        ws,
			done:      make(chan struct{}),
			idleTimer: time.NewTimer(idleTimeout),
			user:      user,
			password:  password,
		}

		slog.Info("v2 ws session started",
			slog.String("remote", c.ClientIP()),
		)
		defer func() {
			session.cleanup()
			slog.Info("v2 ws session ended",
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
