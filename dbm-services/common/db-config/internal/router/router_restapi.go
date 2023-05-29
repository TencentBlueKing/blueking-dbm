package router

import (
	"bk-dbconfig/docs"
	"net/http"

	"github.com/gin-gonic/gin"
)

// RegisterRoutesSwagger TODO
func RegisterRoutesSwagger(r *gin.Engine) {
	r.StaticFS("/docs", http.FS(docs.SwaggerDocs)) // embed
	// r.Static("/swagger", "./assets/swagger-ui")    // not embed
}

// RegisterRoutes TODO
func RegisterRoutes(router *gin.Engine, group string, routesInfo []*gin.RouteInfo) {
	r := router.Group(group)
	for _, route := range routesInfo {
		r.Handle(route.Method, route.Path, route.HandlerFunc)
	}
}

/*
// not use
func RegisterRoutesSimpleConfig(router *gin.Engine, c *simple.Config) {
    v1Router := router.Group("/bkconfig/v1/")
    {
        // config_file
        v1Router.GET("/conffile/get", c.GetVersionedConfigFile)
        v1Router.GET("/conffile/list", c.ListConfigFileVersions)
        v1Router.GET("/conffile/query", c.GenerateAndQueryConfig)
        v1Router.POST("/conffile/generate", c.GenerateConfigFile)
        v1Router.POST("/conffile/publish", c.PublishConfigFile)

        // config_meta
        v1Router.GET("/conftype/query", c.QueryConfigTypeInfo)
        v1Router.GET("/confname/query", c.QueryConfigTypeNames)
        v1Router.GET("/metafield/query", c.GetConfigMetaField)

        // cmdb
        v1Router.GET("/cmdb/module/query", c.GetConfigMetaField)
        v1Router.GET("/cmdb/module/list", c.ListModuleClusters)
        v1Router.POST("/cmdb/module/upsert", c.UpdateModuleClusters)

        // config_item
        v1Router.GET("/confitem/list", c.GetConfigList)
        v1Router.PUT("/confitem/upsert", c.CreateOrUpdateConfig)
        v1Router.POST("/confitem/upsert", c.CreateOrUpdateConfig)
        v1Router.POST("/confitem/commit", c.CreateOrUpdateConfig)
        v1Router.POST("/confitem/rollback", c.CreateOrUpdateConfig)
    }

}
*/
