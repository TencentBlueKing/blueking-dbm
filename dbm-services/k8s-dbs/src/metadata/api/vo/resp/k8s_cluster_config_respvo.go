package resp

import "time"

type K8sClusterConfigRespVo struct {
	Id           uint64    `json:"id"`
	ClusterName  string    `json:"cluster_name"`
	APIServerURL string    `json:"api_server_url"`
	CACert       string    `json:"ca_cert"`
	ClientCert   string    `json:"client_cert"`
	ClientKey    string    `json:"client_key"`
	Token        string    `json:"token"`
	Username     string    `json:"username"`
	Password     string    `json:"password"`
	Active       bool      `json:"active"`
	Description  string    `json:"description"`
	CreatedBy    string    `json:"created_by"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedBy    string    `json:"updated_by"`
	UpdatedAt    time.Time `json:"updated_at"`
}
