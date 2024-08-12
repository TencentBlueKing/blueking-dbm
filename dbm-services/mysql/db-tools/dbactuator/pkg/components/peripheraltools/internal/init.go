package internal

type InstanceInfo struct {
	BkBizId      int    `json:"bk_biz_id"`
	Ip           string `json:"ip"`
	Port         int    `json:"port"`
	Role         string `json:"role"`
	ClusterId    int    `json:"cluster_id"`
	ImmuteDomain string `json:"immute_domain"`
	BkInstanceId int64  `json:"bk_instance_id,omitempty"` // 0 被视为空, 不序列化
	DBModuleId   int    `json:"db_module_id"`
}
