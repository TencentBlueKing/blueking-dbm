package rpc

import (
	"encoding/json"
	"strings"

	"dbm-services/mysql/db-remote-service/pkg/v2/sqlserver/internal/impl"

	"github.com/gin-gonic/gin"
)

type SqlserverRPCRequest struct {
	Addresses      []string `form:"addresses" json:"addresses" binding:"required"`
	Cmds           []string `form:"cmds" json:"cmds" binding:"required"`
	Force          bool     `form:"force" json:"force"`
	ConnectTimeout int      `form:"connect_timeout" json:"connect_timeout"`
	QueryTimeout   int      `form:"query_timeout" json:"query_timeout"`

	classifier *impl.CommandClassifier
}

func (c *SqlserverRPCRequest) TrimSpace() {
	for idx, val := range c.Addresses {
		c.Addresses[idx] = strings.TrimSpace(val)
	}
}

type SqlserverCmdRPCResponse struct {
	Cmd          string          `json:"cmd"`
	Result       json.RawMessage `json:"table_data"`
	RowsAffected int64           `json:"rows_affected"`
	Error        string          `json:"error_msg"`
}

type SqlserverOneAddressRPCResponse struct {
	Address    string                    `json:"address"`
	CmdResults []SqlserverCmdRPCResponse `json:"cmd_results"`
	Error      string                    `json:"error_msg"`
}

func BuildRequestWithDefault(c *gin.Context, classifier *impl.CommandClassifier) (*SqlserverRPCRequest, error) {
	r := &SqlserverRPCRequest{
		ConnectTimeout: 2,
		QueryTimeout:   600,
		Force:          false,
		classifier:     classifier,
	}
	err := c.ShouldBindJSON(r)
	if err != nil {
		return nil, err
	}

	r.TrimSpace()
	if r.QueryTimeout <= 0 {
		r.QueryTimeout = 600
	}

	return r, nil
}
