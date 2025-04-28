package mysql

// Request TODO
type Request struct {
	Content string `json:"content" binding:"required"`
	// Db which database context the sql is running in, can be empty
	Db string `json:"db"`
}
