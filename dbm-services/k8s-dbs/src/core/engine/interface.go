package engine

import (
	"k8s-dbs/src/core/client"
	"k8s-dbs/src/core/entity"

	"github.com/gin-gonic/gin"
)

// CrdOperator database cluster operators
type CrdOperator interface {
	CreateCluster(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterResponseData, error)
	DeleteCluster(k8sClient *client.K8sClient, ctx *gin.Context, clusterData *entity.ClusterResponseData, request *entity.Request) error
	DescribeCluster(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterResponseData, error)
	GetClusterStatus(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) (*entity.ClusterStatus, error)
	CreateCdCmpdCmpv(k8sClient *client.K8sClient, ctx *gin.Context, request *entity.Request) error

	// InitRequestParams param
	InitRequestParams(ctx *gin.Context, request *entity.Request) error
}
