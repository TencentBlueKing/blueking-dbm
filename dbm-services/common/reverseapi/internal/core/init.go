package core

import (
	"encoding/json"
	"net/http"
)

const reverseApiBase = "apis/proxypass/reverse_api"

type apiResponse struct {
	Result  bool            `json:"result"`
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Errors  json.RawMessage `json:"errors"`
	Data    json.RawMessage `json:"data"`
}

type Core struct {
	bkCloudId  int64
	nginxAddrs []string
	ip         string
	debug      bool
	client     *http.Client
}

func NewCore(bkCloudId int64, addrs ...string) *Core {
	return &Core{
		bkCloudId:  bkCloudId,
		nginxAddrs: addrs,
		debug:      false,
		client: &http.Client{
			Transport: &http.Transport{
				MaxIdleConnsPerHost: 2,
				MaxIdleConns:        2,
				MaxConnsPerHost:     5,
			},
		},
	}
}

func NewDebugCore(bkCloudId int64, ip string, addrs ...string) *Core {
	return &Core{
		bkCloudId:  bkCloudId,
		nginxAddrs: addrs,
		debug:      true,
		ip:         ip,
		client: &http.Client{
			Transport: &http.Transport{
				MaxIdleConnsPerHost: 5,
				MaxIdleConns:        5,
				MaxConnsPerHost:     100,
			},
		},
	}
}
