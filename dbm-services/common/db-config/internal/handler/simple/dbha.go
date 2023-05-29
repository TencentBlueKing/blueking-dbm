package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"

	"github.com/gin-gonic/gin"
)

// QueryAllValuesConfigName godoc
//
// @Summary      查询平台配置项列表
// @Description  查询 平台配置 某个配置类型/配置文件的所有配置名列表
// @Tags         plat_config
// @Produce      json
// @Param        body query     api.QueryConfigNamesReq  true  "query"
// @Success      200  {object}  api.QueryConfigNamesResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/queryname [get]
func (cf *Config) QueryAllValuesConfigName(ctx *gin.Context) {
	var r api.QueryConfigNamesReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err := simpleconfig.QueryConfigNames(&r, true)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}
