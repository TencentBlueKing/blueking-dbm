package cc

import (
	"net/http"
)

// TransferHostModule is a the TransferHostModule server
type TransferHostModule struct {
	client *Client
	url    string
}

// NewTransferHostModule returns a new TransferHostModule server
func NewTransferHostModule(client *Client) *TransferHostModule {
	return &TransferHostModule{
		client: client,
		url:    "/api/c/compapi/v2/cc/transfer_host_module",
	}
}

// Transfer 同业务下转移主机业务模块, 支持转移到多个模块
func (h *TransferHostModule) Transfer(param *TransferHostModuleParam) error {
	_, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return err
	}
	return nil
}
