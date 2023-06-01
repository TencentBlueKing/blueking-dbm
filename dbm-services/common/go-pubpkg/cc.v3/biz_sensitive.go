package cc

import (
	"encoding/json"
	"net/http"
	"reflect"

	"dbm-services/common/go-pubpkg/cc.v3/utils"
)

// BizSensitiveList is a the BizSensitiveList server
type BizSensitiveList struct {
	client *Client
	url    string
	fields []string
}

// NewBizSensitiveList returns a new BizSensitiveList server
func NewBizSensitiveList(client *Client) *BizSensitiveList {
	fields := utils.GetStructTagName(reflect.TypeOf(&BizSensitive{}))
	return &BizSensitiveList{
		client: client,
		url:    "/api/c/compapi/v2/cc/find_biz_sensitive_batch",
		fields: fields,
	}
}

// Query handler
func (h *BizSensitiveList) Query(bizIds []int, page BKPage) (*BizSensitiveResponse, error) {
	param := &BizSensitiveParam{
		Fields:   h.fields,
		Page:     page,
		BkBizIds: bizIds,
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result BizSensitiveResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
