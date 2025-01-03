package timezonechange

import (
	"bufio"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func mysqlTzChange(db *sqlx.DB) (msg string, err error) {
	lastTz, err := readLastMysqlTz()
	if err != nil {
		return "", err
	}
	slog.Info("get last mysql tz", slog.String("tz", lastTz))

	var currentTz string
	err = db.QueryRowx(`SELECT @@time_zone`).Scan(&currentTz)
	if err != nil {
		return "", err
	}

	if currentTz == "" {
		return fmt.Sprintf("empty mysql timezone found"), nil
	}

	slog.Info("get current mysql tz", slog.String("tz", currentTz))

	err = storeCurrentMysqlTz(currentTz)
	if err != nil {
		return "", err
	}

	if lastTz == "" {
		return "", nil
	}

	if currentTz != lastTz {
		slog.Info("mysql tz change", slog.String("last tz", lastTz), slog.String("current tz", currentTz))
		return fmt.Sprintf("mysql timezone changed from %s to %s", lastTz, currentTz), nil
	}

	return "", nil
}

func readLastMysqlTz() (tz string, err error) {
	contextFile, err := os.OpenFile(
		filepath.Join(contextBase, fmt.Sprintf("mysql-tz.%d", config.MonitorConfig.Port)),
		os.O_CREATE|os.O_RDWR,
		0777,
	)
	if err != nil {
		return "", err
	}
	defer func() {
		_ = contextFile.Close()
	}()

	scanner := bufio.NewScanner(contextFile)
	scanner.Split(bufio.ScanLines)
	for scanner.Scan() {
		tz = scanner.Text()
	}
	if err := scanner.Err(); err != nil {
		return "", err
	}

	return
}

func storeCurrentMysqlTz(tz string) error {
	contextFile, err := os.OpenFile(
		filepath.Join(contextBase, fmt.Sprintf("mysql-tz.%d", config.MonitorConfig.Port)),
		os.O_CREATE|os.O_RDWR|os.O_TRUNC,
		0777,
	)
	if err != nil {
		return err
	}
	defer func() {
		_ = contextFile.Close()
	}()

	_, err = contextFile.WriteString(tz)
	if err != nil {
		return err
	}

	slog.Info("store current mysql tz success")
	return nil
}
