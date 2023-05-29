package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"

	"github.com/gin-gonic/gin"
)

// QueryConfigTypeNames godoc
//
// @Summary      查询预定义的配置名列表
// @Description  查询某个配置类型/配置文件的配置名列表，会排除 已锁定的平台配置
// @Tags         config_meta
// @Produce      json
// @Param        body query     api.QueryConfigNamesReq  true  "query"
// @Success      200  {object}  api.QueryConfigNamesResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confname/list [get]
func (cf *Config) QueryConfigTypeNames(ctx *gin.Context) {
	var r api.QueryConfigNamesReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err := simpleconfig.QueryConfigNames(&r, false)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}

// QueryConfigTypeInfo TODO
func (cf *Config) QueryConfigTypeInfo(ctx *gin.Context) {
	var r api.QueryConfigTypeReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err := simpleconfig.QueryConfigTypeInfo(&r)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}
