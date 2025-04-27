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

type CdController struct {
	cdProvider provider.K8sCrdClusterDefinitionProvider
}

func NewCdController(cdProvider provider.K8sCrdClusterDefinitionProvider) *CdController {
	return &CdController{cdProvider}
}

func (c *CdController) GetCd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cd, err := c.cdProvider.FindClusterDefinitionById(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var data resp.K8sCrdCdRespVo
		if err := copier.Copy(&data, cd); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, data, "OK")
			return
		}
	}
}

func (c *CdController) CreateCd(ctx *gin.Context) {
	var cd req.K8sCrdCdReqVo
	if err := ctx.ShouldBindJSON(&cd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var cdEntity entitys.K8sCrdClusterDefinitionEntity
	if err := copier.Copy(&cdEntity, &cd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	added, err := c.cdProvider.CreateClusterDefinition(&cdEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var data resp.K8sCrdCdRespVo
	if err := copier.Copy(&data, added); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, data, "OK")
		return
	}

}

func (c *CdController) UpdateCd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cd req.K8sCrdCdReqVo
	if err := ctx.ShouldBindJSON(&cd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var cdEntity entitys.K8sCrdClusterDefinitionEntity
	if err := copier.Copy(&cdEntity, cd); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	cdEntity.ID = id
	rows, err := c.cdProvider.UpdateClusterDefinition(&cdEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
		return
	}
}

func (c *CdController) DeleteCd(ctx *gin.Context) {
	idParam := ctx.Param("id")
	if id, err := strconv.ParseUint(idParam, 10, 64); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	} else {
		rows, err := c.cdProvider.DeleteClusterDefinitionById(id)
		if err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
			return
		}
	}
}
