package rotateproxyconnlog

import (
	"bytes"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"time"

	"github.com/jmoiron/sqlx"
)

var name = "rotate-proxy-connlog"

type Dummy struct {
	db *sqlx.DB
}

func (d *Dummy) Run() (msg string, err error) {
	defer func() {
		_ = d.enableConnlog()
	}()

	connLogFilePath := fmt.Sprintf(`/data/mysql-proxy/%d/log/mysql-proxy.log`, config.MonitorConfig.Port)

	_, err = os.Stat(connLogFilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return "", nil
		}
		slog.Error("get proxy conn log stat", slog.String("err", err.Error()))
		return "", err
	}

	historyFilePath := fmt.Sprintf(`%s.%d.gz`, connLogFilePath, time.Now().Weekday())
	st, err := os.Stat(historyFilePath)
	if err != nil {
		if !os.IsNotExist(err) {
			slog.Error(
				"get proxy conn log history stat",
				slog.String("historyFilePath", historyFilePath),
				slog.String("err", err.Error()),
			)
			return "", err
		}
	} else {
		if time.Now().Sub(st.ModTime()) < 3*24*time.Hour {
			slog.Info(
				"rotate proxy conn log skip too frequency call",
				slog.Time("now", time.Now()),
				slog.Time("history file mod time", st.ModTime()),
				slog.String("historyFilePath", historyFilePath),
			)
			return "", nil
		}
	}

	hf, err := os.OpenFile(historyFilePath, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0666)
	if err != nil {
		slog.Error("create history file", slog.String("err", err.Error()))
		return "", err
	}

	err = d.disableConnlog()
	if err != nil {
		return "", err
	}

	gzCmd := exec.Command("gzip", "-c", connLogFilePath)
	slog.Info("gzip cmd", slog.String("cmd", gzCmd.String()))

	gzCmd.Stdout = hf
	var stderr bytes.Buffer
	gzCmd.Stderr = &stderr
	err = gzCmd.Run()
	if err != nil {
		slog.Error("gzip connlog",
			slog.String("error", err.Error()),
			slog.String("stderr", stderr.String()),
		)
		return "", err
	}
	slog.Info(
		"gzip connlog file",
		slog.String("from", connLogFilePath),
		slog.String("to", historyFilePath),
	)

	err = os.Truncate(connLogFilePath, 0)
	if err != nil {
		slog.Error(
			"truncate conn log file",
			slog.String("err", err.Error()),
			slog.String("file", connLogFilePath),
		)
		return "", err
	}
	slog.Info("truncate conn log file", slog.String("file", connLogFilePath))

	return "", nil
}

func (d *Dummy) disableConnlog() error {
	_, err := d.db.Exec(`refresh_connlog(0)`)
	if err != nil {
		slog.Error("disable connlog", slog.String("error", err.Error()))
		return err
	}
	slog.Info("disable connlog")
	return nil
}

func (d *Dummy) enableConnlog() error {
	_, err := d.db.Exec(`refresh_connlog(1)`)
	if err != nil {
		slog.Error("enable connlog", slog.String("error", err.Error()))
		return err
	}
	slog.Info("enable connlog")
	return nil
}

// Name 监控项名
func (d *Dummy) Name() string {
	return name
}

func NewRotateProxyConnlog(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Dummy{db: cc.ProxyAdminDB}
}

func RegisterRotateProxyConnlog() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewRotateProxyConnlog
}
