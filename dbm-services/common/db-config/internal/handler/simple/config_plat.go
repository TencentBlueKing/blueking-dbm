package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

	"github.com/gin-gonic/gin"
)

// UpsertConfigFilePlat godoc
//
// @Summary      新增平台级配置文件
// @Description  新增平台级配置文件，定义允许的配置名。指定 req_type 为 `SaveOnly` 仅保存, `SaveAndPublish` 保存并发布。保存并发布 也必须提供全量，而不能是前面保存基础上的增量
// @Description  req_type=`SaveOnly` 已废弃
// @Description  第一次保存时，会返回 `file_id`，下次 保存/发布 需传入 `file_id`
// @Description  namespace,conf_type,conf_file 唯一确定一个配置文件，不同DB版本信息体现在 conf_file 里 (如MySQL-5.7), namespace_info 可以存前端传入的 数据库版本，只用于在展示
// @Description  HTTP Header 指定 `X-Bkapi-User-Name` 请求的操作人员
// @Tags         plat_config
// @Accept       json
// @Produce      json
// @Param        body body      api.UpsertConfFilePlatReq  true  "ConfName for ConfType"
// @Success      200  {object}  api.UpsertConfFilePlatResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/conffile/add [post]
func (cf *Config) UpsertConfigFilePlat(ctx *gin.Context) {
	var r api.UpsertConfFilePlatReq
	if err := ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := r.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := simpleconfig.CheckValidConfType(r.ConfFileInfo.Namespace, r.ConfFileInfo.ConfType,
		r.ConfFileInfo.ConfFile, "", 2); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	if resp, err := simpleconfig.UpsertConfigFilePlat(&r, "new", opUser); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
	}

}

// UpdateConfigFilePlat godoc
//
// @Summary      编辑平台级配置文件
// @Description  编辑平台级配置文件。指定 req_type 为 `SaveOnly` 仅保存, `SaveAndPublish` 保存并发布
// @Description  HTTP Header 指定 `X-Bkapi-User-Name` 请求的操作人员
// @Description  编辑平台配置时，如果设置 flag_disable=1 时，该配置不会显示在平台配置项列表，相当于管理 所有允许的配置项列表
// @Description 保存时会校验输入的 value_default, value_type, value_allowed
// @Description   1. value_type 目前允许 STRING, INT, FLOAT, NUMBER
// @Description   2. value_type_sub 允许 ENUM, ENUMS, RANGE, STRING, JSON, REGEX(一种特殊的STRING，会验证 value_default 是否满足 value_allowed 正则), BYTES(64m, 128k格式，会转换成bytes与 value_allowed的范围进行比较)
// @Description   3. value_allowed 允许 枚举: 例如`0|1|2`, `ON|OFF` 格式， 范围: 例如`(0, 1000]`
// @Tags         plat_config
// @Accept       json
// @Produce      json
// @Param        body body      api.UpsertConfFilePlatReq  true  "ConfName for ConfType"
// @Success      200  {object}  api.UpsertConfFilePlatResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/conffile/update [post]
func (cf *Config) UpdateConfigFilePlat(ctx *gin.Context) {
	var r api.UpsertConfFilePlatReq
	var resp *api.UpsertConfFilePlatResp
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
	if err = simpleconfig.CheckValidConfType(r.ConfFileInfo.Namespace, r.ConfFileInfo.ConfType,
		r.ConfFileInfo.ConfFile, "", 2); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	if resp, err = simpleconfig.UpsertConfigFilePlat(&r, "edit", opUser); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
	}
}

// QueryConfigTypeNamesPlat godoc
//
// @Summary      查询平台配置项列表
// @Description  查询 平台配置 某个配置类型/配置文件的所有配置名列表
// @Tags         plat_config
// @Produce      json
// @Param        body query     api.QueryConfigNamesReq  true  "query"
// @Success      200  {object}  api.QueryConfigNamesResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/conffile/query [get]
func (cf *Config) QueryConfigTypeNamesPlat(ctx *gin.Context) {
	var r api.QueryConfigNamesReq
	var resp *api.QueryConfigNamesResp
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

	if err = ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err = simpleconfig.QueryConfigNames(&r, true)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}
