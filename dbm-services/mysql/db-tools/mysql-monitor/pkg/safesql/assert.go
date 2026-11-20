package safesql

import (
	"database/sql"

	"github.com/jmoiron/sqlx"
)

// 编译期断言: 两种 DB 都满足对应的池接口
var (
	_ Pool    = (*sqlx.DB)(nil)
	_ StdPool = (*sql.DB)(nil)
	// *sqlx.DB 内嵌 *sql.DB, 因此同时满足 StdPool
	_ StdPool = (*sqlx.DB)(nil)
)

// 编译期断言: 两种独占连接都满足 Conn / connCloser
var (
	_ connCloser = (*sql.Conn)(nil)
	_ connCloser = (*sqlx.Conn)(nil)
)
