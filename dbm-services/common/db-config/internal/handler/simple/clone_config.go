package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/service/simpleconfig"

	"github.com/gin-gonic/gin"

	"dbm-services/common/go-pubpkg/validate"
)

// CloneModuleConfig godoc
//
// @Summary      克隆模块配置
// @Description  克隆模块配置项
// @Tags         config_item
// @Accept       json
// @Produce      json
// @Param        body body     api.CloneModuleConfigReq true  "change bk_biz_id for clusters"
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/clonemodule [post]
func (cf *Config) CloneModuleConfig(ctx *gin.Context) {
	var r api.CloneModuleConfigReq
	var resp *api.ChangeBkBizIdResp
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, false); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	txErr := simpleconfig.CloneModuleConfig(&r, "", model.DB.Self)
	if txErr != nil {
		handler.SendResponse(ctx, txErr, nil)
		return
	}
	handler.SendResponse(ctx, nil, resp)
	return
}

// CloneClusterConfig godoc
//
// @Summary      修改集群的业务和模块
// @Description  修改集群的业务和模块，克隆配置
// @Tags         config_item
// @Accept       json
// @Produce      json
// @Param        body body     api.CloneClusterConfigReq  true  "change bk_biz_id for clusters"
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/clonecluster [post]
func (cf *Config) CloneClusterConfig(ctx *gin.Context) {
	var r api.CloneClusterConfigReq
	var resp *api.ChangeBkBizIdResp
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, false); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	txErr := simpleconfig.CloneClusterConfig(&r, "", model.DB.Self)
	if txErr != nil {
		handler.SendResponse(ctx, txErr, nil)
		return
	}
	handler.SendResponse(ctx, nil, resp)
	return
}
