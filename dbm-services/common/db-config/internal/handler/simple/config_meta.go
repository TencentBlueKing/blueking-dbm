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

// ValidateConfigNameExists godoc
//
// @Summary      判断配置名是否已存在
// @Description  从 tb_config_name_def / tb_config_name_plat 两个表判断 conf_name 是否已存在
// @Tags         config_meta
// @Produce      json
// @Param        body query     api.QueryConfigNamesReq  true  "query"
// @Success      200  {object}  map[string]bool
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confname/exists [get]
func (cf *Config) ValidateConfigNameExists(ctx *gin.Context) {
	var r api.QueryConfigNamesReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if _, err := simpleconfig.CheckValidConfFile(r.Namespace, r.ConfType, r.ConfFile, ""); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}

	exists, err := simpleconfig.ValidateConfigNameExists(&r)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, nil, map[string]bool{"exists": exists})
}
