package response

// PageResult 封装分页查询返回结果
type PageResult struct {
	Count  uint64      `json:"count"`
	Result interface{} `json:"result"`
}

// RowsAffectedResponse 封装更新/删除操作影响的行数响应
type RowsAffectedResponse struct {
	RowsAffected uint64 `json:"rowsAffected"`
}
