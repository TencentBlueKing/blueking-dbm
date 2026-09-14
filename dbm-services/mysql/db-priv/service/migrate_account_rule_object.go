package service

// MigrateInDbmPara DBM不同业务间迁移帐号规则的入参
type MigrateInDbmPara struct {
	SourceBiz   int64    `json:"source_biz"`
	TargetBiz   int64    `json:"target_biz"`
	ClusterType *string  `json:"cluster_type"`
	Users       []string `json:"users"`
}
