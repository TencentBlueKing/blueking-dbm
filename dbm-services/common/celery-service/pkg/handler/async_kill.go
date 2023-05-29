package handler

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"

	"celery-service/pkg/asyncsession"
)

func HandleAsyncKill(engine *gin.Engine) {
	g := engine.Group("async")
	g.POST("kill",
		func(ctx *gin.Context) {
			var postArg struct {
				SessionID *string `json:"session_id"`
			}

			if err := ctx.ShouldBindJSON(&postArg); err != nil {
				ctx.JSON(
					http.StatusBadRequest,
					gin.H{
						"code": 1,
						"data": "",
						"msg":  err.Error(),
					})
				return
			}

			if postArg.SessionID == nil {
				ctx.JSON(
					http.StatusBadRequest,
					gin.H{
						"code": 1,
						"data": "",
						"msg":  "session_id required",
					})
				return
			}

			v, ok := asyncsession.SessionMap.Load(*postArg.SessionID)
			if !ok {
				ctx.JSON(
					http.StatusOK,
					gin.H{
						"code": 0,
						"data": "",
						"msg":  fmt.Sprintf("session %s not found", *postArg.SessionID),
					})
				return
			}

			session := v.(*asyncsession.Session)
			session.Cancel()

			asyncsession.SessionMap.Delete(postArg.SessionID)

			ctx.JSON(
				http.StatusOK,
				gin.H{
					"code": 0,
					"data": "",
					"msg":  "",
				})
		})
}
