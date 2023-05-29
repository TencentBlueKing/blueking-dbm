package cc

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"
)

// UpdateHost is a the UpdateHost server
type UpdateHost struct {
	client *Client
	url    string
}

// NewUpdateHost returns a new UpdateHost server
func NewUpdateHost(client *Client) *UpdateHost {
	return &UpdateHost{
		client: client,
		url:    "/api/c/compapi/v2/cc/update_host",
	}
}

// Update 更新主机属性
func (h *UpdateHost) Update(param *UpdateHostParam) error {
	// 获取所有的HostId
	hostIds, err := QueryHostId(h.client, param.InnerIPs, param.AssetIds)
	if err != nil {
		return fmt.Errorf("Query BKHostId from innerip or assetid failed: %v", err)
	}
	for _, item := range strings.Split(param.BKHostId, ",") {
		if item == "" {
			continue
		}
		id, _ := strconv.Atoi(item)
		hostIds = append(hostIds, id)
	}
	// 把数组转成字符串，按逗号隔开
	param.BKHostId = strings.Replace(strings.Trim(fmt.Sprint(RemoveRepeatedHostId(hostIds)), "[]"), " ", ",", -1)
	_, err = h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return err
	}
	return nil
}
