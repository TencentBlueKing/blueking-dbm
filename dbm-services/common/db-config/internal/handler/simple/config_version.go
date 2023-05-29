package simple

import (
	"fmt"
	"math/rand"
	"time"

	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/internal/service/simpleconfig"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"bk-dbconfig/pkg/validate"

	"github.com/gin-gonic/gin"
	"github.com/pkg/errors"
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
	var r api.GenerateConfigReq
	var resp *api.GenerateConfigResp
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := r.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := simpleconfig.CheckValidConfType(r.Namespace, r.ConfType, r.ConfFile, r.LevelName, 1); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	levelNode := api.BaseConfigNode{}
	levelNode.Set(r.BKBizID, r.Namespace, r.ConfType, r.ConfFile, r.LevelName, r.LevelValue)
	var r2 = &api.SimpleConfigQueryReq{
		BaseConfigNode: levelNode,
		Format:         r.Format,
		View:           constvar.ViewMerge,
		CreatedBy:      opUser,
		InheritFrom:    constvar.BKBizIDForPlat,
		UpLevelInfo:    r.UpLevelInfo,
	}
	if err = r2.Validate(); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if !model.IsConfigLevelEntityVersioned(r.Namespace, r.ConfType, r.ConfFile, r.LevelName) {
		handler.SendResponse(ctx, errors.New("only entity level allow generate api"), nil)
		return
	}
	r2.Decrypt = true
	r2.Generate = true

	v := &model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
	}
	// 这里先判断是否存在已 applied(即 generated)
	var exists bool
	var expires = true
	// 可能存在并发的问题，随机 sleep 0-2 s
	time.Sleep(time.Duration(rand.Intn(2000)) * time.Millisecond)
	if exists, err = v.ExistsAppliedVersion(model.DB.Self); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}

	if exists {
		logger.Info("generated ever: %+v", r)
		// 之前generate过，判断是否过期
		if vConfigs, err := v.GetVersionPublished(model.DB.Self); err == nil {
			nowTime := time.Now()
			createTime, _ := time.ParseInLocation(model.DBTimeFormat, vConfigs.Versioned.CreatedAt.String(), time.Local)
			if nowTime.Sub(createTime).Seconds() < 10 { // 10s 内重复 generate 会直接返回 published
				expires = false
			}
		}
		if !expires { // generate 没有过期，直接从 tb_config_version 查询 published
			logger.Info("level_node has applied versioned and un-expire, query configs instead of generate")
			if resp, err = simpleconfig.QueryConfigItemsFromVersion(r2, false); err != nil {
				handler.SendResponse(ctx, err, nil)
				return
			} else {
				handler.SendResponse(ctx, nil, resp)
				return
			}
		} // else 过期了，需要重新生成 revision
	} else {
		logger.Info("generate the first time: %+v", r)
	}
	// generated version 不存在，或者存在但已过期，都需进行 generate
	if err := simpleconfig.SaveConfigFileNode(model.DB.Self, &levelNode, opUser, "generated", ""); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	// generate 有 3 种情况：
	// 1. 第一次 generate, 且顺利完成
	// 2. 多个请求并行generate，报重复错误的，直接读取
	// 3. 之前 generate 已过期
	// 还有一种极端情况，多个请求并行generate，但时间是错开不在 1s内，也能generate成功
	if resp, err = simpleconfig.GenerateConfigFile(model.DB.Self, r2, r.Method, nil); err != nil {
		//logger.Warn("simpleconfig.GenerateConfigFile err: %+v", err)
		if util.IsErrorString(err, "Error 1062: Duplicate entry") ||
			util.IsErrorString(err, "Error 1213: Deadlock found when trying to get lock") ||
			util.IsErrorString(err, "revision is applied already:") {
			// 前面已经判断不存在，现在写入报重复，说明有其它请求 generate version 了。直接读取
			logger.Info("level_node has applied versioned, query configs instead of generate")
			if resp, err = simpleconfig.QueryConfigItemsFromVersion(r2, false); err != nil {
				handler.SendResponse(ctx, err, nil)
				return
			} else {
				handler.SendResponse(ctx, nil, resp)
				return
			}
		} else {
			handler.SendResponse(ctx, err, nil)
			return
		}
	} else if len(resp.Content) > 0 {
		handler.SendResponse(ctx, nil, resp)
		return
	} else {
		handler.SendResponse(ctx, fmt.Errorf("no result"), resp)
		return
	}
}

// PublishConfigFile godoc
//
// @Summary      直接发布一个版本[废弃]
// @Description  发布指定版本的配置文件，未发布状态的配置文件是不能使用的
// @Description  发布操作会把已有 published 状态的配置文件下线；同一个 revision 版本的配置无法重复发布
// @Description  发布时带上 patch 参数可以覆盖配置中心该版本的配置项(只有配置项值是`{{`开头的才能被覆盖)
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.PublishConfigFileReq  true  "Publish config file versioned"
// @Success      200  {object}  api.HTTPOkNilResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/publish [post]
func (cf *Config) PublishConfigFile(ctx *gin.Context) {
	var r api.PublishConfigFileReq
	var err error
	defer util.LoggerErrorStack(logger.Error, err)
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	opUser := api.GetHeaderUsername(ctx.GetHeader(constvar.BKApiAuthorization))
	var v = model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		ConfFile:   r.ConfFile,
		ConfType:   r.ConfType,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		Revision:   r.Revision,
		CreatedBy:  opUser,
	}
	publishService := simpleconfig.PublishConfig{
		Versioned:     &v,
		Patch:         r.Patch,
		ConfigsLocked: nil,
		LevelNode: api.BaseConfigNode{
			BKBizIDDef: api.BKBizIDDef{BKBizID: r.BKBizID},
			BaseConfFileDef: api.BaseConfFileDef{
				Namespace: r.Namespace,
				ConfType:  r.ConfType,
				ConfFile:  r.ConfFile,
			},
			BaseLevelDef: api.BaseLevelDef{
				LevelName:  r.LevelName,
				LevelValue: r.LevelValue,
			},
		},
	}
	if err = publishService.PublishAndApplyVersioned(model.DB.Self, false); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, nil, nil)
	return
}

// GetVersionedDetail godoc
//
// @Summary      查询版本的详细信息
// @Description  查询历史配置版本的详情，format 指定返回格式，revision 指定查询哪个版本（当 revision = "v_latest" 时，会返回当前最新的版本）
// @Tags         config_version
// @Produce      json
// @Param        body query     api.GetVersionedDetailReq  true  "query"
// @Success      200  {object}  api.GetVersionedDetailResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/detail [get]
func (cf *Config) GetVersionedDetail(ctx *gin.Context) {
	var r api.GetVersionedDetailReq
	if err := ctx.BindQuery(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, true); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if r.Format == "" {
		r.Format = constvar.FormatList
	}
	resp, err := simpleconfig.GetVersionedDetail(&r)
	if err != nil {
		logger.Errorf("%+v", err)
		handler.SendResponse(ctx, err, nil)
		return
	}
	handler.SendResponse(ctx, err, resp)
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
