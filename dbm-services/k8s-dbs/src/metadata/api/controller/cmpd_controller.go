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

type CmpdController struct {
	cmpdProvider provider.K8sCrdComponentDefinitionProvider
}

func NewCmpdController(cmpdProvider provider.K8sCrdComponentDefinitionProvider) *CmpdController {
	return &CmpdController{cmpdProvider}
}

func (c *CmpdController) GetCmpd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cd, err := c.cmpdProvider.FindComponentDefinitionById(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var data resp.K8sCrdCmpdRespVo
		if err := copier.Copy(&data, cd); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, data, "OK")
			return
		}
	}
}

func (c *CmpdController) CreateCmpd(ctx *gin.Context) {
	var cmpd req.K8sCrdCmpdReqVo
	if err := ctx.ShouldBindJSON(&cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var cmpdEntity entitys.K8sCrdComponentDefinitionEntity
	if err := copier.Copy(&cmpdEntity, &cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := c.cmpdProvider.CreateComponentDefinition(&cmpdEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCmpdRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, data, "OK")
		return
	}
}

func (c *CmpdController) UpdateCmpd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpd req.K8sCrdCmpdReqVo
	if err := ctx.ShouldBindJSON(&cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cmpdEntity entitys.K8sCrdComponentDefinitionEntity
	if err := copier.Copy(&cmpdEntity, cmpd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	cmpdEntity.ID = id
	rows, err := c.cmpdProvider.UpdateComponentDefinition(&cmpdEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
		return
	}
}

func (c *CmpdController) DeleteCmpd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	if id, err := strconv.ParseUint(idParam, 10, 64); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	} else {
		rows, err := c.cmpdProvider.DeleteComponentDefinitionById(id)
		if err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
			return
		}
	}
}
