package core

import (
	"net/http"
)

func (c *Core) Get(api string, ports ...int) (data []byte, err error) {
	return c.do(http.MethodGet, api, nil, ports...)
}
