package router

import (
	"k8s-dbs/src/common/api"
	"k8s-dbs/src/core/api/controller"
	"k8s-dbs/src/core/provider/cluster_manage"
	"k8s-dbs/src/core/provider/ops_manage"
	metaapi "k8s-dbs/src/metadata/api/controller"
	"k8s-dbs/src/metadata/dbaccess"
	"k8s-dbs/src/metadata/provider"
	"log"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

const basePath = "/v4/dbs"

type Router struct {
	Engine *gin.Engine
}

func (r *Router) Run(addr string) {
	if err := r.Engine.Run(addr); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}

func NewRouter(db *gorm.DB) *Router {
	router := gin.Default()

	router.GET(basePath+api.HealthCheckUrl, api.HealthCheck)

	buildClusterRouter(db, router)

	buildMetaRouter(db, router)

	return &Router{Engine: router}
}

func buildMetaRouter(db *gorm.DB, router *gin.Engine) {
	metaRouter := router.Group(basePath + "/metadata")
	{
		buildAddonMetaRouter(db, metaRouter)

		buildCdMetaRouter(db, metaRouter)

		buildCmpdMetaRouter(db, metaRouter)

		buildCmpvMetaRouter(db, metaRouter)

		buildClusterMetaRouter(db, metaRouter)

		buildOpsMetaRouter(db, metaRouter)

		buildComponentMetaRouter(db, metaRouter)

		buildClusterConfigMetaRouter(db, metaRouter)
	}
}

func buildClusterConfigMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	k8sClusterConfigDbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := provider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	k8sClusterConfigController := metaapi.NewK8sClusterConfigController(k8sClusterConfigProvider)
	k8sClusterConfigMetaGroup := metaRouter.Group("/k8s_cluster_config")
	{
		k8sClusterConfigMetaGroup.GET("/id/:id", k8sClusterConfigController.GetK8sClusterConfigById)
		k8sClusterConfigMetaGroup.GET("/name/:cluster_name", k8sClusterConfigController.GetK8sClusterConfigByName)
		k8sClusterConfigMetaGroup.DELETE("/:id", k8sClusterConfigController.DeleteK8sClusterConfig)
		k8sClusterConfigMetaGroup.POST("", k8sClusterConfigController.CreateK8sClusterConfig)
		k8sClusterConfigMetaGroup.PUT("/:id", k8sClusterConfigController.UpdateK8sClusterConfig)
	}
}

func buildComponentMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	componentMetaDbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	componentMetaProvider := provider.NewK8sCrdComponentProvider(componentMetaDbAccess)
	componentMetaController := metaapi.NewComponentController(componentMetaProvider)
	componentMetaGroup := metaRouter.Group("/component")
	{
		componentMetaGroup.GET("/:id", componentMetaController.GetComponent)
	}
}

func buildOpsMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	opsMetaDbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)
	opsMetaProvider := provider.NewK8sCrdOpsRequestProvider(opsMetaDbAccess)
	opsMetaController := metaapi.NewOpsController(opsMetaProvider)
	opsMetaGroup := metaRouter.Group("/ops")
	{
		opsMetaGroup.GET("/:id", opsMetaController.GetOps)
	}
}

func buildClusterMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	clusterMetaDbAccess := dbaccess.NewCrdClusterDbAccess(db)
	clusterMetaProvider := provider.NewK8sCrdClusterProvider(clusterMetaDbAccess)
	clusterMetaController := metaapi.NewClusterController(clusterMetaProvider)
	clusterMetaGroup := metaRouter.Group("/cluster")
	{
		clusterMetaGroup.GET("/:id", clusterMetaController.GetCluster)
	}
}

func buildCmpvMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	cmpvMetaDbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)
	cmpvMetaProvider := provider.NewK8sCrdComponentVersionProvider(cmpvMetaDbAccess)
	cmpvMetaController := metaapi.NewCmpvController(cmpvMetaProvider)
	cmpvMetaGroup := metaRouter.Group("/cmpv")
	{
		cmpvMetaGroup.GET("/:id", cmpvMetaController.GetCmpv)
		cmpvMetaGroup.DELETE("/:id", cmpvMetaController.DeleteCmpv)
		cmpvMetaGroup.POST("", cmpvMetaController.CreateCmpv)
		cmpvMetaGroup.PUT("/:id", cmpvMetaController.UpdateCmpv)
	}
}

func buildCmpdMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	cmpdMetaDbAccess := dbaccess.NewK8sCrdComponentDefinitionDbAccess(db)
	cmpdMetaProvider := provider.NewK8sCrdComponentDefinitionProvider(cmpdMetaDbAccess)
	cmpdMetaController := metaapi.NewCmpdController(cmpdMetaProvider)
	cmpdMetaGroup := metaRouter.Group("/cmpd")
	{
		cmpdMetaGroup.GET("/:id", cmpdMetaController.GetCmpd)
		cmpdMetaGroup.DELETE("/:id", cmpdMetaController.DeleteCmpd)
		cmpdMetaGroup.POST("", cmpdMetaController.CreateCmpd)
		cmpdMetaGroup.PUT("/:id", cmpdMetaController.UpdateCmpd)
	}
}

func buildCdMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	cdMetaDbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)
	cdMetaProvider := provider.NewK8sCrdClusterDefinitionProvider(cdMetaDbAccess)
	cdMetaController := metaapi.NewCdController(cdMetaProvider)
	cdMetaGroup := metaRouter.Group("/cd")
	{
		cdMetaGroup.GET("/:id", cdMetaController.GetCd)
		cdMetaGroup.DELETE("/:id", cdMetaController.DeleteCd)
		cdMetaGroup.POST("", cdMetaController.CreateCd)
		cdMetaGroup.PUT("/:id", cdMetaController.UpdateCd)
	}
}

func buildAddonMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	addonMetaDbAccess := dbaccess.NewK8sCrdStorageAddonDbAccess(db)
	addonMetaProvider := provider.NewK8sCrdStorageAddonProvider(addonMetaDbAccess)
	addonMetaController := metaapi.NewAddonController(addonMetaProvider)
	addonMetaGroup := metaRouter.Group("/addon")
	{
		addonMetaGroup.GET("/:id", addonMetaController.GetAddon)
		addonMetaGroup.DELETE("/:id", addonMetaController.DeleteAddon)
		addonMetaGroup.POST("", addonMetaController.CreateAddon)
		addonMetaGroup.PUT("/:id", addonMetaController.UpdateAddon)
	}
}

func buildClusterRouter(db *gorm.DB, router *gin.Engine) {
	clusterController := initClusterController(db)
	clusterGroup := router.Group(basePath + "/cluster")
	{

		clusterGroup.POST("/create", clusterController.CreateCluster)
		clusterGroup.POST("/delete", clusterController.DeleteCluster)
		clusterGroup.POST("/describe", clusterController.DescribeCluster)
		clusterGroup.POST("/status", clusterController.GetClusterStatus)

	}

	opsRequestGroup := router.Group(basePath + "/opsRequest")
	{
		opsRequestGroup.POST("/vscaling", clusterController.VerticalScaling)
		opsRequestGroup.POST("/hscaling", clusterController.HorizontalScaling)
		opsRequestGroup.POST("/start", clusterController.StartCluster)
		opsRequestGroup.POST("/stop", clusterController.StopCluster)
		opsRequestGroup.POST("/restart", clusterController.RestartCluster)
		opsRequestGroup.POST("/upgrade", clusterController.UpgradeCluster)
		opsRequestGroup.POST("/vexpansion", clusterController.VolumeExpansion)
		opsRequestGroup.POST("/expose", clusterController.ExposeCluster)
		opsRequestGroup.POST("/describe", clusterController.DescribeOpsRequest)
		opsRequestGroup.POST("/status", clusterController.GetOpsRequestStatus)
	}
}

func buildService(db *gorm.DB) (*cluster_manage.ClusterProvider, *ops_manage.OpsRequestProvider) {
	clusterDbAccess := dbaccess.NewCrdClusterDbAccess(db)
	clusterDefinitionDbAccess := dbaccess.NewK8sCrdClusterDefinitionDbAccess(db)
	componentDbAccess := dbaccess.NewK8sCrdComponentAccess(db)
	componentDefinitionDbAccess := dbaccess.NewK8sCrdComponentDefinitionDbAccess(db)
	componentVersionDbAccess := dbaccess.NewK8sCrdComponentVersionDbAccess(db)
	opsReqDbAccess := dbaccess.NewK8sCrdOpsRequestDbAccess(db)
	k8sClusterConfigDbAccess := dbaccess.NewK8sClusterConfigDbAccess(db)

	clusterProvider := provider.NewK8sCrdClusterProvider(clusterDbAccess)
	clusterDefinitionProvider := provider.NewK8sCrdClusterDefinitionProvider(clusterDefinitionDbAccess)
	componentProvider := provider.NewK8sCrdComponentProvider(componentDbAccess)
	componentDefinitionProvider := provider.NewK8sCrdComponentDefinitionProvider(componentDefinitionDbAccess)
	componentVersionProvider := provider.NewK8sCrdComponentVersionProvider(componentVersionDbAccess)
	opsReqProvider := provider.NewK8sCrdOpsRequestProvider(opsReqDbAccess)
	k8sClusterConfigProvider := provider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)

	clusterService := cluster_manage.NewClusterService(
		clusterProvider,
		componentProvider,
		clusterDefinitionProvider,
		componentDefinitionProvider,
		componentVersionProvider,
		k8sClusterConfigProvider,
	)
	opsReqService := ops_manage.NewOpsRequestService(opsReqProvider, clusterProvider, clusterService, k8sClusterConfigProvider)
	return clusterService, opsReqService
}

func initClusterController(db *gorm.DB) *controller.ClusterController {
	return controller.NewClusterController(buildService(db))
}
