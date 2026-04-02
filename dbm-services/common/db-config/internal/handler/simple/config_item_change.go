package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

	"github.com/gin-gonic/gin"
)

// QueryConfItemChanges godoc
//
// @Summary      查询配置的变更历史
// @Description  查询集群/业务配置项的操作历史记录，bk_biz_id 和 namespace 必填，
// conf_type/conf_file/conf_name/level_name/level_value 可选
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
// @Success      200  {object}  []api.ConfItemChangesQueryRowResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/changes [get]
func (cf *Config) QueryConfItemChanges(ctx *gin.Context) {
	var req api.ConfItemChangesQueryReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)

	if err = ctx.ShouldBindQuery(&req); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	changes, err := simpleconfig.QueryConfItemChanges(&req)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, nil, changes)
}
