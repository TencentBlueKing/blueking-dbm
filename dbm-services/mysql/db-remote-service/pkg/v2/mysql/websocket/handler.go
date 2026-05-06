package websocket

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

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
)

// wsSession 封装 WebSocket 会话的所有状态
type wsSession struct {
	ws        *websocket.Conn
	writeMu   sync.Mutex
	done      chan struct{}
	idleTimer *time.Timer
	db        *sqlx.DB
	conn      *sqlx.Conn
	connID    int64
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
	select {
	case <-s.done:
		return
	case <-s.idleTimer.C:
		// 空闲超时，发送关闭消息并关闭连接
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
	// 关闭旧连接，防止资源泄漏
	if s.conn != nil {
		_ = s.conn.Close()
	}
	if s.db != nil {
		_ = s.db.Close()
	}

	var connectReq WSConnectRequest
	if err := json.Unmarshal(body, &connectReq); err != nil {
		return nil, err
	}

	var err error
	s.db, s.conn, s.connID, err = impl.Prepare(
		connectReq.Address, config.RuntimeConfig.WebConsoleUser, config.RuntimeConfig.WebConsolePassword,
		connectReq.Timezone, connectReq.Charset, connectReq.Timeout,
	)
	if err != nil {
		return nil, err
	}

	// 连接成功，返回连接信息
	return []byte(fmt.Sprintf(`{"connection_id":%d,"address":"%s"}`, s.connID, connectReq.Address)), nil
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
		resultData, err = s.handleConnect(req.Body)
		if err != nil {
			s.writeError(err.Error())
			return
		}
	case "COMMAND":
		if s.conn == nil {
			s.writeError("connection not established, please send CONNECT first")
			return
		}
		resultData, rowsAffected, err = handleCommand(s.conn, req.Body)
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
func (s *wsSession) cleanup() {
	close(s.done)
	_ = s.ws.Close()
	impl.Clean(s.db, s.conn, s.connID)
}

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

	session := &wsSession{
		ws:        ws,
		done:      make(chan struct{}),
		idleTimer: time.NewTimer(idleTimeout),
	}
	defer session.cleanup()
	defer session.idleTimer.Stop()

	// 设置 pong 处理器，收到 pong 时更新读取超时
	ws.SetPongHandler(func(string) error {
		_ = ws.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	// 启动后台 goroutine
	go session.startHeartbeat()
	go session.startIdleTimeoutWatcher()

	// 设置初始读取超时
	_ = ws.SetReadDeadline(time.Now().Add(pongWait))

	for {
		msgType, message, err := ws.ReadMessage()
		if err != nil {
			// 如果是正常关闭或超时，不需要发送错误
			if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				return
			}
			session.writeError(err.Error())
			return
		}

		// 收到消息，重置空闲计时器
		session.resetIdleTimer()

		switch msgType {
		case websocket.TextMessage:
			session.handleTextMessage(message)
		case websocket.CloseMessage:
			// 客户端主动关闭，直接返回
			// 清理工作由 defer session.cleanup() 处理
			return
		default:
			session.writeError("unsupported message type")
		}
	}
}
