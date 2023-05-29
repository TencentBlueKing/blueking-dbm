package cst

import (
	"bk-dbconfig/pkg/constvar"
)

// ConfigLevelMap TODO
var ConfigLevelMap = map[string]int{
	constvar.LevelPlat: 10,
	"app":              20,
	"bk_biz_id":        20,
	"bk_cloud_id":      25,
	"module":           30,
	"db_module_id":     30,
	"cluster":          50,
	"role":             60,
	"host":             70,
	"instance":         80,
}

const (
	// Spider TODO
	Spider = "tendbcluster" // TenDBCluster
	// TenDBCluster TODO
	TenDBCluster = "tendbcluster"
	// TenDBHA TODO
	TenDBHA = "tendbha" // tendbha
	// TenDBSingle TODO
	TenDBSingle = "tendbsingle" // tendbsingle
)

// var NamespaceAllowed = []string{TenDBCluster, TenDBHA, TenDBSingle}

// GetConfigLevelMap TODO
func GetConfigLevelMap(confTpye string) map[string]int {
	return ConfigLevelMap
}

// GetConfigLevels TODO
func GetConfigLevels(confTpye string) []string {
	configLevelMap := GetConfigLevelMap(confTpye)

	configLevels := make([]string, len(configLevelMap))
	for k, _ := range configLevelMap {
		configLevels = append(configLevels, k)
	}
	return configLevels
}

// GetConfigLevelsUp TODO
func GetConfigLevelsUp(levelName string) []string {
	configLevelMap := GetConfigLevelMap("")
	levelPriority, _ := configLevelMap[levelName]

	configLevels := make([]string, 0)
	for k, v := range configLevelMap {
		if v < levelPriority {
			configLevels = append(configLevels, k)
		}
	}
	return configLevels
}

// GetConfigLevelsDown TODO
func GetConfigLevelsDown(levelName string) []string {
	configLevelMap := GetConfigLevelMap("")
	levelPriority, _ := configLevelMap[levelName]

	configLevels := make([]string, 0)
	for k, v := range configLevelMap {
		if v > levelPriority {
			configLevels = append(configLevels, k)
		}
	}
	return configLevels
}
