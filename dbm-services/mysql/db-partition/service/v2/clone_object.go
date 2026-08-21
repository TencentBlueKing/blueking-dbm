package v2

// CloneEndpoint 克隆源端或目标端
type CloneEndpoint struct {
	ImmuteDomain string   `json:"immute_domain"`
	Dblikes      []string `json:"dblikes"`
	Tblikes      []string `json:"tblikes"`
	ClusterId    int      `json:"cluster_id"`
	Port         int      `json:"port"`
	BkCloudId    int      `json:"bk_cloud_id"`
	BkBizId      int64    `json:"bk_biz_id"`
	DbAppAbbr    string   `json:"db_app_abbr"`
	BkBizName    string   `json:"bk_biz_name"`
}

// CloneConfPair 一对源集群 → 目标集群
type CloneConfPair struct {
	Source CloneEndpoint `json:"source"`
	Target CloneEndpoint `json:"target"`
}

// CloneConfInput POST /partition/v2/clone_conf 入参
type CloneConfInput struct {
	ClusterType string          `json:"cluster_type"`
	Operator    string          `json:"operator"`
	Infos       []CloneConfPair `json:"infos"`
}

// CloneConfOutput 不回传完整配置，只给成功条数和失败原因
type CloneConfOutput struct {
	SuccessCount int      `json:"success_count"`
	Errors       []string `json:"errors"`
	Info         string   `json:"info"`
}
