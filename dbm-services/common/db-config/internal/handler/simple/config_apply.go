package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

	"github.com/gin-gonic/gin"
)

// VersionApplyInfo godoc
//
// @Summary      获取该目标 已发布且待应用 的配置内容
// @Description  要应用的版本，必须已发布状态
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.ApplyConfigInfoReq  true  "ApplyConfigInfoReq"
// @Success      200  {object}  api.ApplyConfigInfoResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/applyinfo [post]
func (cf *Config) VersionApplyInfo(ctx *gin.Context) {
	var r api.ApplyConfigInfoReq
	var resp *api.ApplyConfigInfoResp
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

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
	// opUser := ctx.GetHeader(constvar.UserNameHeader)
	if resp, err = simpleconfig.GetConfigsToApply(model.DB.Self, r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
	}
}

// VersionApplyStat godoc
//
// @Summary      配置已应用，更新 version 状态
// @Description  该版本配置已全部应用
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.ApplyConfigReq  true  "ApplyConfigInfoReq"
// @Success      200  {object}  api.HTTPOkNilResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/applied [post]
func (cf *Config) VersionApplyStat(ctx *gin.Context) {
	var r api.ApplyConfigReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

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
	// opUser := ctx.GetHeader(constvar.UserNameHeader)
	verObj := model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		Revision:   r.RevisionApplied,
	}
	if err = verObj.VersionApplyStatus(model.DB.Self); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, nil)
	}
}

// VersionStat godoc
//
// @Summary      批量查看已发布版本的状态
// @Description  主要查看已发布版本是否已应用
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.VersionStatReq  true  "VersionStatReq"
// @Success      200  {object}  api.VersionStatResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/status [post]
func (cf *Config) VersionStat(ctx *gin.Context) {
	var r api.VersionStatReq
	var resp *api.VersionStatResp
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

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
	// opUser := ctx.GetHeader(constvar.UserNameHeader)
	if resp, err = simpleconfig.GetVersionStat(r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
	}
}

// VersionApply godoc
//
// @Summary      应用 level_config 配置
// @Description  给所有下级发布配置（但不应用）
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.VersionApplyReq  true  "ApplyConfigInfoReq"
// @Success      200  {object}  api.HTTPOkNilResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/applylevel [post]
func (cf *Config) VersionApply(ctx *gin.Context) {
	var r api.VersionApplyReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

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
	// opUser := ctx.GetHeader(constvar.UserNameHeader)
	publish := simpleconfig.PublishConfig{}
	if err = publish.ApplyVersionLevelNode(model.DB.Self, &r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, nil)
	}
}

// ItemApply godoc
//
// @Summary      修改待应用配置为已应用状态
// @Description  只针对 versioned_config
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.ConfItemApplyReq  true  "ApplyConfigInfoReq"
// @Success      200  {object}  api.HTTPOkNilResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/applyitem [post]
func (cf *Config) ItemApply(ctx *gin.Context) {
	var r api.ConfItemApplyReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

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
	// opUser := ctx.GetHeader(constvar.UserNameHeader)
	if err = simpleconfig.NodeTaskApplyItem(&r); err != nil {
		// if err := verObj.ApplyConfig(model.DB.Self); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, nil)
	}
}
