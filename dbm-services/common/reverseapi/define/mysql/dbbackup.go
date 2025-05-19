package mysql

import "encoding/json"

type DBBackupConfig struct {
	ConfigsTemplate map[string]map[string]string `json:"configs"`
	Options         json.RawMessage              `json:"options"`
	Ip              string                       `json:"ip"`
	Port            int                          `json:"port"`
	Role            string                       `json:"role"`
	ClusterType     string                       `json:"cluster_type"`
	ImmuteDomain    string                       `json:"immute_domain"`
	ClusterId       int                          `json:"cluster_id"`
	ShardId         int                          `json:"shard_id"`
	User            string                       `json:"user"`
	Password        string                       `json:"password"`
	BkBizId         int                          `json:"bk_biz_id"`
	BkCloudId       int                          `json:"bk_cloud_id"`
}
