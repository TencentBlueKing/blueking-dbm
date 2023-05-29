package cc

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// BizTopoTree is a the BizTopoTree server
type BizTopoTree struct {
	client *Client
	url    string
}

// NewBizTopoTree returns a new BizTopoTree server
func NewBizTopoTree(client *Client) *BizTopoTree {
	return &BizTopoTree{
		client: client,
		url:    "/api/c/compapi/v2/cc/search_biz_inst_topo/",
	}
}

// Query 根据业务ID查询业务信息
func (h *BizTopoTree) Query(bizID int) ([]TopoTreeNode, error) {
	param := &BizTopoTreeParam{
		BKBizId: bizID,
	}
	resp, err := h.client.Do(http.MethodGet, h.url, param)
	if err != nil {
		return nil, fmt.Errorf("do http request failed, err: %+v", err)
	}
	var result []TopoTreeNode
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, fmt.Errorf("json unmarshal failed, responseb body: %s, err: %+v", string(resp.Data), err)
	}
	return result, nil
}
