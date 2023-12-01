package timezonechange

import (
	"bufio"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"time"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
)

func sysTzChange(_ *sqlx.DB) (msg string, err error) {
	lastTz, err := readLastSysTz()
	if err != nil {
		return "", err
	}
	slog.Info("get last sys tz", slog.String("tz", lastTz))

	currentTz, _ := time.Now().Zone()
	slog.Info("get current sys tz", slog.String("tz", currentTz))

	err = storeCurrentSysTz(currentTz)
	if err != nil {
		return "", err
	}

	if currentTz != lastTz {
		slog.Info("system tz change", slog.String("last gz", lastTz), slog.String("current tz", currentTz))
		return fmt.Sprintf("system timezone changed from %s to %s", lastTz, currentTz), nil
	}

	return "", nil
}

func readLastSysTz() (tz string, err error) {
	contextFile, err := os.OpenFile(
		filepath.Join(contextBase, fmt.Sprintf("system-tz.%d", config.MonitorConfig.Port)),
		os.O_CREATE|os.O_RDWR,
		0777,
	)
	if err != nil {
		return "", err
	}
	defer func() {
		_ = contextFile.Close()
	}()

	tz, _ = time.Now().Zone()

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

func storeCurrentSysTz(tz string) error {
	contextFile, err := os.OpenFile(
		filepath.Join(contextBase, fmt.Sprintf("system-tz.%d", config.MonitorConfig.Port)),
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

	slog.Info("store current sys tz success")
	return nil
}
