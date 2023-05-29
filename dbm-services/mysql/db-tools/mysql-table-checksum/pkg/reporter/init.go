package reporter

import "time"

// ChecksumResult 校验结果
type ChecksumResult struct {
	MasterIp      string    `db:"master_ip" json:"master_ip"`
	MasterPort    int       `db:"master_port" json:"master_port"`
	Db            string    `db:"db" json:"db"`
	Tbl           string    `db:"tbl" json:"tbl"`
	Chunk         int       `db:"chunk" json:"chunk"`
	ChunkTime     float64   `db:"chunk_time" json:"chunk_time"`
	ChunkIndex    *string   `db:"chunk_index" json:"chunk_index"`
	LowerBoundary *string   `db:"lower_boundary" json:"lower_boundary"`
	UpperBoundary *string   `db:"upper_boundary" json:"upper_boundary"`
	ThisCrc       string    `db:"this_crc" json:"this_crc"`
	ThisCnt       int       `db:"this_cnt" json:"this_cnt"`
	MasterCrc     string    `db:"master_crc" json:"master_crc"`
	MasterCnt     int       `db:"master_cnt" json:"master_cnt"`
	Ts            time.Time `db:"ts" json:"ts"`
}

// ReportRecord 上报记录
type ReportRecord struct {
	*ChecksumResult `json:",inline"`
	BKBizId         int    `json:"bk_biz_id"`
	ImmuteDomain    string `json:"immute_domain"`
	ClusterId       int    `json:"cluster_id"`
	Ip              string `json:"ip"`
	Port            int    `json:"port"`
	InnerRole       string `json:"inner_role"`
}
