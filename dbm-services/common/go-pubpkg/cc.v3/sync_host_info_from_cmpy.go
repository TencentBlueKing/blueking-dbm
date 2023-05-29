package cc

import (
	"net/http"
)

// SyncHostInfoFromCmpy sync host from cmdb
type SyncHostInfoFromCmpy struct {
	client *Client
	url    string
}

// NewSyncHostInfoFromCmpy returns a new SyncHostInfoFromCmpy
func NewSyncHostInfoFromCmpy(client *Client) *SyncHostInfoFromCmpy {
	return &SyncHostInfoFromCmpy{
		client: client,
		url:    "/api/c/compapi/v2/cc/sync_host_info_from_cmpy/",
	}
}

// Query 同步更新主机信息到cc
func (s *SyncHostInfoFromCmpy) Query(bizHostIds []int) (*Response, error) {
	param := &SyncHostInfoFromCmpyParam{
		BkHostIds: bizHostIds,
	}
	return s.client.Do(http.MethodPost, s.url, param)
}
