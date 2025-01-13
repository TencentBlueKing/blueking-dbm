package simple

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/handler"
	"bk-dbconfig/internal/service/simpleconfig"

	"github.com/gin-gonic/gin"

	"dbm-services/common/go-pubpkg/validate"
)

// ChangeBizBizId godoc
//
// @Summary      修改集群的业务
// @Description  修改集群的业务归属
// @Tags         config_version
// @Accept       json
// @Produce      json
// @Param        body body     api.ChangeBkBizIdReq  true  "change bk_biz_id for clusters"
// @Success      200  {object}  api.ChangeBkBizIdResp
// @Failure      400  {object}  api.HTTPClientErrResp
// @Router       /bkconfig/v1/version/change_bk_biz_id [post]
func (cf *Config) ChangeBizBizId(ctx *gin.Context) {
	var r api.ChangeBkBizIdReq
	var resp *api.ChangeBkBizIdResp
	var err error
	if err = ctx.BindJSON(&r); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	if err := validate.GoValidateStruct(r, false); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	//r.ClusterDomains = cmutil.UniqueStrings(r.ClusterDomains)
	if resp, err = simpleconfig.ChangeBkBizId(&r, ""); err != nil {
		handler.SendResponse(ctx, err, nil)
		return
	}
	resp.ClusterReceived = len(r.ClusterDomains)
	handler.SendResponse(ctx, nil, resp)
	return
}
