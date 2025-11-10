package backend

import (
	"crypto/tls"
	"encoding/json"
	"net/http"
)

type backendResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

var httpClient *http.Client

func init() {
	httpClient = &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
	}
	httpClient = http.DefaultClient
}
