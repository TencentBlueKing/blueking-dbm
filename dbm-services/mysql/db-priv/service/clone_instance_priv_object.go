package service

import "sync"

// CloneInstancePrivParaList CloneInstancePrivDryRun函数的入参
type CloneInstancePrivParaList struct {
	BkBizId                  int64                   `json:"bk_biz_id"`
	CloneInstancePrivRecords []CloneInstancePrivPara `json:"clone_instance_priv_records"`
}

// visitor 访问语法树的结构体
type visitor struct {
	username    string
	hostname    string
	secText     string
	secPassword string
	withgrant   bool
	legal       bool
}

// CloneInstancePrivPara 克隆实例权限CloneInstancePriv、DealWithPrivileges函数的入参
type CloneInstancePrivPara struct {
	BkBizId   int64        `json:"bk_biz_id"`
	Operator  string       `json:"operator"`
	Source    InstancePara `json:"source"`
	Target    InstancePara `json:"target"`
	BkCloudId *int64       `json:"bk_cloud_id"`
}

// InstancePara TODO
type InstancePara struct {
	Address     string `json:"address"`
	MachineType string `json:"machine_type"`
}

// InstanceDetail GetInstanceInfo函数返回的结构体
type InstanceDetail struct {
	BkBizId      int64       `json:"bk_biz_id"`
	ImmuteDomain string      `json:"immute_domain"`
	BindEntry    []BindEntry `json:"bind_entry"`
	InstanceRole string      `json:"instance_role"`
	SpiderRole   string      `json:"spider_role"`
	MachineType  string      `json:"machine_type"`
	Port         int64       `json:"port"`
	Ip           string      `json:"ip"`
	BkCloudId    int64       `json:"bk_cloud_id"`
	ClusterType  string      `json:"cluster_type"`
}

// BindEntry TODO
type BindEntry struct {
	Entry     string `json:"entry"`
	EntryType string `json:"entry_type"`
	EntryRole string `json:"entry_role"`
}

// String 打印CloneInstancePrivPara
func (m CloneInstancePrivPara) String() string {
	return m.Source.Address + "|||" + m.Target.Address
}

// NewUserGrants 授权语句列表
type NewUserGrants struct {
	mu   sync.RWMutex
	Data []UserGrant `json:"data"`
}
