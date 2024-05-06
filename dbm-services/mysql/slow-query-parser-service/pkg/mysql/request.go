package mysql

// Request TODO
type Request struct {
	Content string `json:"content" binding:"required"`
}
