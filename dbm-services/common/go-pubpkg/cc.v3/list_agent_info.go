package cc

import (
	"encoding/json"
	"net/http"
)

// ListAgentState TODO
type ListAgentState struct {
	client *Client
	Url    string
}

// NewListAgentState TODO
// NewListBizHosts returns a new ListBizHosts server
func NewListAgentState(client *Client) *ListAgentState {
	return &ListAgentState{
		client: client,
		Url:    "/api/v2/cluster/list_agent_info",
	}
}

// ListAgentInfoParam TODO
type ListAgentInfoParam struct {
	BaseSecret `json:",inline"`
	// 最大支持1000个ID的查询
	AgentIdList []string `json:"agent_id_list"`
}

// ListAgentInfoRespone TODO
type ListAgentInfoRespone struct {
	BkAgentId  string `json:"bk_agent_id"`
	BkCloudID  int    `json:"bk_cloud_id"`
	BkHostIp   string `json:"bk_host_ip"`
	Version    string `json:"version"`
	RunMode    int    `json:"run_mode"`
	StatusCode int    `json:"status_code"`
}

// QueryListAgentInfo 查询主机gseAgent转态
func (h *ListAgentState) QueryListAgentInfo(param *ListAgentInfoParam) ([]ListAgentInfoRespone, *Response, error) {
	resp, err := h.client.Do(http.MethodPost, h.Url, param)
	if err != nil {
		return nil, resp, err
	}
	var result []ListAgentInfoRespone
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, resp, err
	}
	return result, resp, nil
}
