package rpc

import (
	"encoding/json"
	"strings"

	"github.com/gin-gonic/gin"
)

type MySQLRPCRequest struct {
	Addresses      []string `form:"addresses" json:"addresses" binding:"required"`
	Cmds           []string `form:"cmds" json:"cmds" binding:"required"`
	Force          bool     `form:"force" json:"force"`
	ConnectTimeout int      `form:"connect_timeout" json:"connect_timeout"`
	QueryTimeout   int      `form:"query_timeout" json:"query_timeout"`
	Timezone       string   `form:"timezone" json:"timezone"`
	Charset        string   `form:"charset" json:"charset"`
	TraceId        string   `form:"trace_id" json:"trace_id"`
}

func (c *MySQLRPCRequest) TrimSpace() {
	c.Timezone = strings.TrimSpace(c.Timezone)
	for idx, val := range c.Addresses {
		c.Addresses[idx] = strings.TrimSpace(val)
	}
}

type MySQLRPCResponse struct {
	Cmd          string
	Result       json.RawMessage //[]byte //impl.SQLResultRows
	RowsAffected int64
	Error        string
}

func BuildRequestWithDefault(c *gin.Context) (*MySQLRPCRequest, error) {
	r := &MySQLRPCRequest{
		ConnectTimeout: 2,
		QueryTimeout:   600,
		Force:          false,
		Timezone:       "",
		Charset:        "",
	}
	err := c.ShouldBindJSON(r)
	if err != nil {
		return nil, err
	}

	r.TrimSpace()
	if r.QueryTimeout <= 0 {
		r.QueryTimeout = 600
	}
	if r.Charset == "" {
		r.Charset = "default"
	}

	return r, nil
}
