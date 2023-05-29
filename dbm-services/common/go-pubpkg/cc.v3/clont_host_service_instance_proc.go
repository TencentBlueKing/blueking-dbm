package cc

import (
	"net/http"
)

// HostServiceInstance 主机属性
type HostServiceInstance struct {
	client *Client
	url    string
}

// NewHostServiceInstance TODO
func NewHostServiceInstance(client *Client) *HostServiceInstance {
	return &HostServiceInstance{
		client: client,
		url:    "/api/c/compapi/v2/cc/clone_host_service_instance_proc",
	}
}

// Clone 克隆实例信息
func (h *HostServiceInstance) Clone(param *CloneHostSvcInsParam) error {
	// 获取所有的HostId
	_, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return err
	}
	return nil
}
