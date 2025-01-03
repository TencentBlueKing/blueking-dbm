package internal

import "encoding/json"

type apiResponse struct {
	Result  bool            `json:"result"`
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Errors  string          `json:"errors"`
	Data    json.RawMessage `json:"data"`
}
