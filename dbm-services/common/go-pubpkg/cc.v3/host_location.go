package cc

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// HostLocation 业务CC版本位置
type HostLocation struct {
	client *Client
	url    string
}

// NewHostLocation returns a new HostLocation server
func NewHostLocation(client *Client) *HostLocation {
	return &HostLocation{
		client: client,
		url:    "/api/c/compapi/v2/cc/get_host_location",
	}
}

// Query 根据Host查询业务所在CC版本位置
func (h *HostLocation) Query(host []string) ([]HostLocationInfo, error) {
	list := make([]BkHostList, len(host))
	for i := 0; i < len(host); i++ {
		list[i].BkCloudID = 0
		list[i].BkHostInnerip = host[i]
	}
	param := HostLocationParam{
		BkHostList: list,
	}

	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, fmt.Errorf("do http request failed, err: %s", err.Error())
	}
	var result []HostLocationInfo
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, fmt.Errorf("json unmarshal failed, responseb body: %s, err: %+v", string(resp.Data), err)
	}
	return result, nil
}
