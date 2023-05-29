package cc

import (
	"encoding/json"
	"net/http"
	"reflect"

	"dbm-services/common/go-pubpkg/cc.v3/utils"
)

// BizModuleList is a the BizModuleList server
type BizModuleList struct {
	client *Client
	url    string
	fields []string
}

// NewBizModuleList returns a new BizModuleList server
func NewBizModuleList(client *Client) *BizModuleList {
	fields := utils.GetStructTagName(reflect.TypeOf(&Module{}))
	return &BizModuleList{
		client: client,
		url:    "/api/c/compapi/v2/cc/search_module",
		fields: fields,
	}
}

// Query handler
func (h *BizModuleList) Query(bizId int, setId int, page BKPage) (*BizModuleResponse, error) {
	param := &BizModuleParam{
		BKBizId: bizId,
		BKSetId: setId,
		Fields:  h.fields,
		Page:    page,
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result BizModuleResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
