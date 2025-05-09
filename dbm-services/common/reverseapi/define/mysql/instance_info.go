package mysql

const (
	AccessLayerStorage string = "storage"
	AccessLayerProxy   string = "proxy"
)

type InstanceAddr struct {
	Ip   string `json:"ip"`
	Port int    `json:"port"`
}

type CommonInstanceInfo struct {
	InstanceAddr
	ImmuteDomain string `json:"immute_domain"`
	Phase        string `json:"phase"`
	Status       string `json:"status"`
	AccessLayer  string `json:"access_layer"`
	MachineType  string `json:"machine_type"`
	BkInstanceId int64  `json:"bk_instance_id"`
	BkBizId      int    `json:"bk_biz_id"`
	BkCloudId    int    `json:"bk_cloud_id"`
	ClusterType  string `json:"cluster_type"`
}

type StorageInstanceInfo struct {
	CommonInstanceInfo
	IsStandBy         bool           `json:"is_stand_by"`
	InstanceRole      string         `json:"instance_role"`
	InstanceInnerRole string         `json:"instance_inner_role"`
	Receivers         []InstanceAddr `json:"receivers"`
	Ejectors          []InstanceAddr `json:"ejectors"`
}

type ProxyInstanceInfo struct {
	CommonInstanceInfo
	StorageInstanceList []InstanceAddr `json:"storage_instance_list"`
}
