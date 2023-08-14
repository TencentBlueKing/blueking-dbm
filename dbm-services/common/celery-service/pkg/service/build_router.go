package service

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/iancoleman/strcase"

	"celery-service/pkg/asyncsession"
	"celery-service/pkg/handler"
)

func buildRouter(engine *gin.Engine) error {
	err := handler.InitHandlers()
	if err != nil {
		return err
	}

	buildSyncRouter(engine)
	buildAsyncRouter(engine)

	return nil
}

type workerResPack struct {
	Msg string
	Err error
}

func buildSyncRouter(engine *gin.Engine) {
	syncGroup := engine.Group("sync")
	for dbType, hs := range handler.Handlers {
		g := syncGroup.Group(strcase.ToKebab(dbType))
		for _, h := range hs {
			g.POST(
				strcase.ToKebab(h.Name()),
				func(h handler.IHandler) func(ctx *gin.Context) {
					return func(ctx *gin.Context) {
						body, err := io.ReadAll(ctx.Request.Body)
						if err != nil {
							ctx.JSON(
								http.StatusInternalServerError,
								gin.H{
									"code": 1,
									"data": "",
									"msg":  err.Error(),
								})
							return
						}

						resPackChan := make(chan *workerResPack)
						hCtx, cancel := context.WithCancel(context.Background())
						defer cancel()

						go func() {
							msg, err := h.Worker(body, hCtx)
							resPackChan <- &workerResPack{
								Msg: msg,
								Err: err,
							}
						}()

						for {
							select {
							case resPack := <-resPackChan:
								if resPack.Err != nil {
									ctx.JSON(
										http.StatusOK,
										gin.H{
											"code": 1,
											"data": "",
											"msg":  resPack.Err.Error(),
										})
								} else {
									ctx.JSON(
										http.StatusOK,
										gin.H{
											"code": 0,
											"data": resPack.Msg,
											"msg":  "",
										})
								}
								return
							case <-ctx.Request.Context().Done():
								ctx.JSON(
									http.StatusTooEarly,
									gin.H{
										"code": 0,
										"data": "",
										"msg":  "canceled",
									})
								return
							}
						}
					}
				}(h),
			)
		}
	}
}

func buildAsyncRouter(engine *gin.Engine) {
	asyncGroup := engine.Group("async")

	for dbType, hs := range handler.Handlers {
		g := asyncGroup.Group(strcase.ToKebab(dbType))
		for _, h := range hs {
			g.POST(
				strcase.ToKebab(h.Name()),
				func(h handler.IHandler) func(ctx *gin.Context) {
					return func(ctx *gin.Context) {
						body, err := io.ReadAll(ctx.Request.Body)
						if err != nil {
							ctx.JSON(
								http.StatusInternalServerError,
								gin.H{
									"code": 1,
									"data": "",
									"msg":  err.Error(),
								})
							return
						}

						sessionID := uuid.New().String()
						hCtx, cancel := context.WithCancel(context.Background())

						go func(body []byte) {
							asyncsession.SessionMap.Store(
								sessionID,
								&asyncsession.Session{
									ID:      sessionID,
									Message: "",
									Err:     "",
									Done:    false,
									Cancel:  cancel,
									StartAt: time.Now(),
								},
							)

							msg, err := h.Worker(body, hCtx)

							select {
							case <-hCtx.Done():
								logger.Info("canceled")
							default:
								v, ok := asyncsession.SessionMap.Load(sessionID)
								if !ok {
									ctx.JSON(
										http.StatusInternalServerError,
										gin.H{
											"code": 1,
											"data": "",
											"msg":  fmt.Sprintf("%s not found", sessionID),
										})
								}
								st := v.(*asyncsession.Session)
								st.Message = msg
								st.Done = true
								if err != nil {
									st.Err = err.Error()
								}
							}
						}(body)

						ctx.JSON(
							http.StatusOK,
							gin.H{
								"code": 0,
								"data": sessionID,
								"msg":  "",
							})
						return
					}
				}(h),
			)
		}
	}
}
