package core

import "encoding/json"

type Core struct {
	bkCloudId  int64
	nginxAddrs []string
}

func NewCore(bkCloudId int64, nginxAddrs ...string) *Core {
	return &Core{
		bkCloudId:  bkCloudId,
		nginxAddrs: nginxAddrs,
	}
}

type apiResponse struct {
	Result  bool            `json:"result"`
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Errors  string          `json:"errors"`
	Data    json.RawMessage `json:"data"`
}
