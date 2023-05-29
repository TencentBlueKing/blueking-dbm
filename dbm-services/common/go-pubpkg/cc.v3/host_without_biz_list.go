package cc

import (
	"encoding/json"
	"net/http"
)

// HostWithoutBizList is a the HostWithoutBizList server
type HostWithoutBizList struct {
	client *Client
	url    string
}

// NewHostWithoutBizList returns a new HostWithoutBizList server
func NewHostWithoutBizList(client *Client) *HostWithoutBizList {
	return &HostWithoutBizList{
		client: client,
		url:    "/api/c/compapi/v2/cc/list_hosts_without_biz",
	}
}

// QueryWithFilter 根据内网IP查询主机ID信息
func (h *HostWithoutBizList) QueryWithFilter(filter HostPropertyFilter, page BKPage) (*HostsWithoutBizListResponse,
	error) {
	param := &HostsWithoutBizListParam{
		HostPropertyFilter: filter,
		Page:               page,
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result HostsWithoutBizListResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
