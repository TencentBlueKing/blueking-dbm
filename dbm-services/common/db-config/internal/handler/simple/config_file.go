package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/constvar"

	"dbm-services/common/go-pubpkg/validate"

	"github.com/gin-gonic/gin"
)

// ListConfigFiles godoc
//
// @Summary      查询配置文件列表
// @Description  查询配置文件模板列表。只有平台和业务才有配置文件列表
// @Description  返回的 updated_by 代表操作人
// @Tags         plat_config
// @Produce      json
// @Param        body query     api.ListConfFileReq  true  "query"
// @Success      200  {object}  []api.ListConfFileResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/conffile/list [get]
func (cf *Config) ListConfigFiles(ctx *gin.Context) {
	var r api.ListConfFileReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if r.LevelValue == "" && r.LevelName == constvar.LevelApp {
		r.LevelValue = r.BKBizID
	}
	resp, err := simpleconfig.ListConfigFiles(&r)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}

// ListConfigLevel godoc
//
// @Summary      查询业务有哪些配置层级
// @Description  查询业务有哪些配置层级
// @Description  返回的 updated_by 代表操作人
// @Tags         plat_config
// @Produce      json
// @Param        body query     api.ListConfLevelReq  true  "query"
// @Success      200  {object}  []api.ListConfLevelResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/conffile/list_level_value [get]
func (cf *Config) ListConfigLevel(ctx *gin.Context) {
	var r api.ListConfLevelReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err := simpleconfig.ListConfigLevels(&r)

	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}

// DeleteConfigLevel godoc
//
// @Summary      删除配置层级
// @Description  删除配置层级
// @Description  返回的 updated_by 代表操作人
// @Tags         plat_config
// @Produce      json
// @Param        body body     api.DeleteConfLevelReq  true  "body"
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/conffile/delete_level_value [post]
func (cf *Config) DeleteConfigLevel(ctx *gin.Context) {
	var r api.DeleteConfLevelReq
	if err := ctx.ShouldBindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err := simpleconfig.DeleteConfigLevel(&r)

	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}
