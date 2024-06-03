// Package parser sql解析
package parser

// ParseQueryBase query result base field
type ParseQueryBase struct {
	QueryId   int    `json:"query_id"`
	Command   string `json:"command"`
	ErrorCode int    `json:"error_code"`
	ErrorMsg  string `json:"error_msg"`
}
