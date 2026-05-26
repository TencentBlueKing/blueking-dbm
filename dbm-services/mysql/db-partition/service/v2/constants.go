package v2

// v2 包内使用的常量（不依赖 v1 未导出常量）

const (
	// phase 值
	phaseOnline         = "online"
	phaseOffline        = "offline"
	phaseOfflineWithClu = "offlinewithclu"

	// partition 默认值
	extraPartitionDefault = 15

	// manage log operate 值
	opInsert           = "Insert"
	opUpdate           = "Update"
	opDelete           = "Delete"
	opDisable          = "Disable"
	opEnable           = "Enable"
	opDisableByCluster = "DisableByCluster"
	opEnableByCluster  = "EnableByCluster"
	opDeleteByCluster  = "Delete by cluster"
)
