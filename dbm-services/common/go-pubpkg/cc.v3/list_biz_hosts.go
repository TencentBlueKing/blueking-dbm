package cc

import (
	"encoding/json"
	"net/http"
)

// 功能描述
// 根据业务ID查询业务下的主机，可附带其他的过滤信息，如集群id,模块id等

// ListBizHosts TODO
type ListBizHosts struct {
	client *Client
	url    string
}

// NewListBizHosts returns a new ListBizHosts server
func NewListBizHosts(client *Client) *ListBizHosts {
	return &ListBizHosts{
		client: client,
		url:    "/api/c/compapi/v2/cc/list_biz_hosts/",
	}
}

// QueryListBizHosts 查询业务下的主机
func (h *ListBizHosts) QueryListBizHosts(param *ListBizHostsParam) (*ListBizHostsResponse, *Response, error) {
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, resp, err
	}
	var result ListBizHostsResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, resp, err
	}
	return &result, resp, nil
}
