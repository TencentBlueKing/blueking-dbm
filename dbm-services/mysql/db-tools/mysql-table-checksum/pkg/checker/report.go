package checker

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/reporter"
	"fmt"

	"golang.org/x/exp/slog"
)

// Report 只在 repeater, slave 的例行校验做上报
func (r *Checker) Report() error {
	if !r.hasHistoryTable {
		slog.Info("report history table not found")
		return nil
	}

	// initReporter(path.Join(r.Config.ReportPath, "checksum_report.log"))

	// ToDo 清理太老的历史记录

	rows, err := r.db.Queryx(
		fmt.Sprintf(
			`SELECT `+
				`master_ip, master_port, db, tbl, `+
				`chunk, chunk_time, chunk_index, lower_boundary, upper_boundary, `+
				`this_crc, this_cnt, master_crc, master_cnt, ts `+
				`FROM %s WHERE CONCAT(master_ip, ":", master_port) <> ? AND reported = 0`,
			r.resultHistoryTable,
		),
		fmt.Sprintf("%s:%d", r.Config.Ip, r.Config.Port),
	)

	if err != nil {
		slog.Error("query unreported result", err)
		return err
	}

	// Todo 这里其实有个风险, 单独在 slave 上修改数据了
	stmt, err := r.db.Preparex(
		fmt.Sprintf(
			`UPDATE %s `+
				`SET reported = 1 `+
				`WHERE master_ip = ? AND master_port = ? AND db = ? AND tbl = ? AND chunk = ? AND ts = ?`,
			r.resultHistoryTable,
		),
	)
	if err != nil {
		slog.Error("prepare update statement", err)
		return err
	}

	for rows.Next() {
		var cs reporter.ChecksumResult
		err := rows.StructScan(&cs)
		if err != nil {
			slog.Error("scan unreported result", err)
			return err
		}

		slog.Debug("scan checksum history", slog.Any("checksum result", cs))

		// err = writeReportRecord(
		//	ReportRecord{
		//		ChecksumResult: cs,
		//		Ip:             r.Config.Ip,
		//		Port:           r.Config.Port,
		//		BKBizId:        r.Config.BkBizId,
		//		ImmuteDomain:   r.Config.Cluster.ImmuteDomain,
		//		ClusterId:      r.Config.Cluster.Id,
		//		InnerRole:      string(r.Config.InnerRole),
		//	},
		// )

		err = r.reporter.Report(&cs)
		if err != nil {
			return err
		}

		_, err = stmt.Exec(
			cs.MasterIp,
			cs.MasterPort,
			cs.Db,
			cs.Tbl,
			cs.Chunk,
			cs.Ts,
		)

		if err != nil {
			slog.Error("update reported", err)
			return err
		}
	}
	return nil
}

// /*
// json 序列化时间的时候用了默认的 format
// 上报的时间格式和 db 中的看起来不太一样
// */
// func writeReportRecord(record ReportRecord) error {
//	row, err := json.Marshal(record)
//	if err != nil {
//		slog.Error("marshal report", err)
//		return err
//	}
//
//	slog.Debug("write report record", slog.String("record", string(row)))
//	row = append(row, []byte("\n")...)
//
//	_, err = reporter.Write(row)
//	if err != nil {
//		slog.Error("write report record", err)
//	}
//
//	return nil
// }
