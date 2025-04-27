package controller

import (
	"k8s-dbs/src/core/entity"
	"k8s-dbs/src/core/errors"
	"k8s-dbs/src/metadata/api/vo/resp"
	"k8s-dbs/src/metadata/provider"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

type OpsController struct {
	opsProvider provider.K8sCrdOpsRequestProvider
}

func NewOpsController(opsProvider provider.K8sCrdOpsRequestProvider) *OpsController {
	return &OpsController{opsProvider}
}

func (o *OpsController) GetOps(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	ops, err := o.opsProvider.FindOpsRequestById(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var data resp.K8sCrdOpsRequestRespVo
		if err := copier.Copy(&data, ops); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, data, "OK")
			return
		}
	}
}
