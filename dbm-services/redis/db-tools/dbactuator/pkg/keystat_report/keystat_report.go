package keystat_report

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

// KeyStatRecord 集群报告记录
type KeyStatRecord struct {
	//	BkBizId              int64  `json:"bk_biz_id"`    // 业务ID
	//	TicketId             int64  `json:"ticket_id"`    // 单据ID
	RecordId int `json:"record_id"` // 报告记录ID
	//	ClusterId            int64  `json:"cluster_id"`   // ticket_id + cluster_id 作为唯一标识
	//	ClusterType          string `json:"cluster_type"` // 集群类型
	//	ImmuteDomain         string `json:"immute_domain"`
	//	ClusterShardNum      int    `json:"cluster_shard_num"`        // 集群总分片数
	AnalyzedShardNum     int    `json:"analyzed_shard_num"`       // 分析的分片数
	KeyStatRowsCount     int    `json:"key_stat_rows_count"`      // 报告记录数
	RankKeyStatRowsCount int    `json:"rank_key_stat_rows_count"` // rank报告记录数
	Status               string `json:"status"`                   // 报告状态
	ExecIp               string `json:"exec_ip"`                  // 执行IP
	AnalysisTime         int    `json:"analysis_time"`            // 分析时间,单位:秒
	RedisVersion         string `json:"redis_version"`            // Redis版本
	SourceType           string `json:"source_type"`              // 源类型
	SourceRole           string `json:"source_role"`              // 源角色
	SourceAddrList       string `json:"source_addr_list"`         // 源地址列表
	AtimeAvailable       bool   `json:"atime_available"`          // atime是否可用
	SamplingRatio        int    `json:"sampling_ratio"`           // 采样比例, 用于计算分析进度. 0-100.
}

// KeyReportReportBase 基础报告结构体. 用于key报告和rank报告的关联.
type KeyReportReportBase struct {
	RecordId int `json:"record_id"`
}

// 以下结果来自于key-splitter工程.
type KeyStatReportItem struct {
	KeyReportReportBase
	KeyType                      string  `json:"key_type"`
	KeyName                      string  `json:"key_name"`
	Class                        string  `json:"key_class"`
	Count                        int     `json:"count"`
	CountWithTtl                 int     `json:"count_with_ttl"` // 不显示.
	AvgTtl                       int64   `json:"avg_ttl" `       // ttl 需要当前时间比较.
	AvgTtlHuman                  string  `json:"avg_ttl_human"`
	MinIdleTime                  int64   `json:"min_idletime"`
	MinIdletimeHuman             string  `json:"min_idletime_human"`
	MinIdletimeShow              string  `json:"min_idletime_show,omitempty"`
	SharedObjectMinIdletimeHuman string  `json:"so_min_idletime_human"`
	MemberCountMax               int     `json:"member_max_count"`
	MemUsedBytes                 int64   `json:"mem_used_bytes"`
	MemUsedPct                   float64 `json:"mem_used_pct,omitempty"`
	AvgKeyUsedBytes              int64   `json:"avg_key_used_bytes" ` // 平均key占用字节数
	AvgKeyLength                 int64   `json:"avg_key_length"`      // 平均key长度
}

// RankKeyReportRow
// 用于解析 rank-key-splitter.report 文件. rank-key-splitter.report 是一个map[string]RankKeyReportRow.
// 其中key 是 "global" 或者 "$key_type".
type RankKeyReportRow struct {
	TopN    int64             `json:"top_n"`
	Min     int64             `json:"min"`
	Count   int64             `json:"count"`
	KeyList []KeyStatRankItem `json:"key_list"`
}

// KeyStatRankItem 返回给Saas的Rank报告结构体.
type KeyStatRankItem struct {
	KeyReportReportBase
	LdbKey
	RankValue int64  `json:"rank_value"`
	KeyType   string `json:"key_type"`            // 从 LdbKey.Type 中解析出来.
	KeyName   string `json:"key_name"`            // 从 LdbKey.key 中解析出来.
	TtlHuman  string `json:"ttl_human,omitempty"` // 过期时间（带单位） 用于展示, 非必填. 从 LdbKey.Ttl 中解析出来.
	KeyLen    int    `json:"key_length"`          // Key的长度. 从 LdbKey.Key 中解析出来.
}

// LdbKey 用于解析 ldb 导出来的Key
type LdbKey struct {
	Type         byte   `json:"-"` // Key type
	Key          string `json:"key"`
	Ttl          int64  `json:"ttl"` // second/1000
	Atime        int64  `json:"atime"`
	Member       int    `json:"member"`     // 成员的数量
	MemberLen    int    `json:"member_len"` // 成员的平均长度.
	ValueSize    int    `json:"value_size"` // Value的长度或者成员Value的长度.
	Db           uint8  `json:"db"`
	SharedObject bool   `json:"-"`           // [0-9999] 的数字. 在这个范围内，它的Atime有可能是不准确的.
	MemorySize   int    `json:"memory_size"` // 基础内存占用, 复合类型中是采样计算结果。
}

// loadReport 加载报告 返回集群报告记录, key报告和rank报告
func LoadReport(reportFile string) (keyReportRowItems []KeyStatReportItem, err error) {
	report, err := os.ReadFile(reportFile)
	if err != nil {
		err = errors.New("open reportFile failed, err:" + err.Error())
		return
	}

	err = json.Unmarshal(report, &keyReportRowItems)
	if err != nil {
		err = errors.New("loadReport failed, err:" + err.Error())
		return
	}

	// 计算CountWithTtl
	for i := range keyReportRowItems {
		updateAvgTtlHuman(&keyReportRowItems[i])
	}

	return keyReportRowItems, nil
}

// updateAvgTtlHuman 更新AvgTtlHuman. 显示在UI上.
// 如果CountWithTtl为0, 则设置为"N/A".
// 如果全都有过期时间, 则设置为"avg:xxx".
// 否则设置为"count:xxx, avg:xxx".
func updateAvgTtlHuman(item *KeyStatReportItem) {
	if item.CountWithTtl == 0 {
		item.AvgTtlHuman = "N/A"
		return
	}
	if item.CountWithTtl == item.Count {
		item.AvgTtlHuman = fmt.Sprintf("avg:%s", getTtlHuman(item.AvgTtl))
	} else {
		item.AvgTtlHuman = fmt.Sprintf("count:%d, avg:%s", item.CountWithTtl, getTtlHuman(item.AvgTtl))
	}
}

// LoadRankReport 加载rank报告 返回rank报告
func LoadRankReport(rankReportFile string) (rankKeyReportRow map[string]RankKeyReportRow, err error) {
	rankReport, err := os.ReadFile(rankReportFile)
	if err != nil {
		err = errors.New("open rankReportFile failed, err:" + err.Error())
		return nil, err
	}

	err = json.Unmarshal(rankReport, &rankKeyReportRow)
	if err != nil {
		return nil, err
	}
	// 将rank报告的Ttl转换为人类可读的时间格式.
	for t := range rankKeyReportRow {
		for i := range rankKeyReportRow[t].KeyList {
			item := rankKeyReportRow[t].KeyList[i]
			rankKeyReportRow[t].KeyList[i].TtlHuman = getTtlHuman(item.Ttl)
			rankKeyReportRow[t].KeyList[i].KeyLen = len(item.Key)
		}
	}

	return rankKeyReportRow, nil
}

const (
	secondsPerYear  = int64(365 * 24 * 3600) // 31536000
	secondsPerMonth = int64(30 * 24 * 3600)  // 2592000
	secondsPerDay   = int64(24 * 3600)       // 86400
	secondsPerHour  = int64(3600)
)

// getTtlHuman 将秒数转换为人类可读的时间格式
// 例如: 31536000 -> "1.0year", 86400 -> "1.0day", 3600 -> "1.0hour", 60 -> "60sec"
func getTtlHuman(t int64) string {
	var value float64
	var unit string

	switch {
	case t == -1:
		return "-"
	case t >= secondsPerYear:
		value = float64(t) / float64(secondsPerYear)
		unit = "year"
	case t >= secondsPerMonth:
		value = float64(t) / float64(secondsPerMonth)
		unit = "mon"
	case t >= secondsPerDay:
		value = float64(t) / float64(secondsPerDay)
		unit = "day"
	case t >= secondsPerHour:
		value = float64(t) / float64(secondsPerHour)
		unit = "hour"
	case t >= 0:
		value = float64(t)
		unit = "sec"
	default:
		// 其他情况, 直接返回原值吧. 这样也能兼容一些特殊情况.
		return fmt.Sprintf("%d", t)
	}

	return fmt.Sprintf("%.1f%s", value, unit)
}
