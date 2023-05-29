package cc

import (
	"encoding/json"
	"net/http"
)

// DeptList is a the DeptList server
type DeptList struct {
	client *Client
	url    string
}

// NewDeptList returns a new DeptList server
func NewDeptList(client *Client) *DeptList {
	return &DeptList{
		client: client,
		url:    "/component/compapi/tof/get_dept_info",
	}
}

// Query handler
func (h *DeptList) Query(deptId string) (*DeptResponse, error) {
	param := &DeptParam{
		DeptId: deptId,
	}
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, err
	}
	var result DeptResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, err
	}
	return &result, nil
}
