package cc

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// BizSet is a the BizSet server
type BizSet struct {
	client *Client
	url    string
}

// NewBizSet returns a new BizSet server
func NewBizSet(client *Client) *BizSet {
	return &BizSet{
		client: client,
		url:    "/api/c/compapi/v2/cc",
	}
}

// Create handler
func (h *BizSet) Create(bizId int, setName string, setTemplateID int) (*BizCreateSetResponse, error) {
	param := &BizCreateSetParam{
		BkBizID: bizId,
	}
	param.Data.BkParentID = bizId
	param.Data.BkSetName = setName
	param.Data.SetTemplateID = setTemplateID

	resp, err := h.client.Do(http.MethodPost, fmt.Sprintf("%s/create_set", h.url), param)
	if err != nil {
		return nil, err
	}
	var result BizCreateSetResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}

// Delete handler
func (h *BizSet) Delete(bizId int, bizSetId int) error {
	param := &BizDeleteSetParam{
		BkBizID:    bizId,
		BkBizSetID: bizSetId,
	}

	resp, err := h.client.Do(http.MethodPost, fmt.Sprintf("%s/delete_set", h.url), param)
	if err != nil {
		return err
	}

	if resp.Code != 0 || !resp.Result {
		return fmt.Errorf("delete bkset failed: code: %v result: %v message: %s", resp.Code, resp.Result, resp.Message)
	}

	return nil
}
