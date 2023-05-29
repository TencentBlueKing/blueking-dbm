package handler_rpc

import "strings"

type queryRequest struct {
	Addresses      []string `form:"addresses" json:"addresses" binding:"required"`
	Cmds           []string `form:"cmds" json:"cmds" binding:"required"`
	Force          bool     `form:"force" json:"force"`
	ConnectTimeout int      `form:"connect_timeout" json:"connect_timeout"`
	QueryTimeout   int      `form:"query_timeout" json:"query_timeout"`
}

// TrimSpace delete space around address
func (r *queryRequest) TrimSpace() {
	for idx, val := range r.Addresses {
		r.Addresses[idx] = strings.TrimSpace(val)
	}
}
