package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// RequestMiddleware TODO
func RequestMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		reqId := ctx.Request.Header.Get("X-Request-Id")
		if reqId == "" {
			uid, err := uuid.NewUUID()
			if err != nil {
				ctx.Abort()
			}
			ctx.Request.Header.Set("X-Request-Id", uid.String())
		}
		ctx.Header("X-Request-Id", reqId)
		ctx.Next()
	}
}
