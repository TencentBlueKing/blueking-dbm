package handler

import (
	"bk-dnsapi/internal/domain/entity"
	"bk-dnsapi/internal/domain/repo/domain"
	"bk-dnsapi/pkg/logger"
	"bk-dnsapi/pkg/tools"
	"fmt"
	"runtime/debug"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

const timeLayout = "2006-01-02 15:04:05"

var validOpTypes = map[string]bool{
	entity.OpTypeCreateDomain:  true,
	entity.OpTypeUpdateManager: true,
	entity.OpTypeUpdateRemark:  true,
	entity.OpTypeUpdateIp:      true,
	entity.OpTypeDeleteDomain:  true,
}

// OpLogPutReqParam 写入操作日志参数
type OpLogPutReqParam struct {
	Logs []struct {
		// OpTime 操作时间，格式 2006-01-02 15:04:05；为空则取当前时间
		OpTime   string `json:"op_time"`
		Operator string `json:"operator"`
		// ClientIp 客户端IP；为空则取请求来源IP
		ClientIp   string `json:"client_ip"`
		OpType     string `json:"op_type"`
		DomainName string `json:"domain_name"`
		Content    string `json:"content"`
	} `json:"logs"`
}

// AddOpLog 写入操作日志
func (h *Handler) AddOpLog(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c, fmt.Errorf("panic error:%v", r), Data{})
		}
	}()

	var param OpLogPutReqParam
	if err := c.BindJSON(&param); err != nil {
		SendResponse(c, err, Data{})
		return
	}
	if len(param.Logs) == 0 {
		SendResponse(c, fmt.Errorf("param logs must not be empty"), Data{})
		return
	}

	var errMsg string
	var logs []*entity.TbDnsOpLog
	for i, l := range param.Logs {
		operator := strings.TrimSpace(l.Operator)
		if operator == "" {
			errMsg += fmt.Sprintf("logs[%d]: operator must not be empty\r\n", i)
		}
		if !validOpTypes[l.OpType] {
			errMsg += fmt.Sprintf("logs[%d]: op_type[%s] invalid\r\n", i, l.OpType)
		}
		domainName, err := tools.CheckDomain(l.DomainName)
		if err != nil {
			errMsg += fmt.Sprintf("logs[%d]: %s\r\n", i, err.Error())
		}
		opTime := time.Now()
		if s := strings.TrimSpace(l.OpTime); s != "" {
			if opTime, err = time.ParseInLocation(timeLayout, s, time.Local); err != nil {
				errMsg += fmt.Sprintf("logs[%d]: op_time[%s] format must be %s\r\n", i, s, timeLayout)
			}
		}
		clientIp := strings.TrimSpace(l.ClientIp)
		if clientIp == "" {
			clientIp = c.ClientIP()
		}
		logs = append(logs, &entity.TbDnsOpLog{
			OpTime:     opTime,
			Operator:   operator,
			ClientIp:   clientIp,
			OpType:     l.OpType,
			DomainName: domainName,
			Content:    l.Content,
		})
	}
	if errMsg != "" {
		SendResponse(c, fmt.Errorf("%s", errMsg), Data{})
		return
	}

	rowsAffected, err := domain.DnsOpLogResource().Insert(logs)
	SendResponse(c, err, Data{RowsNum: rowsAffected})
}

// parseOpLogQuery 解析公共过滤条件与分页
func parseOpLogQuery(c *gin.Context) (domain.DnsOpLogQuery, error) {
	q := domain.DnsOpLogQuery{
		Operator: strings.TrimSpace(c.Query("operator")),
		OpType:   strings.TrimSpace(c.Query("op_type")),
	}
	if q.OpType != "" && !validOpTypes[q.OpType] {
		return q, fmt.Errorf("op_type[%s] invalid", q.OpType)
	}
	for _, p := range []struct {
		key string
		dst **time.Time
	}{{"start_time", &q.StartTime}, {"end_time", &q.EndTime}} {
		s := strings.TrimSpace(c.Query(p.key))
		if s == "" {
			continue
		}
		t, err := time.ParseInLocation(timeLayout, s, time.Local)
		if err != nil {
			return q, fmt.Errorf("%s[%s] format must be %s", p.key, s, timeLayout)
		}
		*p.dst = &t
	}
	var err error
	q.Limit, q.Offset, err = parsePage(c)
	return q, err
}

// GetDomainOpLog 查询域名级别的操作日志，域名为模糊匹配
func (h *Handler) GetDomainOpLog(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c, fmt.Errorf("panic error:%v", r), Data{})
		}
	}()

	domainName := strings.TrimSpace(c.Query("domain_name"))
	if domainName == "" {
		SendResponse(c, fmt.Errorf("param domain_name must not be empty"), Data{})
		return
	}
	q, err := parseOpLogQuery(c)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	q.DomainName = domainName

	rs, total, err := domain.DnsOpLogResource().Query(q)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	SendResponse(c, nil, Data{Detail: rs, RowsNum: total})
}

// GetAllOpLog 查询全局操作日志
func (h *Handler) GetAllOpLog(c *gin.Context) {
	defer func() {
		if r := recover(); r != nil {
			logger.Error(fmt.Sprintf("panic error:%v,stack:%s", r, string(debug.Stack())))
			SendResponse(c, fmt.Errorf("panic error:%v", r), Data{})
		}
	}()

	q, err := parseOpLogQuery(c)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	rs, total, err := domain.DnsOpLogResource().Query(q)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	SendResponse(c, nil, Data{Detail: rs, RowsNum: total})
}
