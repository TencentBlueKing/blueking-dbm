package crond

// NotFoundError TODO
type NotFoundError string

// Error 用于错误处理
func (r NotFoundError) Error() string {
	return string(r)
}
