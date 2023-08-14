package handler

import (
	"fmt"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
	"golang.org/x/exp/slog"

	"celery-service/pkg/asyncsession"
)

func HandleAsyncQuery(engine *gin.Engine) {
	g := engine.Group("async")
	g.POST("query",
		func(ctx *gin.Context) {
			var postArg struct {
				SessionID *string `json:"session_id"`
			}

			if err := ctx.ShouldBindJSON(&postArg); err != nil && err != io.EOF {
				logger.Error("bind post args", slog.Any("error", err))
				ctx.JSON(
					http.StatusBadRequest,
					gin.H{
						"code": 1,
						"data": "",
						"msg":  err.Error(),
					})
				return
			}

			if postArg.SessionID != nil {
				logger.Info("query", slog.String("post session id", *postArg.SessionID))

				v, ok := asyncsession.SessionMap.Load(*postArg.SessionID)
				if !ok {
					ctx.JSON(
						http.StatusOK,
						gin.H{
							"code": 1,
							"data": "",
							"msg":  fmt.Sprintf("session %s not found", *postArg.SessionID),
						})
					return
				}

				session := v.(*asyncsession.Session)

				ctx.JSON(
					http.StatusOK,
					gin.H{
						"code": 0,
						"data": []*asyncsession.Session{session},
						"msg":  "",
					})
				return
			} else {
				logger.Info("query all sessions")

				var sessions []*asyncsession.Session
				asyncsession.SessionMap.Range(func(_, v any) bool {
					sessions = append(sessions, v.(*asyncsession.Session))
					return true
				})

				ctx.JSON(
					http.StatusOK,
					gin.H{
						"code": 0,
						"data": sessions,
						"msg":  "",
					})
				return
			}

		})
}
