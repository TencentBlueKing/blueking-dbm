package common

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// LooseBackupTypeList 备份类型允许列表
func LooseBackupTypeList() []string {
	var ss []string
	for _, t := range cst.LooseBackupTypes {
		ss = append(ss, t...)
	}
	return ss
}

// LooseBackupTypeMap 将不规范的备份类型，映射成规范值
// 不区分大小写
func LooseBackupTypeMap(backupType string) string {
	for t, v := range cst.LooseBackupTypes {
		if util.StringsHasICase(v, backupType) {
			return t
		}
	}
	return backupType
}

// MapNameVarToConf godoc
func MapNameVarToConf(varName string) string {
	if val, ok := util.MycnfItemsMap[varName]; ok {
		return val
	}
	return varName
}
