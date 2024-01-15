package consts

// dts type
const (
	DtsTypeOneAppDiffCluster  = "one_app_diff_cluster"  // 一个业务下的不同集群
	DtsTypeDiffAppDiffCluster = "diff_app_diff_cluster" // 不同业务下的不同集群
	DtsTypeSyncToOtherSystem  = "sync_to_other_system"  // 同步到其他系统,如迁移到腾讯云
	DtsTypeUserBuiltToDbm     = "user_built_to_dbm"     // 用户自建redis到dbm系统
)

// IsDtsTypeSrcClusterBelongDbm (该dst类型中)源集群是否属于dbm系统
func IsDtsTypeSrcClusterBelongDbm(dtsType string) bool {
	if dtsType == DtsTypeOneAppDiffCluster ||
		dtsType == DtsTypeDiffAppDiffCluster ||
		dtsType == DtsTypeSyncToOtherSystem {
		return true
	}
	return false
}

// dts datacheck mode
const (
	DtsDataCheckByKeysFileMode = "bykeysfile" // 基于key提取结果,做数据校验
	DtsDataCheckByScanMode     = "byscan"     // 通过scan命令获取key名,做数据校验
)
