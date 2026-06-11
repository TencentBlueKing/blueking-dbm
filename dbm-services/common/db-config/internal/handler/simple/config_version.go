package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"

	"dbm-services/common/go-pubpkg/validate"

	"github.com/gin-gonic/gin"
)

// GenerateConfigVersion godoc
//
// @Summary      生成并获取配置文件新版本
// @Description  从现有配置项直接生成配置文件并返回，每次调用会生成一个新版本，可以选择是否直接发布。这个接口一般用户后台服务查询配置
// @Description  修改配置并发布，使用 /confitem/upsert 接口
// @Description  直接查询配置文件内容，使用 /confitem/query 接口
// @Description  根据 `method` 生成方式不同，可以生成配置并存储 `GenerateAndSave`、生成配置并存储且发布`GenerateAndPublish`
// @Description   使用 `GenerateAndSave` 方式需要进一步调用 PublishConfigFile 接口进行发布
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.GenerateConfigReq  true  "Generate config file versioned"
// @Success      200  {object}  api.GenerateConfigResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/generate [post]
func (cf *Config) GenerateConfigVersion(ctx *gin.Context) {
	cf.MergeAndGetConfigItemsOne(ctx)
}

// ListConfigFileVersions godoc
//
// @Summary      查询历史配置版本名列表
// @Description  Get config file versions list
// @Tags         config_version
// @Produce      json
// @Param        body query     api.ListConfigVersionsReq  true  "query"
// @Success      200  {object}  api.ListConfigVersionsResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/list [get]
func (cf *Config) ListConfigFileVersions(ctx *gin.Context) {
	var r api.ListConfigVersionsReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp, err := simpleconfig.ListConfigFileVersions(&r)
	if err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
}
