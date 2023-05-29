package cc

import (
	"net/http"
)

// BizModule TODO
type BizModule struct {
	client *Client
	url    string
}

// NewBizModule List returns a new BizModuleList server
func NewBizModule(client *Client) *BizModule {
	return &BizModule{
		client: client,
		url:    "/api/c/compapi/v2/cc/create_module/",
	}
}

// Create TODO
func (h *BizModule) Create(param CreateModuleParam) (err error) {
	_, err = h.client.Do(http.MethodPost, h.url, param)
	return
}
