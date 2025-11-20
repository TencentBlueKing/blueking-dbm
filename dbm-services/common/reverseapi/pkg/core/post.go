package core

import (
	"encoding/json"
	"net/http"
)

func (c *Core) Post(api string, payLoad json.RawMessage, ports ...int) (data []byte, err error) {
	return c.do(http.MethodPost, api, payLoad, ports...)
}
