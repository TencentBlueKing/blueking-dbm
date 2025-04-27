package controller

import (
	"k8s-dbs/src/core/entity"
	"k8s-dbs/src/core/errors"
	"k8s-dbs/src/metadata/api/vo/req"
	"k8s-dbs/src/metadata/api/vo/resp"
	"k8s-dbs/src/metadata/provider"
	entitys "k8s-dbs/src/metadata/provider/entity"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

type CmpvController struct {
	cmpvProvider provider.K8sCrdComponentVersionProvider
}

func NewCmpvController(cmpvProvider provider.K8sCrdComponentVersionProvider) *CmpvController {
	return &CmpvController{cmpvProvider}
}

func (c *CmpvController) GetCmpv(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cd, err := c.cmpvProvider.FindComponentVersionById(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var data resp.K8sCrdCmpvRespVo
		if err := copier.Copy(&data, cd); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, data, "OK")
			return
		}
	}
}

func (c *CmpvController) CreateCmpv(ctx *gin.Context) {
	var cmpv req.K8sCrdCmpvReqVo
	if err := ctx.ShouldBindJSON(&cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var cmpvEntity entitys.K8sCrdComponentVersionEntity
	if err := copier.Copy(&cmpvEntity, &cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := c.cmpvProvider.CreateComponentVersion(&cmpvEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCmpvRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, data, "OK")
		return
	}
}

func (c *CmpvController) UpdateCmpv(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpv req.K8sCrdCmpvReqVo
	if err := ctx.ShouldBindJSON(&cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpvEntity entitys.K8sCrdComponentVersionEntity
	if err := copier.Copy(&cmpvEntity, cmpv); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	cmpvEntity.ID = id
	rows, err := c.cmpvProvider.UpdateComponentVersion(&cmpvEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
		return
	}
}

func (c *CmpvController) DeleteCmpv(ctx *gin.Context) {
	idParam := ctx.Param("id")
	if id, err := strconv.ParseUint(idParam, 10, 64); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	} else {
		rows, err := c.cmpvProvider.DeleteComponentVersionById(id)
		if err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
			return
		}
	}
}
