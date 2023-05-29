package cc

import (
	"encoding/json"
	"net/http"
)

// BizInternalModule is a the BizInternalModule server
type BizInternalModule struct {
	client *Client
	url    string
}

// NewBizInternalModule returns a new BizInternalModule server
func NewBizInternalModule(client *Client) *BizInternalModule {
	return &BizInternalModule{
		client: client,
		url:    "/api/c/compapi/v2/cc/get_biz_internal_module/",
	}
}

// Query 根据业务ID查询业务的内置模块
func (h *BizInternalModule) Query(bizID int) (*BizInternalModuleResponse, error) {
	param := &BizInternalModulesParam{
		BKBizId: bizID,
	}
	resp, err := h.client.Do(http.MethodGet, h.url, param)
	if err != nil {
		return nil, err
	}
	var result BizInternalModuleResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
