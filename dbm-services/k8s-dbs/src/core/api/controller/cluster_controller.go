package controller

import (
	types "k8s-dbs/src/core/api/constants"
	"k8s-dbs/src/core/entity"
	"k8s-dbs/src/core/errors"
	"k8s-dbs/src/core/provider/cluster_manage"
	"k8s-dbs/src/core/provider/ops_manage"

	"github.com/gin-gonic/gin"
)

type ClusterController struct {
	clusterService    *cluster_manage.ClusterProvider
	opsRequestService *ops_manage.OpsRequestProvider
}

func NewClusterController(clusterService *cluster_manage.ClusterProvider, opsRequestService *ops_manage.OpsRequestProvider) *ClusterController {
	return &ClusterController{
		clusterService:    clusterService,
		opsRequestService: opsRequestService,
	}
}

func (c *ClusterController) VerticalScaling(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	responseData, err := c.opsRequestService.VerticalScaling(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.VerticalScalingError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.VerticalScalingSuccess)
}

func (c *ClusterController) HorizontalScaling(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	responseData, err := c.opsRequestService.HorizontalScaling(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.HorizontalScalingError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.HorizontalScalingSuccess)
}

func (c *ClusterController) StartCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.StartCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.StartClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.StartClusterSuccess)
}

func (c *ClusterController) RestartCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.RestartCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.RestartClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.RestartClusterSuccess)
}

func (c *ClusterController) StopCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.StopCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.StopClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.StopClusterSuccess)
}

func (c *ClusterController) UpgradeCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.UpgradeCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpgradeClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.UpgradeClusterSuccess)
}

func (c *ClusterController) VolumeExpansion(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	responseData, err := c.opsRequestService.VolumeExpansion(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.VolumeExpansionError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.VolumeExpansionSuccess)
}

func (c *ClusterController) DescribeOpsRequest(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	opsRequestData, err := c.opsRequestService.DescribeOpsRequest(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeOpsRequestError, err))
		return
	}
	entity.SuccessResponse(ctx, opsRequestData, types.DescribeOpsRequestSuccess)
}

func (c *ClusterController) GetOpsRequestStatus(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	opsRequestStatus, err := c.opsRequestService.GetOpsRequestStatus(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetOpsRequestStatusError, err))
		return
	}
	entity.SuccessResponse(ctx, opsRequestStatus, types.GetOpsRequestStatusSuccess)
}

func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	err = c.clusterService.CreateCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, nil, types.CreateClusterSuccess)
}

func (c *ClusterController) DeleteCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	err = c.clusterService.DeleteCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, nil, types.DeleteClusterSuccess)
}

func (c *ClusterController) DescribeCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	clusterData, err := c.clusterService.DescribeCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DescribeClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, clusterData, types.DescribeClusterSuccess)
}

func (c *ClusterController) GetClusterStatus(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	clusterStatus, err := c.clusterService.GetClusterStatus(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetClusterStatusError, err))
		return
	}
	entity.SuccessResponse(ctx, clusterStatus, types.GetClusterStatsuSuccess)
}

func (c *ClusterController) ExposeCluster(ctx *gin.Context) {
	request := &entity.Request{}
	err := ctx.BindJSON(&request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	responseData, err := c.opsRequestService.ExposeCluster(request)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.ExposeClusterError, err))
		return
	}
	entity.SuccessResponse(ctx, responseData, types.ExposeClusterSuccess)
}
