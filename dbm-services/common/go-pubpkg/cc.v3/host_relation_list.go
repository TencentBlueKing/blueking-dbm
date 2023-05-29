package cc

import (
	"dbm-services/common/go-pubpkg/cc.v3/utils"
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
)

// HostRelationList 主机关联信息查询
type HostRelationList struct {
	client     *Client
	url        string
	hostFields []string
}

// NewHostRelationList returns a new HostRelationList server
func NewHostRelationList(client *Client) *HostRelationList {
	hostFields := utils.GetStructTagName(reflect.TypeOf(&Host{}))
	return &HostRelationList{
		client:     client,
		url:        "/api/c/compapi/v2/cc/list_host_related_info",
		hostFields: hostFields,
	}
}

// Query handler
func (h *HostRelationList) Query(data *HostMetaData, page BKPage) (*ListHostRelationResponse, error) {
	param := &ListHostRelationParam{
		BKHostFields:   h.hostFields,
		BKBizFields:    []string{"bk_biz_id", "bk_biz_name"},
		BKSetFields:    []string{"bk_set_id", "bk_set_name"},
		BKModuleFields: []string{"bk_module_id", "bk_module_name"},
		Page:           page,
	}
	if data != nil {
		hostIds, err := QueryHostId(h.client, data.InnerIPs, data.AssetIds)
		if err != nil {
			return nil, fmt.Errorf("Query BKHostId from innerip or assetid failed: %v", err)
		}
		hostIds = append(hostIds, data.BKHostIds...)
		if len(hostIds) > 0 {
			param.BKHostIds = RemoveRepeatedHostId(hostIds)
		}
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result ListHostRelationResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
