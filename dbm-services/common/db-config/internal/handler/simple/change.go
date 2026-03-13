package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/validatestruct"

	"github.com/gin-gonic/gin"
)

// ChangeConfNameDef godoc
//
// @Summary      编辑平台级配置文件
// @Description  HTTP Header 指定 `X-Bkapi-User-Name` 请求的操作人员
// @Description  编辑平台配置时，如果设置 flag_disable=1 时，该配置不会显示在平台配置项列表，相当于管理 所有允许的配置项列表
// @Description 保存时会校验输入的 value_default, value_type, value_allowed
// @Description   1. value_type 目前允许 STRING, INT, FLOAT, NUMBER
// @Description   2. value_type_sub 允许 ENUM, ENUMS, RANGE, STRING, JSON, REGEX(一种特殊的STRING，会验证 value_default 是否满足 value_allowed 正则), BYTES(64m, 128k格式，会转换成bytes与 value_allowed的范围进行比较)
// @Description   3. value_allowed 允许 枚举: 例如`0|1|2`, `ON|OFF` 格式， 范围: 例如`(0, 1000]`
// @Tags         config_meta
// @Accept       json
// @Produce      json
// @Param        body body      api.ChangeConfNameDefReq true  "ConfName for ConfType"
// @Success      200  {object}  api.UpsertConfFilePlatResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confname/change [post]
func (cf *Config) ChangeConfNameDef(ctx *gin.Context) {
	var r api.ChangeConfNameDefReq
	//var resp *api.UpsertConfFilePlatResp
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

	if err = simpleconfig.ValidateValueForClient(r.ConfNames, false); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}

	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))

	confFile := api.BaseConfFileDef{
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
	}
	if err := simpleconfig.ConfigNamesBatchUpsert(model.DB.Self, confFile, r.ConfNames, opUser); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, "ok")
		return
	}
}

// QueryConfNameChanges godoc
//
// @Summary      查询配置项定义的变更历史
// @Description  查询 conf_name_def 的操作历史记录，namespace 必填，conf_type/conf_file/conf_name 可选
// @Tags         config_meta
// @Accept       json
// @Produce      json
// @Param        namespace  query  string  true   "命名空间"
// @Param        conf_type  query  string  false  "配置类型"
// @Param        conf_file  query  string  false  "配置文件"
// @Param        conf_name  query  string  false  "配置项名称"
// @Success      200  {object}  []model.ConfNameChangesModel
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confname/changes [get]
func (cf *Config) QueryConfNameChanges(ctx *gin.Context) {
	var req model.ConfNameChangesQueryReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

	if err = ctx.ShouldBindQuery(&req); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	changes, err := model.QueryConfNameChanges(model.DB.Self, &req)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, nil, changes)
}

// QueryConfItemChanges godoc
//
// @Summary      查询配置的变更历史
// @Description  查询集群/业务配置项的操作历史记录，bk_biz_id 和 namespace 必填，conf_type/conf_file/conf_name/level_name/level_value 可选
// @Tags         config_item
// @Accept       json
// @Produce      json
// @Param        bk_biz_id   query  string  true   "业务ID"
// @Param        namespace   query  string  true   "命名空间"
// @Param        conf_type   query  string  false  "配置类型"
// @Param        conf_file   query  string  false  "配置文件"
// @Param        conf_name   query  string  false  "配置项名称"
// @Param        level_name  query  string  false  "层级名称，如 app、cluster"
// @Param        level_value query  string  false  "层级值，如 app123、aa.bb.cc.db"
// @Success      200  {object}  []model.ConfItemChangesModel
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/changes [get]
func (cf *Config) QueryConfItemChanges(ctx *gin.Context) {
	var req model.ConfItemChangesQueryReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

	if err = ctx.ShouldBindQuery(&req); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	changes, err := model.QueryConfItemChanges(model.DB.Self, &req)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, nil, changes)
}

// ListDataTypes godoc
//
// @Summary      返回所有 value_type
// @Description  查询 dbconfig 支持的 value_type
// @Tags         config_meta
// @Produce      json
// @Param        body query     string  true  "query"
// @Success      200  {object}  []api.ListConfFileResp
// @Router       /bkconfig/v1/confname/types [get]
func (cf *Config) ListDataTypes(ctx *gin.Context) {
	resp := validatestruct.ValueTypeSubRef
	handler.SendResponse(ctx, nil, resp)
}
