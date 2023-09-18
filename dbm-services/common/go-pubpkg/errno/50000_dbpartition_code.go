package errno

var (
	// NoTableMatched TODO
	NoTableMatched = Errno{Code: 52019, Message: "no table matched", CNMessage: "找不到匹配的表"}
	// ClusterIdIsEmpty TODO
	ClusterIdIsEmpty = Errno{Code: 52020, Message: "cluster_id can't be empty",
		CNMessage: "cluster_id不能为空"}
	// CheckPartitionFailed TODO
	CheckPartitionFailed = Errno{Code: 52021, Message: "partition check failed", CNMessage: "分区检查失败"}
	// PartitionConfigNotExisted TODO
	PartitionConfigNotExisted = Errno{Code: 52022, Message: "Partition config not existed ", CNMessage: "分区配置不存在"}
	// PartOfPartitionConfigsNotExisted TODO
	PartOfPartitionConfigsNotExisted = Errno{Code: 52023, Message: "part of artition configs not existed ",
		CNMessage: "部分分区配置不存在"}
	// NotSupportedClusterType TODO
	NotSupportedClusterType = Errno{Code: 52024, Message: "this instance type is not supportted by partition",
		CNMessage: "不支持的实例类型"}
	// ConfigIdIsEmpty TODO
	ConfigIdIsEmpty = Errno{Code: 52025, Message: "partition config id can't be empty",
		CNMessage: "partition config id 不能为空"}
	// GetPartitionSqlFail TODO
	GetPartitionSqlFail = Errno{Code: 52027, Message: "get partition sql failed", CNMessage: "获取分区语句失败"}
	// ExecutePartitionFail TODO
	ExecutePartitionFail = Errno{Code: 52028, Message: "execute partition failed", CNMessage: "执行分区失败"}
	// NothingToDo TODO
	NothingToDo = Errno{Code: 52029, Message: "nothing to do", CNMessage: "没有需要执行的操作"}
	// DomainNotExists TODO
	DomainNotExists           = Errno{Code: 52030, Message: "domain not exists", CNMessage: "域名不存在"}
	NotSupportedPartitionType = Errno{Code: 52031, Message: "not supported partition type", CNMessage: "不支持的分区类型"}
	WrongPartitionNameFormat  = Errno{Code: 52032, Message: "wrong partition name format ", CNMessage: "分区名格式错误"}
)
