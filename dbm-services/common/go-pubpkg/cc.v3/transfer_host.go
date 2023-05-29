package cc

import (
	"fmt"
	"net/http"
)

// TransferHost is a the TransferHost server
type TransferHost struct {
	client *Client
	url    string
}

// NewTransferHost returns a new TransferHost server
func NewTransferHost(client *Client) *TransferHost {
	return &TransferHost{
		client: client,
		url:    "/api/c/compapi/v2/cc/transfer_host_to_another_biz",
	}
}

// Transfer 转移主机业务模块
func (h *TransferHost) Transfer(param *TransferHostParam) error {
	// 获取所有的HostId
	hostIds, err := QueryHostId(h.client, param.From.InnerIPs, param.From.AssetIds)
	if err != nil {
		return fmt.Errorf("Query BKHostId from innerip or assetid failed: %v", err)
	}
	hostIds = append(hostIds, param.From.BKHostIds...)
	param.From.BKHostIds = RemoveRepeatedHostId(hostIds)
	_, err = h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return err
	}
	return nil
}
