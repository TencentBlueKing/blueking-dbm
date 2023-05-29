package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/dbha"
	"bk-dbconfig/internal/service/simpleconfig"

	"github.com/gin-gonic/gin"
)

// BatchGetConfigOneItem godoc
//
// @Summary      批量获取多个对象的某一配置项
// @Description  批量获取多个对象的某一配置项，不会继承
// @Tags         config_item
// @Accept      json
// @Produce      json
// @Param        body body     api.BatchGetConfigItemReq  true  "BatchGetConfigItemReq"
// @Success      200  {object}  api.BatchGetConfigItemResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/batchget [post]
func (cf *Config) BatchGetConfigOneItem(ctx *gin.Context) {
	var r api.BatchGetConfigItemReq
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err = r.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err = simpleconfig.CheckValidConfType(r.Namespace, r.ConfType, r.ConfFile, r.LevelName, 2); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if resp, err := dbha.BatchGetConfigItem(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
		return
	}
}

// BatchGetConfigItemMore godoc
//
// @Summary      批量获取多个对象的多个配置项
// @Description  批量获取多个对象的多个配置项，不会继承
// @Tags         config_item
// @Accept      json
// @Produce      json
// @Param        body body     api.BatchGetConfigItemReq  true  "BatchGetConfigItemReq"
// @Success      200  {object}  api.BatchGetConfigItemResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/batchgetmore [post]
func (cf *Config) BatchGetConfigItemMore(ctx *gin.Context) {
	var r api.BatchGetConfigItemReq
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err = r.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err = simpleconfig.CheckValidConfType(r.Namespace, r.ConfType, r.ConfFile, r.LevelName, 2); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if resp, err := dbha.BatchGetConfigItem(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
		return
	}
}
