/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package harvest

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	processlistSuspiciousTimeSec = int64(10)
	processlistMaxFetchRows      = 50
	processlistMaxLogRows        = 50
	processlistInfoMaxLen        = 256
)

// processlistSQL caps INFO and the result set on the server so a large PROCESSLIST
// is not pulled into the probe. Keep LEFT/LIMIT in sync with the constants above.
var processlistSQL = fmt.Sprintf(
	"SELECT ID AS id, USER AS `user`, HOST AS host, DB AS db, "+
		"COMMAND AS command, TIME AS time, STATE AS state, LEFT(INFO, %d) AS info "+
		"FROM information_schema.PROCESSLIST "+
		"WHERE COMMAND NOT LIKE '%%Binlog Dump%%' "+
		"AND ((TIME > %d AND COMMAND <> 'Sleep') "+
		"OR STATE LIKE '%%waiting for%%' "+
		"OR INFO LIKE '%%lock table%%' "+
		"OR INFO LIKE '%%flush table%%') "+
		"ORDER BY TIME DESC LIMIT %d",
	processlistInfoMaxLen, processlistSuspiciousTimeSec, processlistMaxFetchRows,
)

// processlistRow is the diagnostic subset of information_schema.PROCESSLIST.
type processlistRow struct {
	ID      uint64         `gorm:"column:id"`
	User    string         `gorm:"column:user"`
	Host    string         `gorm:"column:host"`
	DB      sql.NullString `gorm:"column:db"`
	Command string         `gorm:"column:command"`
	Time    int64          `gorm:"column:time"`
	State   sql.NullString `gorm:"column:state"`
	Info    sql.NullString `gorm:"column:info"`
}

// processlistLogRow is the flat JSON shape logged after a heartbeat REPLACE failure.
type processlistLogRow struct {
	ID      uint64 `json:"id"`
	User    string `json:"user"`
	Host    string `json:"host"`
	DB      string `json:"db"`
	Command string `json:"command"`
	Time    int64  `json:"time"`
	State   string `json:"state"`
	Info    string `json:"info"`
}

func toProcesslistLogRow(row processlistRow) processlistLogRow {
	return processlistLogRow{
		ID:      row.ID,
		User:    row.User,
		Host:    row.Host,
		DB:      nullStringValue(row.DB),
		Command: row.Command,
		Time:    row.Time,
		State:   nullStringValue(row.State),
		Info:    truncateProcesslistInfo(nullStringValue(row.Info)),
	}
}

func nullStringValue(v sql.NullString) string {
	if !v.Valid {
		return ""
	}
	return v.String
}

func truncateProcesslistInfo(info string) string {
	if len(info) <= processlistInfoMaxLen {
		return info
	}
	return info[:processlistInfoMaxLen] + "..."
}

// isSuspiciousProcesslistRow reports whether a session looks like it could block heartbeat writes:
// STATE contains "waiting for", INFO mentions LOCK/FLUSH TABLE(S), or TIME > 10s.
// Binlog dump and idle Sleep sessions are excluded: they stay up for hours and would drown the log.
func isSuspiciousProcesslistRow(row processlistRow) bool {
	cmd := strings.ToLower(row.Command)
	if strings.Contains(cmd, "binlog dump") {
		return false
	}

	state := strings.ToLower(nullStringValue(row.State))
	if strings.Contains(state, "waiting for") {
		return true
	}
	info := strings.ToLower(nullStringValue(row.Info))
	if strings.Contains(info, "lock table") || strings.Contains(info, "flush table") {
		return true
	}
	return row.Time > processlistSuspiciousTimeSec && cmd != "sleep"
}

// logSuspiciousProcesslist queries PROCESSLIST after a heartbeat REPLACE failure.
// parent is the same ctx as the REPLACE; heartbeatScan still applies the per-statement timeout.
// Failure is logged only and never treated as a missing table.
func (c *collector) logSuspiciousProcesslist(parent context.Context) {
	if c.db == nil {
		return
	}

	host := ""
	port := 0
	if c.endpoint != nil {
		host = c.endpoint.Host
		port = c.endpoint.Port
	}

	var rows []processlistRow
	_, err := c.heartbeatScan(parent, &rows, processlistSQL)
	if err != nil {
		logger.Warn("failed to query processlist after heartbeat replace failure, host: %s, port: %d, errmsg: %s",
			host, port, err)
		return
	}

	suspicious := make([]processlistRow, 0)
	for _, row := range rows {
		if isSuspiciousProcesslistRow(row) {
			suspicious = append(suspicious, row)
		}
	}

	logged := suspicious
	omitted := 0
	if len(logged) > processlistMaxLogRows {
		omitted = len(logged) - processlistMaxLogRows
		logged = logged[:processlistMaxLogRows]
	}

	payload := make([]processlistLogRow, 0, len(logged))
	for _, row := range logged {
		payload = append(payload, toProcesslistLogRow(row))
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		logger.Warn("failed to marshal processlist after heartbeat replace failure, host: %s, port: %d, errmsg: %s",
			host, port, err)
		return
	}

	logger.Warn("processlist after heartbeat replace failure, "+
		"host: %s, port: %d, fetched: %d, capped: %t, suspicious: %d, omitted: %d, rows: %s",
		host, port, len(rows), len(rows) >= processlistMaxFetchRows, len(suspicious), omitted, raw)
}
