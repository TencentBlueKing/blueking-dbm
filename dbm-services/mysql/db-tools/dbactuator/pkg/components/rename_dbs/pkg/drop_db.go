package pkg

import (
	"context"
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/jmoiron/sqlx"
)

func DropDB(conn *sqlx.Conn, dbName, to string, onlyStageTable bool) error {
	yes, err := isDBTransClean(conn, dbName, to, onlyStageTable)
	if err != nil {
		return err
	}
	if !yes {
		return fmt.Errorf(`db "%s" is not trans clean`, dbName)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", dbName),
	)

	return err
}

func isDBTransClean(conn *sqlx.Conn, from, to string, onlyStageTable bool) (bool, error) {
	dbEmpty, err := isDBEmpty(conn, from)
	if err != nil {
		return false, err
	}

	yes, err := isTableTransClean(conn, from, to)
	if err != nil {
		return false, err
	}

	if !dbEmpty && !yes {
		return false, nil
	}
	logger.Info("%s table trans clean", from)

	if onlyStageTable {
		logger.Info("db %s only stage table, trans clean", to)
		return true, nil
	}

	yes, err = isTriggerTransClean(conn, from, to)
	if err != nil {
		return false, err
	}
	if !yes {
		return false, nil
	}
	logger.Info("%s trigger trans clean", from)

	yes, err = isEventTransClean(conn, from, to)
	if err != nil {
		return false, err
	}
	if !yes {
		return false, nil
	}
	logger.Info("%s event trans clean", from)

	yes, err = isRoutineTransClean(conn, from, to)
	if err != nil {
		return false, err
	}
	if !yes {
		return false, nil
	}
	logger.Info("%s routine trans clean", from)

	yes, err = isViewTransClean(conn, from, to)
	if err != nil {
		return false, err
	}
	if !yes {
		return false, nil
	}
	logger.Info("%s view trans clean", from)

	return true, nil
}

func isDBEmpty(conn *sqlx.Conn, dbName string) (bool, error) {
	var tableCount int

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := conn.QueryRowxContext(
		ctx,
		`SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
					WHERE TABLE_SCHEMA = ? AND TABLE_TYPE = 'BASE TABLE'`,
		dbName,
	).Scan(&tableCount)
	if err != nil {
		return false, err
	}

	return tableCount == 0, nil
}

func isTableTransClean(conn *sqlx.Conn, from, to string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var tables []string
	err := conn.SelectContext(
		ctx,
		&tables,
		`SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_TYPE = 'BASE TABLE'`,
		from,
	)
	if err != nil {
		return false, err
	}

	defer func() {
		for _, t := range tables {
			flushTable(conn, from, to, t)
		}
	}()

	for _, table := range tables {
		yes, err := IsTableExistsIn(conn, table, to)
		if err != nil {
			return false, err
		}
		if !yes {
			return false, nil
		}
	}
	return true, nil
}

func isTriggerTransClean(conn *sqlx.Conn, from, to string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var triggers []string
	err := conn.SelectContext(
		ctx,
		&triggers,
		`SELECT TRIGGER_NAME FROM INFORMATION_SCHEMA.TRIGGERS WHERE TRIGGER_SCHEMA = ?`,
		from,
	)
	if err != nil {
		return false, err
	}

	for _, trigger := range triggers {
		yes, err := IsTriggerExistsIn(conn, trigger, to)
		if err != nil {
			return false, err
		}
		if !yes {
			return false, nil
		}
	}
	return true, nil
}

func isEventTransClean(conn *sqlx.Conn, from, to string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var events []string
	err := conn.SelectContext(
		ctx,
		&events,
		`SELECT EVENT_NAME FROM INFORMATION_SCHEMA.EVENTS WHERE EVENT_SCHEMA = ?`,
		from,
	)
	if err != nil {
		return false, err
	}

	for _, event := range events {
		yes, err := IsEventExistsIn(conn, event, to)
		if err != nil {
			return false, err
		}
		if !yes {
			return false, nil
		}
	}
	return true, nil
}

func isRoutineTransClean(conn *sqlx.Conn, from, to string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var routines []string
	err := conn.SelectContext(
		ctx,
		&routines,
		`SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_SCHEMA = ?`,
		from,
	)
	if err != nil {
		return false, err
	}

	for _, routine := range routines {
		yes, err := IsRoutineExistsIn(conn, routine, to)
		if err != nil {
			return false, err
		}
		if !yes {
			logger.Error("%s routine %s not exists", routine, to)
			return false, nil
		}
	}
	return true, nil
}

func isViewTransClean(conn *sqlx.Conn, from, to string) (bool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var views []string
	err := conn.SelectContext(
		ctx,
		&views,
		`SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = ?`,
		from,
	)
	if err != nil {
		return false, err
	}

	for _, view := range views {
		yes, err := IsViewExistsIn(conn, view, to)
		if err != nil {
			return false, err
		}
		if !yes {
			return false, nil
		}
	}
	return true, nil
}
