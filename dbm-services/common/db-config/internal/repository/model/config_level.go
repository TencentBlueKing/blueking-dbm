package model

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/pkg/cst"
	"bk-dbconfig/pkg/util"
)

// GetParentLevelStraight 获得合法的直接上层级名
func GetParentLevelStraight(namespace, confType, confFile, curLevelName string) string {
	fd := api.BaseConfFileDef{Namespace: namespace, ConfType: confType, ConfFile: confFile}
	if fileDef, err := CacheGetConfigFile(fd); err == nil {
		levelNames := util.SplitAnyRuneTrim(fileDef.LevelNames, ",")
		if len(levelNames) > 0 {
			return GetConfigLevelsUp(curLevelName, levelNames, true)[0]
		}
	}
	return ""
}

// GetChildLevelStraight 获得合法的直接下层级名
func GetChildLevelStraight(namespace, confType, confFile, curLevelName string) string {
	fd := api.BaseConfFileDef{Namespace: namespace, ConfType: confType, ConfFile: confFile}
	if fileDef, err := CacheGetConfigFile(fd); err == nil {
		levelNames := util.SplitAnyRuneTrim(fileDef.LevelNames, ",")
		if len(levelNames) > 0 {
			return GetConfigLevelsDown(curLevelName, levelNames, true)[0]
		}
	}
	return ""
}

// GetConfigLevelsUp 获取指定 level 的上级，如果 straight=true，只返回直接上级
// priority 越大，优先级越高，level 越低(plat, app, module, cluster, instance)
func GetConfigLevelsUp(levelName string, names []string, straight bool) []string {
	configLevelMap := cst.GetConfigLevelMap("")
	levelPriority, _ := configLevelMap[levelName]

	configLevels := make([]string, 0)
	maxLevelName := ""
	maxLevelPrio := 0
	for k, v := range configLevelMap {
		if !util.StringsHas(names, k) {
			continue
		}
		if v < levelPriority {
			configLevels = append(configLevels, k)
			// 在左边找个最大值 1 <2> [3] 4
			if v > maxLevelPrio {
				maxLevelPrio = v
				maxLevelName = k
			}
		}
	}
	if straight {
		return []string{maxLevelName}
	}
	return configLevels
}

// GetConfigLevelsDown 获取指定 level 的下级，如果 straight=true，只返回直接下级
func GetConfigLevelsDown(levelName string, names []string, straight bool) []string {
	configLevelMap := cst.GetConfigLevelMap("")
	levelPriority, _ := configLevelMap[levelName]

	configLevels := make([]string, 0)
	minLevelName := ""
	minLevelPrio := 9999
	for k, v := range configLevelMap {
		if !util.StringsHas(names, k) {
			continue
		}
		if v > levelPriority {
			configLevels = append(configLevels, k)
			// 在右边找个最小值 [2] <3> 4 5
			if v < minLevelPrio {
				minLevelPrio = v
				minLevelName = k
			}
		}
	}
	if straight {
		return []string{minLevelName}
	}
	return configLevels
}
