package websocket

import "encoding/json"

type WSBaseRequest struct {
	RequestType string          `json:"request-type"`
	Body        json.RawMessage `json:"body"`
}

type WSConnectRequest struct {
	Address  string `json:"address"`
	Charset  string `json:"charset"`
	Timezone string `json:"timezone"`
	Timeout  int    `json:"timeout"`
}

type WSCommandRequest struct {
	Command string `json:"command"`
	Timeout int    `json:"timeout"`
}

type WSResponse struct {
	//Data         json.RawMessage `json:"data"`
	Result       json.RawMessage `json:"result"`
	RowsAffected int64           `json:"rows_affected"`
	Error        string          `json:"error"`
}

func (c WSResponse) Bytes() []byte {
	b, _ := json.Marshal(c)
	return b
}
