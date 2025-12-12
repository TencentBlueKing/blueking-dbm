package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/service/simpleconfig"
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
	if err = simpleconfig.CheckValidConfType(r.Namespace, r.ConfType,
		r.ConfFile, "", 2); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err = simpleconfig.ValidateValueForClient(r.ConfNames); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}

	//opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))

	confFile := api.BaseConfFileDef{
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
	}
	if err := simpleconfig.ConfigNamesBatchUpsert(model.DB.Self, confFile, r.ConfNames); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
		return
	}
}

// ListDataTypes godoc
//
// @Summary      返回所有 value_type
// @Description  查询 dbconfig 支持的 value_type
// @Tags         config_meta
// @Produce      json
// @Param        body query     map[string][]string  true  "query"
// @Success      200  {object}  []api.ListConfFileResp
// @Router       /bkconfig/v1/confname/types [get]
func (cf *Config) ListDataTypes(ctx *gin.Context) {
	resp := validatestruct.ValueTypeSubRef
	handler.SendResponse(ctx, nil, resp)
}
