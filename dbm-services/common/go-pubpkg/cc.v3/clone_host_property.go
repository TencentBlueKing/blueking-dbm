package cc

import (
	"net/http"
)

// HostProperty 主机属性
type HostProperty struct {
	client *Client
	url    string
}

// NewHostProperty TODO
func NewHostProperty(client *Client) *HostProperty {
	return &HostProperty{
		client: client,
		url:    "/api/c/compapi/v2/cc/clone_host_property",
	}
}

// Clone 克隆主机属性
func (h *HostProperty) Clone(param *CloneHostPropertyParam) error {
	// 获取所有的HostId
	_, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return err
	}
	return nil
}
