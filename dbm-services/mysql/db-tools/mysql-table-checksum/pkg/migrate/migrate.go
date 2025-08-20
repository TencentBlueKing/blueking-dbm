package migrate

import (
	"context"
	"database/sql"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"errors"
	"fmt"
	"path/filepath"

	_ "github.com/go-sql-driver/mysql"
	"github.com/golang-migrate/migrate/v4"
	"github.com/golang-migrate/migrate/v4/database/mysql"
	_ "github.com/golang-migrate/migrate/v4/source/file"
)

const migTable = "checksum_migrations"

func Migrate() error {
	db, err := sql.Open(
		"mysql",
		fmt.Sprintf(
			"%s:%s@tcp(%s:%d)/%s?multiStatements=true",
			config.ChecksumConfig.User, config.ChecksumConfig.Password,
			config.ChecksumConfig.Ip, config.ChecksumConfig.Port,
			config.ResultDb,
		),
	)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()

	var migExists bool
	err = db.QueryRow(
		`SELECT COUNT(*)=3 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME IN (?, ?, ?)`,
		config.ResultDb, migTable, config.ResultTable, config.ResultHistoryTable).Scan(&migExists)
	if err != nil {
		panic(err)
	}
	if !migExists {
		conn, err := db.Conn(context.Background())
		if err != nil {
			return err
		}
		defer func() {
			_ = conn.Close()
		}()

		_, err = conn.ExecContext(
			context.Background(), `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;`)
		if err != nil {
			return err
		}

		_, err = conn.ExecContext(
			context.Background(), `SET BINLOG_FORMAT = 'STATEMENT'`)
		if err != nil {
			return err
		}

		_, _ = db.Exec(fmt.Sprintf(`DROP TABLE IF EXISTS %s.%s`, config.ResultDb, migTable))
		_, _ = db.Exec(fmt.Sprintf(`DROP TABLE IF EXISTS %s.%s`, config.ResultDb, config.ResultTable))
		_, _ = db.Exec(fmt.Sprintf(`DROP TABLE IF EXISTS %s.%s`, config.ResultDb, config.ResultHistoryTable))
	}

	driver, err := mysql.WithInstance(db, &mysql.Config{
		MigrationsTable: migTable,
	})
	if err != nil {
		panic(err)
	}
	defer func() {
		_ = driver.Close()
	}()

	m, err := migrate.NewWithDatabaseInstance(fmt.Sprintf("file://%s", filepath.Join(config.ExecutablePath, "migrations")), config.ResultDb, driver)
	if err != nil {
		panic(err)
	}
	defer func() {
		_, _ = m.Close()
	}()

	err = m.Up()
	if err != nil && !errors.Is(err, migrate.ErrNoChange) {
		panic(err)
	}

	return nil
}
