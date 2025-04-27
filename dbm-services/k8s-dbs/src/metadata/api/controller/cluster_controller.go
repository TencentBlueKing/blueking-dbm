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

type ClusterController struct {
	clusterProvider provider.K8sCrdClusterProvider
}

func NewClusterController(clusterProvider provider.K8sCrdClusterProvider) *ClusterController {
	return &ClusterController{clusterProvider}
}

func (c *ClusterController) GetCluster(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	cluster, err := c.clusterProvider.FindClusterById(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	} else {
		var data resp.K8sCrdClusterRespVo
		if err := copier.Copy(&data, cluster); err != nil {
			entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
			return
		} else {
			entity.SuccessResponse(ctx, data, "OK")
			return
		}
	}
}
