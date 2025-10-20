package config

import (
	"fmt"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	webreq "k8s-dbs/dataweb/vo/request"
	"log/slog"

	"github.com/jinzhu/copier"
)

// VMClusterConfigBuilder vm 集群配置构建器
type VMClusterConfigBuilder struct {
}

// BuildConfig 构建 config
func (v *VMClusterConfigBuilder) BuildConfig(installRequest *webreq.ClusterInstallRequest) (
	*coreentity.Request,
	error,
) {
	storageAddonVersion, serviceVersion, err := parseInstallVersion(installRequest)
	if err != nil {
		slog.Error("failed to parse install version", "installRequest", installRequest, "err", err)
		return nil, err
	}
	clusterConfig, err := v.BuildBasicConfig(installRequest, storageAddonVersion)
	if err != nil {
		slog.Error("failed to build cluster config", "installRequest", installRequest, "err", err)
		return nil, err
	}
	componentList, err := v.BuildComponentList(installRequest, serviceVersion)
	if err != nil {
		slog.Error("failed to build component list", "installRequest", installRequest, "err", err)
		return nil, err
	}
	clusterConfig.ComponentList = componentList
	return clusterConfig, nil
}

// BuildBasicConfig 构建基础配置信息
func (v *VMClusterConfigBuilder) BuildBasicConfig(
	request *webreq.ClusterInstallRequest,
	storageAddonVersion string,
) (*coreentity.Request, error) {
	return buildBasicClusterConfig(request, storageAddonVersion)
}

// BuildComponentList 构建组件配置列表
func (v *VMClusterConfigBuilder) BuildComponentList(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) ([]coreentity.ComponentResource, error) {
	switch installRequest.ResourceConfig.TopoName {
	case coreconst.VMClusterTopo:
		componentList, err := v.buildComponentsInCluster(installRequest, serviceVersion)
		if err != nil {
			slog.Error("failed to build component list", "installRequest", installRequest, "err", err)
			return nil, err
		}
		return componentList, nil
	case coreconst.VMQueryTopo:
		componentList, err := v.buildComponentsInSelect(installRequest, serviceVersion)
		if err != nil {
			return nil, err
		}
		return componentList, nil
	default:
		return nil, fmt.Errorf("unknown topo name %v", installRequest.ResourceConfig.TopoName)
	}
}

// BuildEnvConfig 构建vm env
func (v *VMClusterConfigBuilder) BuildEnvConfig(request *webreq.ClusterUpdatedRequest) (*coreentity.Request, error) {
	for i, resource := range request.ComponentList {
		if resource.Config == nil {
			continue
		}
		// 初始化
		envMap := make(map[string]interface{})
		request.ComponentList[i].Env = envMap
		request.ComponentList[i].Env["EXTRA_ARGS"] = resource.Config
	}
	var result = &coreentity.Request{}
	err := copier.Copy(result, request)
	if err != nil {
		return nil, err
	}
	return result, nil
}

// ParseEnvConfig 解析Env
func (v *VMClusterConfigBuilder) ParseEnvConfig(request *coreentity.ComponentDetail) (*webreq.ComponentDetail, error) {
	var result = &webreq.ComponentDetail{}
	err := copier.Copy(result, request)
	if err != nil {
		return nil, err
	}
	// EXTRA_ARGS才处理
	if request.Env != nil {
		for _, envVar := range request.Env {
			if envVar.Name == "EXTRA_ARGS" {
				argsMap := parseCommandLineArgs(envVar.Value)
				result.Config = argsMap
			}
		}
	}
	return result, nil
}

// buildComponentsInSelect Victoriametrics 查询模式构建组件列表
func (v *VMClusterConfigBuilder) buildComponentsInSelect(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) ([]coreentity.ComponentResource, error) {
	var componentList []coreentity.ComponentResource
	for _, component := range installRequest.ResourceConfig.ComponentList {
		if component.ComponentName == coreconst.VMSelect {
			componentResource := buildComponentResource(component, serviceVersion)
			componentResource.Env = map[string]interface{}{
				"EXTRA_ARGS": map[string]interface{}{
					"storageNode": component.StorageNode,
				},
			}
			componentList = append(componentList, componentResource)
			break
		}
	}
	if len(componentList) == 0 {
		return nil, fmt.Errorf("failed to find the vmselect component")
	}
	return componentList, nil
}

// buildComponentsInCluster Victoriametrics 集群模式构建组件配置列表
func (v *VMClusterConfigBuilder) buildComponentsInCluster(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) ([]coreentity.ComponentResource, error) {
	componentList := make([]coreentity.ComponentResource, 0, len(installRequest.ResourceConfig.ComponentList))
	for _, component := range installRequest.ResourceConfig.ComponentList {
		componentResource := buildComponentResource(component, serviceVersion)
		if component.ComponentName == coreconst.VMStorage {
			componentResource.VolumeClaimTemplates = &coreentity.VolumeClaimTemplates{
				AccessModes:      []string{"ReadWriteOnce"},
				StorageClassName: "cbs",
				VolumeMode:       "Filesystem",
				Storage:          component.Storage,
			}
		}
		componentResource.Env = v.buildComponentEnv(component)
		componentList = append(componentList, componentResource)
	}
	return componentList, nil
}

// buildComponentEnv 构建 Component Env
func (v *VMClusterConfigBuilder) buildComponentEnv(component webreq.Component) map[string]interface{} {
	envMap := make(map[string]interface{})
	// 默认env
	switch component.ComponentName {
	case coreconst.VMSelect:
		envMap["EXTRA_ARGS"] = map[string]interface{}{
			"envflag.enable":                     "true",
			"envflag.prefix":                     "VM_",
			"loggerFormat":                       "json",
			"cacheExpireDuration":                "5m",
			"search.maxUniqueTimeseries":         "500000",
			"search.maxSamplesPerQuery":          "1000000000",
			"search.maxPointsPerTimeseries":      "500000",
			"search.maxSeries":                   "200000",
			"memory.allowedPercent":              "20",
			"search.maxMemoryPerQuery":           "2GB",
			"search.logQueryMemoryUsage":         "1GB",
			"search.logSlowQueryDuration":        "5s",
			"search.queryStats.lastQueriesCount": "10000",
			"search.queryStats.minQueryDuration": "3s",
			"search.maxQueryLen":                 "4MB",
			"dedup.minScrapeInterval":            "1ms",
			"search.maxConcurrentRequests":       "16",
		}
	case coreconst.VMInsert:
		envMap["EXTRA_ARGS"] = map[string]interface{}{
			"envflag.enable":         "true",
			"envflag.prefix":         "VM_",
			"loggerFormat":           "json",
			"influxDBLabel":          "__bk_db__",
			"maxLabelsPerTimeseries": "100",
		}
	case coreconst.VMStorage:
		envMap["EXTRA_ARGS"] = map[string]interface{}{
			"envflag.enable":               "true",
			"envflag.prefix":               "VM_",
			"loggerFormat":                 "json",
			"cacheExpireDuration":          "15m",
			"dedup.minScrapeInterval":      "1ms",
			"internStringMaxLen":           "128",
			"memory.allowedPercent":        "50",
			"retentionPeriod":              6,
			"search.maxConcurrentRequests": "16",
		}
	}
	// 如果有自定义env，则进行合并
	if component.Env != nil {
		for key, value := range component.Env {
			envMap["EXTRA_ARGS"].(map[string]interface{})[key] = value
		}
	}
	return envMap
}
