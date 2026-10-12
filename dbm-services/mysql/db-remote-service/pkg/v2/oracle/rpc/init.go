package rpc

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/gin-gonic/gin"
)

var serviceNameRe = regexp.MustCompile(`^[A-Za-z0-9_.$#-]+$`)

// OracleRPCRequest Oracle 只读查询请求
type OracleRPCRequest struct {
	Addresses      []string `form:"addresses" json:"addresses" binding:"required"`
	Cmds           []string `form:"cmds" json:"cmds" binding:"required"`
	ServiceName    string   `form:"service_name" json:"service_name" binding:"required"`
	Force          bool     `form:"force" json:"force"`
	ConnectTimeout int      `form:"connect_timeout" json:"connect_timeout"`
	QueryTimeout   int      `form:"query_timeout" json:"query_timeout"`
}

func (c *OracleRPCRequest) TrimSpace() {
	for idx, val := range c.Addresses {
		c.Addresses[idx] = strings.TrimSpace(val)
	}
	c.ServiceName = strings.TrimSpace(c.ServiceName)
}

type OracleCmdRPCResponse struct {
	Cmd          string          `json:"cmd"`
	Result       json.RawMessage `json:"table_data"`
	RowsAffected int64           `json:"rows_affected"`
	Error        string          `json:"error_msg"`
}

type OracleOneAddressRPCResponse struct {
	Address    string                 `json:"address"`
	CmdResults []OracleCmdRPCResponse `json:"cmd_results"`
	Error      string                 `json:"error_msg"`
}

func BuildRequestWithDefault(c *gin.Context) (*OracleRPCRequest, error) {
	r := &OracleRPCRequest{
		ConnectTimeout: 2,
		QueryTimeout:   600,
		Force:          false,
	}
	err := c.ShouldBindJSON(r)
	if err != nil {
		return nil, err
	}

	r.TrimSpace()
	if r.ConnectTimeout <= 0 {
		r.ConnectTimeout = 2
	}
	if r.QueryTimeout <= 0 {
		r.QueryTimeout = 600
	}
	if !serviceNameRe.MatchString(r.ServiceName) {
		return nil, fmt.Errorf("invalid service_name: %s", r.ServiceName)
	}

	return r, nil
}
