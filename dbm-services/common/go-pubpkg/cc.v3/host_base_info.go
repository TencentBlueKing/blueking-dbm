package cc

import (
	"encoding/json"
	"net/http"
)

// HostBaseInfo TODO
type HostBaseInfo struct {
	client *Client
	url    string
}

// NewHostBaseInfo TODO
// NewHostBizRelation returns a new HostBizRelation server
func NewHostBaseInfo(client *Client) *HostBaseInfo {
	return &HostBaseInfo{
		client: client,
		url:    "/api/c/compapi/v2/cc/get_host_base_info/",
	}
}

// Query handler
func (h *HostBaseInfo) Query(hostId int) ([]HostPropertyInfo, error) {
	param := &GetHostBaseInfoParam{
		BkHostID: hostId,
	}
	resp, err := h.client.Do(http.MethodGet, h.url, param)
	if err != nil {
		return nil, err
	}
	var result []HostPropertyInfo
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return result, nil
}
