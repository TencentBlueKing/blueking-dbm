package response

// PageResult 封装分页查询返回结果
type PageResult struct {
	Count  uint64      `json:"count"`
	Result interface{} `json:"result"`
}
