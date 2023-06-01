package cc

import (
	"encoding/json"
	"net/http"
	"reflect"

	"dbm-services/common/go-pubpkg/cc.v3/utils"
)

// BizList is a the BizList server
type BizList struct {
	client *Client
	url    string
	fields []string
}

// NewBizList returns a new BizList server
func NewBizList(client *Client) *BizList {
	fields := utils.GetStructTagName(reflect.TypeOf(&Biz{}))
	return &BizList{
		client: client,
		url:    "/api/c/compapi/v2/cc/search_business",
		fields: fields,
	}
}

// Query handler
func (h *BizList) Query(condition map[string]interface{}, fields []string, page BKPage) (*BizResponse, error) {
	param := &BizParam{
		Fields:    fields,
		Page:      page,
		Condition: condition,
	}
	if len(fields) == 0 {
		param.Fields = h.fields
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result BizResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
