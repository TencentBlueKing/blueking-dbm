package handler

import (
	"bk-dnsapi/internal/domain/repo/domain"
	"fmt"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

const (
	defaultPageSize = 20
	maxPageSize     = 1000
)

// parsePage 解析分页参数 page(从1开始)、page_size，返回 limit、offset
func parsePage(c *gin.Context) (limit, offset int, err error) {
	page, pageSize := 1, defaultPageSize
	if s := strings.TrimSpace(c.Query("page")); s != "" {
		if page, err = strconv.Atoi(s); err != nil || page < 1 {
			return 0, 0, fmt.Errorf("page[%s] must be a positive integer", s)
		}
	}
	if s := strings.TrimSpace(c.Query("page_size")); s != "" {
		if pageSize, err = strconv.Atoi(s); err != nil || pageSize < 1 || pageSize > maxPageSize {
			return 0, 0, fmt.Errorf("page_size[%s] must be an integer in [1,%d]", s, maxPageSize)
		}
	}
	return pageSize, (page - 1) * pageSize, nil
}

// SearchDns 检索域名，一行一个域名，返回维护方式、实例列表、管理人、更新人、更新时间。
// 支持域名(模糊)、维护方式(domain_type: 0集群托管 1自主维护)、负责人(manager)，条件之间为 and 关系，都不传返回全部
func (h *Handler) SearchDns(c *gin.Context) {
	defer recoverPanic(c)

	q := domain.DomainSearchQuery{
		DomainName: strings.TrimSpace(c.Query("domain_name")),
		Manager:    strings.TrimSpace(c.Query("manager")),
	}
	// domain_type 传了就按值查询，没有匹配数据则返回空结果；不传则不过滤。
	// 非整数的值不可能匹配任何记录，直接返回空结果
	if s := strings.TrimSpace(c.Query("domain_type")); s != "" {
		t, err := strconv.ParseInt(s, 10, 64)
		if err != nil {
			SendResponse(c, nil, Data{Detail: []domain.DomainSearchResult{}, RowsNum: 0})
			return
		}
		q.DomainType = &t
	}
	var err error
	if q.Limit, q.Offset, err = parsePage(c); err != nil {
		SendResponse(c, err, Data{})
		return
	}

	rs, total, err := domain.DnsDomainMgrResource().Search(q)
	if err != nil {
		SendResponse(c, err, Data{})
		return
	}
	SendResponse(c, nil, Data{Detail: rs, RowsNum: total})
}
