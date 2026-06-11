package simple

import (
	"fmt"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"

	"dbm-services/common/go-pubpkg/validate"
)

// ChangeConfigFilePlat godoc
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
// @Router       /bkconfig/v1/conffile/change [post]
func (cf *Config) ChangeConfigFilePlat(ctx *gin.Context) {
	var r api.ChangeConfFileDefReq
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err = validate.GoValidateStruct(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}

	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	r.UpdatedBy = opUser

	fileModel := model.ConfigFileDefModel{}
	if err = copier.Copy(&fileModel, r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if r.OPType == "upsert" {
		if err = fileModel.Upsert(model.DB.Self); err != nil {
			handler.SendResponse(ctx, err, nil)
			return
		}
	} else if r.OPType == "remove" {
		if err = model.DeleteByUnique(model.DB.Self, fileModel.TableName(), map[string]interface{}{
			"namespace": r.Namespace,
			"conf_type": r.ConfType,
			"conf_file": r.ConfFile,
		}); err != nil {
			handler.SendResponse(ctx, err, nil)
			return
		}
	} else {
		handler.SendResponse(ctx, fmt.Errorf("invalid op_type %s", r.OPType), nil)
		return
	}
	handler.SendResponse(ctx, nil, "ok")
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
