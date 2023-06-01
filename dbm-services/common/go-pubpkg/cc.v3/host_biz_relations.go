package cc

import (
	"encoding/json"
	"net/http"
	"reflect"

	"dbm-services/common/go-pubpkg/cc.v3/utils"
)

// HostBizRelation is a the HostBizRelation server
type HostBizRelation struct {
	client     *Client
	url        string
	hostFields []string
}

// NewHostBizRelation returns a new HostBizRelation server
func NewHostBizRelation(client *Client) *HostBizRelation {
	hostFields := utils.GetStructTagName(reflect.TypeOf(&Host{}))
	return &HostBizRelation{
		client:     client,
		url:        "/api/c/compapi/v2/cc/find_host_biz_relations/",
		hostFields: hostFields,
	}
}

// Query handler
func (h *HostBizRelation) Query(hostIds []int, page BKPage) ([]FindHostBizRelationResp, error) {
	param := &FindHostBizRelationParam{
		BKHostFields:   h.hostFields,
		BKBizFields:    []string{"bk_biz_id", "bk_biz_name"},
		BKSetFields:    []string{"bk_set_id", "bk_set_name"},
		BKModuleFields: []string{"bk_module_id", "bk_module_name"},
		Page:           page,
	}
	if len(hostIds) > 0 {
		param.BKHostIds = hostIds
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	result := make([]FindHostBizRelationResp, 0)
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return result, nil
}
