package service

import (
	"strings"
	"sync"
)

// CloneClientPrivParaList CloneClientPrivDryRun函数的入参
type CloneClientPrivParaList struct {
	BkBizId                int64                 `json:"bk_biz_id"`
	CloneClientPrivRecords []CloneClientPrivPara `json:"clone_client_priv_records"`
}

// CloneClientPrivPara CloneClientPriv函数的入参
type CloneClientPrivPara struct {
	BkBizId     int64    `json:"bk_biz_id"`
	Operator    string   `json:"operator"`
	SourceIp    string   `json:"source_ip"`
	TargetIp    []string `json:"target_ip"`
	BkCloudId   *int64   `json:"bk_cloud_id"`
	ClusterType *string  `json:"cluster_type"`
}

// String 打印CloneClientPrivPara
func (m CloneClientPrivPara) String() string {
	return m.SourceIp + "|||" + strings.Join(m.TargetIp, "|||")
}

// UserGrant 授权账号user@host、授权语句
type UserGrant struct {
	UserHost string   `json:"user_host"`
	Grants   []string `json:"grants"`
}

// Err 错误信息列表
type Err struct {
	mu   sync.RWMutex
	errs []string
}
