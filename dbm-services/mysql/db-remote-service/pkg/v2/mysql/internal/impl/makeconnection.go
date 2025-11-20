package impl

import (
	"context"
	"fmt"
	"net/url"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/jmoiron/sqlx"
)

func Prepare(addr, user, password, timezone, charset string, timeout int) (*sqlx.DB, *sqlx.Conn, int64, error) {
	db, err := makeConnection(
		addr, user, password,
		timezone, charset, timeout,
	)
	if err != nil {
		return nil, nil, 0, err
	}

	conn, err := db.Connx(context.Background())
	if err != nil {
		return nil, nil, 0, err
	}

	var connId int64
	err = conn.GetContext(context.Background(), &connId, `SELECT CONNECTION_ID()`)
	if err != nil {
		return nil, nil, 0, err
	}

	return db, conn, connId, nil
}

func makeConnection(addr, user, password, timezone, charset string, timeout int) (db *sqlx.DB, err error) {
	dsn := fmt.Sprintf(`%s:%s@tcp(%s)/?timeout=%ds`, user, password, addr, timeout)
	if timezone != "" {
		dsn = dsn + fmt.Sprintf("&time_zone=%s", url.QueryEscape(fmt.Sprintf(`%s`, timezone)))
	}
	if charset != "default" {
		dsn = dsn + fmt.Sprintf("&charset=%s", charset)
	}

	err = retry.Do(
		func() error {
			db, err = sqlx.Connect("mysql", dsn)
			if err != nil {
				return err
			}
			if charset == "default" {
				defer func() {
					_ = db.Close()
				}()
				var serverCharset string
				err := db.QueryRow(`SELECT @@character_set_server`).Scan(&serverCharset)
				if err != nil {
					return err
				}
				db, err = makeConnection(addr, user, password, timezone, serverCharset, timeout)
				if err != nil {
					return err
				}
			}
			return nil
		},
		retry.Attempts(3),
		retry.Delay(2*time.Second),
		retry.DelayType(retry.FixedDelay),
	)
	if err != nil {
		return nil, err
	}

	return db, nil
}
