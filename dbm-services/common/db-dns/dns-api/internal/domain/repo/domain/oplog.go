package domain

import (
	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/domain/entity"
	"bk-dnsapi/pkg/logger"
	"fmt"
	"time"
)

// DnsOpLogQuery 操作日志查询条件
type DnsOpLogQuery struct {
	// DomainName 域名，模糊匹配
	DomainName string
	Operator   string
	OpType     string
	StartTime  *time.Time
	EndTime    *time.Time
	Limit      int
	Offset     int
}

// DnsOpLogRepo 操作日志方法接口
type DnsOpLogRepo interface {
	Insert(logs []*entity.TbDnsOpLog) (num int64, err error)
	Query(q DnsOpLogQuery) (rs []entity.TbDnsOpLog, total int64, err error)
}

// DnsOpLogImpl 操作日志方法实现
type DnsOpLogImpl struct {
}

// DnsOpLogResource 操作日志构建类
func DnsOpLogResource() DnsOpLogRepo {
	return &DnsOpLogImpl{}
}

// Insert 批量写入操作日志
func (o *DnsOpLogImpl) Insert(logs []*entity.TbDnsOpLog) (num int64, err error) {
	tx := dao.DnsDB.Begin()
	for _, l := range logs {
		r := tx.Create(l)
		if r.Error != nil {
			tx.Rollback()
			return 0, r.Error
		}
		num += r.RowsAffected
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return
}

// Query 查询操作日志，按时间倒序。total 为满足条件的总条数
func (o *DnsOpLogImpl) Query(q DnsOpLogQuery) (rs []entity.TbDnsOpLog, total int64, err error) {
	db := dao.DnsDB.Model(&entity.TbDnsOpLog{})
	if q.DomainName != "" {
		db = db.Where("domain_name like ?", "%"+escapeLike(q.DomainName)+"%")
	}
	if q.Operator != "" {
		db = db.Where("operator = ?", q.Operator)
	}
	if q.OpType != "" {
		db = db.Where("op_type = ?", q.OpType)
	}
	if q.StartTime != nil {
		db = db.Where("op_time >= ?", *q.StartTime)
	}
	if q.EndTime != nil {
		db = db.Where("op_time <= ?", *q.EndTime)
	}
	logger.Info(fmt.Sprintf("query op log. params[%+v]", q))

	rs = []entity.TbDnsOpLog{}
	if err = db.Count(&total).Error; err != nil {
		return rs, 0, err
	}
	err = db.Order("op_time desc, uid desc").Limit(q.Limit).Offset(q.Offset).Find(&rs).Error
	return rs, total, err
}
