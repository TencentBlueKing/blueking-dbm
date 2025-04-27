package controller

import (
	"fmt"
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

type K8sClusterConfigController struct {
	configProvider provider.K8sClusterConfigProvider
}

func NewK8sClusterConfigController(configProvider provider.K8sClusterConfigProvider) *K8sClusterConfigController {
	return &K8sClusterConfigController{configProvider}
}

func (k *K8sClusterConfigController) GetK8sClusterConfigById(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	config, err := k.configProvider.FindConfigById(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var respVo resp.K8sClusterConfigRespVo
		if err := copier.Copy(&respVo, config); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, respVo, "OK")
			return
		}
	}
}

func (k *K8sClusterConfigController) GetK8sClusterConfigByName(ctx *gin.Context) {
	nameParam := ctx.Param("cluster_name")
	if nameParam == "" {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, fmt.Errorf("cluster_name 参数不能为空")))
		return
	}
	config, err := k.configProvider.FindConfigByName(nameParam)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var respVo resp.K8sClusterConfigRespVo
		if err := copier.Copy(&respVo, config); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, respVo, "OK")
			return
		}
	}
}

func (k *K8sClusterConfigController) CreateK8sClusterConfig(ctx *gin.Context) {
	var reqVo req.K8sClusterConfigReqVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var configEntity entitys.K8sClusterConfigEntity
	if err := copier.Copy(&configEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	addedConfig, err := k.configProvider.CreateConfig(&configEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var respVo resp.K8sClusterConfigRespVo
	if err := copier.Copy(&respVo, addedConfig); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, respVo, "OK")
		return
	}

}

func (k *K8sClusterConfigController) UpdateK8sClusterConfig(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var reqVo req.K8sClusterConfigReqVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var configEntity entitys.K8sClusterConfigEntity
	if err := copier.Copy(&configEntity, reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	configEntity.ID = id
	rows, err := k.configProvider.UpdateConfig(&configEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	} else {
		entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
		return
	}
}

func (k *K8sClusterConfigController) DeleteK8sClusterConfig(ctx *gin.Context) {
	idParam := ctx.Param("id")
	if id, err := strconv.ParseUint(idParam, 10, 64); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	} else {
		rows, err := k.configProvider.DeleteConfigById(id)
		if err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, "OK")
			return
		}
	}
}
