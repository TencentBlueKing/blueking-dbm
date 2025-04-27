package utils

type Pagination struct {
	Page  int `json:"page"`  // 当前页码
	Limit int `json:"limit"` // 每页记录数
}
