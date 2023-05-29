package cc

import (
	"net/http"
)

// AddHostInfoFromCmpy TODO
type AddHostInfoFromCmpy struct {
	client *Client
	url    string
}

// NewAddHostInfoFromCmpy returns a new AddHostInfoFromCmpy
func NewAddHostInfoFromCmpy(client *Client) *AddHostInfoFromCmpy {
	return &AddHostInfoFromCmpy{
		client: client,
		url:    "/api/c/compapi/v2/cc/add_host_from_cmpy/",
	}
}

// Query 同步新增主机信息到cc
func (s *AddHostInfoFromCmpy) Query(svrIds []int) (*Response, error) {
	param := &AddHostInfoFromCmpyParam{
		SvrIds: svrIds,
	}
	return s.client.Do(http.MethodPost, s.url, param)
}
