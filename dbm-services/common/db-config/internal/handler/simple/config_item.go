package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"fmt"

	"github.com/gin-gonic/gin"
)

// MergeAndGetConfigItems godoc
//
// @Summary      获取多个配置文件配置项列表
// @Description  根据业务/模块/集群的信息，获取某个配置文件的配置项。一般用户前端请求、再编辑的场景，后端服务直接获取配置文件使用 /version/generate 接口
// @Description     conf_file 可以是,号分隔的多个文件名，返回结果是一个按照配置文件名组合的一个 list
// @Description  需要指定返回格式 format, 可选值 map, list.
// @Description    map 格式会丢弃 conf_item 的其它信息，只保留 conf_name=conf_value, 一般用于后台服务
// @Description    list 格式会保留 conf_items 的其它信息，conf_name=conf_item，一般用于前端展示
// @Description  获取cluster级别配置时，需要提供 level_info:{"module":"xxx"} 模块信息
// @Tags         config_item
// @Accept      json
// @Produce      json
// @Param        body body     api.GetConfigItemsReq  true  "GetConfigItemsReq"
// @Success      200  {object}  []api.GetConfigItemsResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/query [post]
func (cf *Config) MergeAndGetConfigItems(ctx *gin.Context) {
	var r api.GetConfigItemsReq
	var resp []*api.GetConfigItemsResp
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
	levelNode := api.BaseConfigNode{}
	levelNode.Set(r.BKBizID, r.Namespace, r.ConfType, r.ConfFile, r.LevelName, r.LevelValue)
	var r2 = &api.SimpleConfigQueryReq{
		BaseConfigNode: levelNode,
		Format:         r.Format,
		View:           constvar.ViewMerge,
		InheritFrom:    "0",
		ConfName:       r.ConfName,
		UpLevelInfo:    r.UpLevelInfo,
	}
	if err = r2.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	confFiles := util.SplitAnyRuneTrim(r.ConfFile, ",")
	if resp, err = simpleconfig.GetConfigItemsForFiles(r2, confFiles); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else if len(resp) > 0 {
		handler.SendResponse(ctx, nil, resp)
		return
	} else {
		handler.SendResponse(ctx, fmt.Errorf("no result"), resp)
	}
}

// MergeAndGetConfigItemsOne godoc
//
// @Summary      获取一个配置文件配置项列表
// @Description  根据业务/模块/集群的信息，获取某个配置文件的配置项。一般用户前端请求、再编辑的场景，后端服务直接获取配置文件使用 /version/generate 接口
// @Description     注：与`/confitem/query` 接口使用相同，但该`/confitem/queryone` 只接受一个 conf_file，返回的是一个map
// @Description  需要指定返回格式 format, 可选值 map, list.
// @Description    map 格式会丢弃 conf_item 的其它信息，只保留 conf_name=conf_value, 一般用于后台服务
// @Description    list 格式会保留 conf_items 的其它信息，conf_name=conf_item，一般用于前端展示
// @Description  获取cluster级别配置时，需要提供 level_info:{"module":"xxx"} 模块信息
// @Tags         config_item
// @Accept      json
// @Produce      json
// @Param        body body     api.GetConfigItemsReq  true  "GetConfigItemsReq"
// @Success      200  {object}  api.GetConfigItemsResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/queryone [post]
func (cf *Config) MergeAndGetConfigItemsOne(ctx *gin.Context) {
	var r api.GetConfigItemsReq
	var err error
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
	levelNode := api.BaseConfigNode{}
	levelNode.Set(r.BKBizID, r.Namespace, r.ConfType, r.ConfType, r.LevelName, r.LevelValue)
	var r2 = &api.SimpleConfigQueryReq{
		BaseConfigNode: levelNode,
		Format:         r.Format,
		View:           constvar.ViewMerge,
		InheritFrom:    "0",
		ConfName:       r.ConfName,
		UpLevelInfo:    r.UpLevelInfo,
	}
	if err := r2.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}

	if resp, err := simpleconfig.QueryConfigItems(r2, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
		return
	}
}

// UpdateConfigFileItems godoc
//
// @Summary      编辑发布层级配置
// @Description  编辑层级配置，层级包括业务app、模块module、集群cluster，需要指定修改哪个级别的配置，通过 level_name, level_value 来区分
// @Description  例1: level_name=app, level_value=testapp 表示修改业务 bk_biz_id=testapp 的配置
// @Description  例2: level_name=module, level_value=account 表示某业务 bk_biz_id 的模块 module=account 的配置
// @Description  HTTP Header 指定 `X-Bkapi-User-Name` 请求的操作人员
// @Description  获取cluster级别配置时，需要提供 level_info:{"module":"xxx"} 模块信息
// @Description  只修改配置项，不修改配置文件描述时，conf_file_info 只需要传 namespace, conf_type, conf_file
// @Tags         config_item
// @Accept       json
// @Produce      json
// @Param        body body     api.UpsertConfItemsReq  true  "UpsertConfItemsReq"
// @Success      200  {object}  api.UpsertConfItemsResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/upsert [post]
func (cf *Config) UpdateConfigFileItems(ctx *gin.Context) {
	var r api.UpsertConfItemsReq
	var resp *api.UpsertConfItemsResp
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
		r.ConfFileInfo.ConfFile, r.LevelName, 1); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	if resp, err = simpleconfig.UpdateConfigFileItems(&r, opUser); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
	}
}

// SaveConfigFileItems godoc
//
// @Summary      编辑配置(无版本概念)
// @Description  编辑层级配置，层级包括业务app、模块module、集群cluster，需要指定修改哪个级别的配置，通过 level_name, level_value 来区分
// @Description  针对编辑的配置类型 conf_type 无版本化的概念，即保存生效，无需发布
// @Description  保存 cluster级别配置时，需要提供 level_info:{"module":"xxx"} 模块信息
// @Tags         config_item
// @Accept       json
// @Produce      json
// @Param        body body     api.SaveConfItemsReq  true  "SaveConfItemsReq"
// @Success      200  {object}  api.UpsertConfItemsResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/confitem/save [post]
func (cf *Config) SaveConfigFileItems(ctx *gin.Context) {
	var r api.SaveConfItemsReq
	var resp *api.UpsertConfItemsResp
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
		r.ConfFileInfo.ConfFile, r.LevelName, 0); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	r2 := api.UpsertConfItemsReq{
		RequestType:      api.RequestType{ReqType: constvar.MethodSave},
		SaveConfItemsReq: r,
	}
	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	if resp, err = simpleconfig.UpdateConfigFileItems(&r2, opUser); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	} else {
		handler.SendResponse(ctx, nil, resp)
	}
}
