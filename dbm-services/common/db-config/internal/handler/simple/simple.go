// Package simple TODO
package simple

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// ConfigIfce TODO
type ConfigIfce interface {
	RegisterRoutes(group string, router *gin.Engine)
	Routes()
}

// Config TODO
type Config struct {
}

// Routes TODO
func (cf *Config) Routes() []*gin.RouteInfo {
	return []*gin.RouteInfo{
		// config_file
		{Method: http.MethodPost, Path: "/conffile/add", HandlerFunc: cf.UpsertConfigFilePlat},
		{Method: http.MethodPost, Path: "/conffile/update", HandlerFunc: cf.UpdateConfigFilePlat},
		{Method: http.MethodGet, Path: "/conffile/list", HandlerFunc: cf.ListConfigFiles},
		{Method: http.MethodGet, Path: "/conffile/query", HandlerFunc: cf.QueryConfigTypeNamesPlat},

		// config_version
		{Method: http.MethodGet, Path: "/version/list", HandlerFunc: cf.ListConfigFileVersions},
		{Method: http.MethodGet, Path: "/version/detail", HandlerFunc: cf.GetVersionedDetail},
		{Method: http.MethodPost, Path: "/version/generate", HandlerFunc: cf.GenerateConfigVersion},
		{Method: http.MethodPost, Path: "/version/publish", HandlerFunc: cf.PublishConfigFile},
		{Method: http.MethodPost, Path: "/version/applyinfo", HandlerFunc: cf.VersionApplyInfo},
		{Method: http.MethodPost, Path: "/version/applied", HandlerFunc: cf.VersionApplyStat},
		{Method: http.MethodPost, Path: "/version/status", HandlerFunc: cf.VersionStat},
		{Method: http.MethodPost, Path: "/version/applyitem", HandlerFunc: cf.ItemApply},

		// config_item
		{Method: http.MethodPost, Path: "/confitem/query", HandlerFunc: cf.MergeAndGetConfigItems},
		{Method: http.MethodPost, Path: "/confitem/queryone", HandlerFunc: cf.MergeAndGetConfigItemsOne},
		{Method: http.MethodPost, Path: "/confitem/upsert", HandlerFunc: cf.UpdateConfigFileItems},
		{Method: http.MethodPost, Path: "/confitem/save", HandlerFunc: cf.SaveConfigFileItems},
		{Method: http.MethodPost, Path: "/confitem/batchget", HandlerFunc: cf.BatchGetConfigOneItem},

		// config_meta
		{Method: http.MethodGet, Path: "/conftype/query", HandlerFunc: cf.QueryConfigTypeInfo},
		{Method: http.MethodGet, Path: "/confname/list", HandlerFunc: cf.QueryConfigTypeNames},
	}
}
