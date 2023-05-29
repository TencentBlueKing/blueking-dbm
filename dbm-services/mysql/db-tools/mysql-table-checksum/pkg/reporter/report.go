package reporter

import (
	"encoding/json"

	"golang.org/x/exp/slog"
)

// Report 执行上报
func (r *Reporter) Report(cs *ChecksumResult) error {
	rr := ReportRecord{
		ChecksumResult: cs,
		BKBizId:        r.cfg.BkBizId,
		ImmuteDomain:   r.cfg.Cluster.ImmuteDomain,
		ClusterId:      r.cfg.Cluster.Id,
		Ip:             r.cfg.Ip,
		Port:           r.cfg.Port,
		InnerRole:      string(r.cfg.InnerRole),
	}

	row, err := json.Marshal(rr)
	if err != nil {
		slog.Error("marshal report", err)
		return err
	}

	row = append(row, []byte("\n")...)

	_, err = r.writer.Write(row)
	if err != nil {
		slog.Error("write report", err)
		return err
	}

	return nil
}
