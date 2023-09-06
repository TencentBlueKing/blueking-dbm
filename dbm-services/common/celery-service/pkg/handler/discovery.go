package handler

import (
	"encoding/json"
	"net/http"
	"net/url"

	"github.com/gin-gonic/gin"
	"github.com/iancoleman/strcase"
)

type descriptor struct {
	Name        string          `json:"name"`
	ClusterType string          `json:"cluster_type"`
	EmptyParam  json.RawMessage `json:"empty_param"`
	Enable      bool            `json:"enable"`
	Url         string          `json:"url"`
}

func HandleDiscovery(engine *gin.Engine) {
	engine.GET("discovery",
		func(ctx *gin.Context) {
			var dess []descriptor

			for _, hs := range Handlers {
				for _, h := range hs {
					handlerUrl, err := url.JoinPath(
						strcase.ToKebab(h.ClusterType()),
						strcase.ToKebab(h.Name()))

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

					dess = append(dess, descriptor{
						Name:        h.Name(),
						ClusterType: h.ClusterType(),
						EmptyParam:  h.EmptyParam(),
						Enable:      h.Enable(),
						Url:         handlerUrl,
					})
				}
			}

			ctx.JSON(
				http.StatusOK,
				gin.H{
					"code": 0,
					"data": dess,
					"msg":  "",
				})
			return
		})
}
