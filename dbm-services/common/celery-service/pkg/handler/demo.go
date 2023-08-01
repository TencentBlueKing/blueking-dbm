package handler

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
)

type DemoPostArgs struct {
	World string `json:"world"`
}

type DemoHandler struct {
	InternalBase // 必须匿名包含
}

// ClusterType 实现 IHandler
func (h *DemoHandler) ClusterType() string {
	return "DemoClusterType"
}

func (h *DemoHandler) Name() string {
	return "DemoHandler"
}

func (h *DemoHandler) Handler() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		var postArgs DemoPostArgs
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

		if len(body) > 0 {
			if err := json.Unmarshal(body, &postArgs); err != nil {
				ctx.JSON(
					http.StatusBadRequest,
					gin.H{
						"code": 1,
						"data": "",
						"msg":  err.Error(),
					})
				return
			}
		}

		ctx.JSON(
			http.StatusOK,
			gin.H{
				"code": 0,
				"data": fmt.Sprintf("hello: %v", postArgs),
				"msg":  "",
			})
	}
}

// 注册
func init() {
	addInternalHandler(&DemoHandler{})
}
