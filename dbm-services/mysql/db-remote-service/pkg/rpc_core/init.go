package rpc_core

type tableDataType []map[string]interface{}

type cmdResult struct {
	Cmd          string        `json:"cmd"`
	TableData    tableDataType `json:"table_data"`
	RowsAffected int64         `json:"rows_affected"`
	ErrorMsg     string        `json:"error_msg"`
}

type oneAddressResult struct {
	Address    string      `json:"address"`
	CmdResults []cmdResult `json:"cmd_results"`
	ErrorMsg   string      `json:"error_msg"`
}
