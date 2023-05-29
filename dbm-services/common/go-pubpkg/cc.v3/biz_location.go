package cc

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// BizLocation is a the BizLocation server
type BizLocation struct {
	client *Client
	url    string
}

// NewBizLocation returns a new BizLocation server
func NewBizLocation(client *Client) *BizLocation {
	return &BizLocation{
		client: client,
		url:    "/api/c/compapi/v2/cc/get_biz_location",
	}
}

// Query 根据业务Id查询业务所在CC版本位置
func (h *BizLocation) Query(bizIDs []int) ([]BizLocationInfo, error) {
	param := &BizLocationParam{
		BKBizIds: bizIDs,
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, fmt.Errorf("do http request failed, err: %+v", err)
	}
	var result []BizLocationInfo
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, fmt.Errorf("json unmarshal failed, responseb body: %s, err: %+v", string(resp.Data), err)
	}
	return result, nil
}
