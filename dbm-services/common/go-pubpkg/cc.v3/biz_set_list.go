package cc

import (
	"encoding/json"
	"net/http"
	"reflect"

	"dbm-services/common/go-pubpkg/cc.v3/utils"
)

// BizSetList is a the BizSetList server
type BizSetList struct {
	client *Client
	url    string
	fields []string
}

// NewBizSetList returns a new BizSetList server
func NewBizSetList(client *Client) *BizSetList {
	fields := utils.GetStructTagName(reflect.TypeOf(&Set{}))
	return &BizSetList{
		client: client,
		url:    "/api/c/compapi/v2/cc/search_set",
		fields: fields,
	}
}

// Query handler
func (h *BizSetList) Query(bizId int, page BKPage) (*BizSetResponse, error) {
	param := &BizSetParam{
		BKBizId: bizId,
		Fields:  h.fields,
		Page:    page,
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result BizSetResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
