package pkg

import (
	"context"
	"time"

	"github.com/jmoiron/sqlx"
)

func IsTableExistsIn(conn *sqlx.Conn, tableName, dbName string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var cnt int
	err := conn.QueryRowxContext(
		ctx,
		`SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                	WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND TABLE_TYPE = 'BASE TABLE'`,
		dbName, tableName,
	).Scan(&cnt)
	if err != nil {
		return false, err
	}

	return cnt > 0, nil
}

func IsTriggerExistsIn(conn *sqlx.Conn, triggerName, dbName string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var cnt int
	err := conn.QueryRowxContext(
		ctx,
		`SELECT COUNT(*) FROM INFORMATION_SCHEMA.TRIGGERS 
                	WHERE TRIGGER_SCHEMA = ? AND TRIGGER_NAME = ?`,
		dbName, triggerName,
	).Scan(&cnt)
	if err != nil {
		return false, err
	}

	return cnt > 0, nil
}

func IsEventExistsIn(conn *sqlx.Conn, eventName, dbName string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var cnt int
	err := conn.QueryRowxContext(
		ctx,
		`SELECT COUNT(*) FROM INFORMATION_SCHEMA.EVENTS 
                	WHERE EVENT_SCHEMA = ? AND EVENT_NAME = ?`,
		dbName, eventName,
	).Scan(&cnt)
	if err != nil {
		return false, err
	}

	return cnt > 0, nil
}

func IsRoutineExistsIn(conn *sqlx.Conn, routineName, dbName string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var cnt int
	err := conn.QueryRowxContext(
		ctx,
		`SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES 
                	WHERE ROUTINE_SCHEMA = ? AND ROUTINE_NAME = ?`,
		dbName, routineName,
	).Scan(&cnt)
	if err != nil {
		return false, err
	}

	return cnt > 0, nil
}

func IsViewExistsIn(conn *sqlx.Conn, viewName, dbName string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var cnt int
	err := conn.QueryRowxContext(
		ctx,
		`SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS 
                	WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?`,
		dbName, viewName,
	).Scan(&cnt)
	if err != nil {
		return false, err
	}

	return cnt > 0, nil
}
