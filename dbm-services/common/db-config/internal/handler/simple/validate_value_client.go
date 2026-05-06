package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
)

// ValidateValueClient validate value
// 实际用到的字段：op_type, =value_default, value_type,value_type_sub,value_allowed,flag_readonly
type ValidateValueClient []*api.UpsertConfNames

// ValidateValueForClient godoc
//
// @Summary      配置合法性校验
// @Description  根据 value, value_type, value_type_sub, value_allowed 校验配置合法性
// @Tags         config_item
// @Accept       json
// @Produce      json
// @Param        body body      ValidateValueClient true  "ConfName for ConfType"
// @Success      200  {object}  nil
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/validate [post]
func (cf *Config) ValidateValueForClient(ctx *gin.Context) {
	var err error
	var r ValidateValueClient
	defer util.LoggerErrorStack(logger.Error, err)

	/*
		使用 ctx.ShouldBindBodyWith(&r, binding.JSON) 替代 ctx.ShouldBindJSON(&r)
		ShouldBindBodyWith 会将请求体缓存到 gin 的 context 中，即使解析失败，body 内容也不会丢失
		解析失败时 通过 ctx.GetRawData() 获取完整的原始请求参数，作为 data 返回给客户端
	*/
	if err = ctx.ShouldBindBodyWith(&r, binding.JSON); err != nil {
		rawData, _ := ctx.GetRawData()
		handler.SendResponse(ctx, err, string(rawData))
		return
	}
	if err = simpleconfig.ValidateValueForClient(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, "ok")
		return
	}
}
