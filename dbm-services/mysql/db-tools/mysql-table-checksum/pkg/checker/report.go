package checker

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/reporter"
	"fmt"
	"log/slog"
	"strconv"
)

func (r *Checker) masterHosts() (ip string, port int, err error) {
	rows, err := r.db.Queryx(`SHOW SLAVE STATUS`)
	if err != nil {
		slog.Error("querying master hosts: ", slog.String("error", err.Error()))
		return "", 0, err
	}
	defer func() {
		_ = rows.Close()
	}()

	slaveStatus := make(map[string]interface{})
	for rows.Next() {
		err := rows.MapScan(slaveStatus)
		if err != nil {
			slog.Error("scan slave status", slog.String("error", err.Error()))
			return "", 0, err
		}
		break
	}

	for k, v := range slaveStatus {
		if value, ok := v.([]byte); ok {
			slaveStatus[k] = string(value)
		}
	}
	slog.Debug("query master hosts", slog.Any("result map", slaveStatus))
	ip = slaveStatus["Master_Host"].(string)
	port, err = strconv.Atoi(slaveStatus["Master_Port"].(string))

	if err != nil {
		slog.Error("parse master port error", slog.String("error", err.Error()))
		return "", 0, err
	}
	return
}

// Report 只在 repeater, slave 的例行校验做上报
func (r *Checker) Report() error {
	if !r.hasHistoryTable {
		slog.Info("report history table not found")
		return nil
	}

	masterIP, masterPort, err := r.masterHosts()
	if err != nil {
		slog.Error("get master hosts: ", slog.String("error", err.Error()))
		return err
	}
	slog.Info("query master info",
		slog.String("master ip", masterIP), slog.Int("master port", masterPort))

	rows, err := r.db.Queryx(
		fmt.Sprintf(`SELECT master_ip, master_port,
									db, tbl,
									chunk, chunk_time, chunk_index,
									lower_boundary, upper_boundary,
									this_crc, this_cnt, master_crc, master_cnt, ts
							FROM %s WHERE master_ip = ? AND master_port = ? AND reported = 0
										AND (this_crc <> master_crc or this_cnt <> master_cnt)
							UNION
							SELECT master_ip, master_port,
							       db, tbl,
							       chunk, chunk_time, chunk_index,
							       lower_boundary, upper_boundary,
							       this_crc, this_cnt, master_crc, master_cnt, ts
							FROM %s WHERE master_ip = ? AND master_port = ? AND reported = 0
										AND (db = ? OR db = ?)`, r.resultHistoryTable, r.resultHistoryTable),
		masterIP, masterPort, masterIP, masterPort,
		dailyStr, roundStartStr,
	)
	if err != nil {
		slog.Error("query unreported result", slog.String("error", err.Error()))
		return err
	}

	for rows.Next() {
		var cs reporter.ChecksumResult
		err := rows.StructScan(&cs)
		if err != nil {
			slog.Error("scan unreported result", slog.String("error", err.Error()))
			return err
		}

		slog.Debug("scan checksum history", slog.Any("checksum result", cs))

		err = r.reporter.Report(&cs)
		if err != nil {
			return err
		}
	}

	_, err = r.conn.ExecContext(
		context.Background(),
		fmt.Sprintf(`UPDATE %s.%s SET reported = 1
								WHERE master_ip = ? AND master_port = ? AND reported = 0`,
			r.resultDB, r.resultHistoryTable), masterIP, masterPort)
	if err != nil {
		slog.Error("update reported", slog.String("error", err.Error()))
		return err
	}
	slog.Info("update reported")

	return nil
}
