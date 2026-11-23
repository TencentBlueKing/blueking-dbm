package domain

import (
	"bk-dnsapi/internal/domain/entity"
	"fmt"
	"strings"
	"time"

	"github.com/jinzhu/gorm"
)

// OpContext 写操作的操作上下文：用于记录域名更新人和操作日志
type OpContext struct {
	// Operator 操作人，为空时取 fallback，再为空取 system
	Operator string
	// ClientIp 客户端IP，写入操作日志
	ClientIp string
}

// operatorOr 返回操作人：优先 Operator，其次 fallback，最后 system
func (o OpContext) operatorOr(fallback string) string {
	return resolveUpdater(o.Operator, fallback)
}

func joinList(ss []string) string {
	return "[" + strings.Join(ss, ",") + "]"
}

func newOpLog(op OpContext, fallback string, now time.Time, opType, domainName, content string) *entity.TbDnsOpLog {
	return &entity.TbDnsOpLog{
		OpTime:     now,
		Operator:   op.operatorOr(fallback),
		ClientIp:   op.ClientIp,
		OpType:     opType,
		DomainName: domainName,
		Content:    content,
	}
}

// writeOpLogs 在事务中写入操作日志，任意一条失败返回错误，由调用方回滚
func writeOpLogs(tx *gorm.DB, logs []*entity.TbDnsOpLog) error {
	for _, l := range logs {
		if err := tx.Create(l).Error; err != nil {
			return err
		}
	}
	return nil
}

// getDomainInfo 读取 tb_dns_domain_info 中的域名记录，没有记录返回零值
func getDomainInfo(tx *gorm.DB, domainName string) (entity.TbDnsDomainInfo, error) {
	var info entity.TbDnsDomainInfo
	if err := tx.Where("domain_name = ?", domainName).First(&info).Error; err != nil {
		if gorm.IsRecordNotFoundError(err) {
			return entity.TbDnsDomainInfo{}, nil
		}
		return entity.TbDnsDomainInfo{}, err
	}
	return info, nil
}

func instancesOf(recs []entity.TbDnsBase) []string {
	ins := make([]string, 0, len(recs))
	for _, r := range recs {
		ins = append(ins, DomainInstance{Ip: r.Ip, Port: r.Port}.String())
	}
	return ins
}

// buildInsertLogs 新增记录对应的操作日志，每个域名一条。
// isNew 为 true 记 CREATE_DOMAIN（域名在本次新增前不存在），否则记 UPDATE_IP（往已有域名追加实例）
func buildInsertLogs(dnsList []*entity.TbDnsBase, isNew map[string]bool, op OpContext,
	now time.Time) []*entity.TbDnsOpLog {
	var order []string
	group := map[string][]*entity.TbDnsBase{}
	for _, l := range dnsList {
		if _, ok := group[l.DomainName]; !ok {
			order = append(order, l.DomainName)
		}
		group[l.DomainName] = append(group[l.DomainName], l)
	}
	var logs []*entity.TbDnsOpLog
	for _, name := range order {
		recs := group[name]
		ins := make([]string, 0, len(recs))
		for _, r := range recs {
			ins = append(ins, DomainInstance{Ip: r.Ip, Port: r.Port}.String())
		}
		first := recs[0]
		manager := normalizeManagers(first.Manager)
		if isNew[name] {
			content := fmt.Sprintf("create domain, instances: %s, manager: %s, remark: %s, domain_type: %d, "+
				"app: %s, bk_cloud_id: %d", joinList(ins), manager, first.Remark, first.DomainType, first.App,
				first.BkCloudId)
			logs = append(logs, newOpLog(op, manager, now, entity.OpTypeCreateDomain, name, content))
			continue
		}
		logs = append(logs, newOpLog(op, manager, now, entity.OpTypeUpdateIp, name,
			fmt.Sprintf("add instances: %s", joinList(ins))))
	}
	return logs
}

// buildDeleteLogs 删除记录对应的操作日志，每个域名一条。remaining 为删除后该域名剩余的记录数：
// 为 0（或不在 map 中）记 DELETE_DOMAIN，否则记 UPDATE_IP
func buildDeleteLogs(records []entity.TbDnsBase, remaining map[string]int64, op OpContext,
	now time.Time) []*entity.TbDnsOpLog {
	var order []string
	group := map[string][]entity.TbDnsBase{}
	for _, r := range records {
		if _, ok := group[r.DomainName]; !ok {
			order = append(order, r.DomainName)
		}
		group[r.DomainName] = append(group[r.DomainName], r)
	}
	var logs []*entity.TbDnsOpLog
	for _, name := range order {
		recs := group[name]
		ins := joinList(instancesOf(recs))
		if remaining[name] == 0 {
			content := fmt.Sprintf("delete domain, removed instances: %s, app: %s, bk_cloud_id: %d",
				ins, recs[0].App, recs[0].BkCloudId)
			logs = append(logs, newOpLog(op, "", now, entity.OpTypeDeleteDomain, name, content))
			continue
		}
		logs = append(logs, newOpLog(op, "", now, entity.OpTypeUpdateIp, name,
			fmt.Sprintf("remove instances: %s", ins)))
	}
	return logs
}

// buildManagerLog 管理人有变化时返回 UPDATE_MANAGER 日志，否则返回 nil
func buildManagerLog(domainName, oldManager, newManager string, op OpContext, now time.Time) *entity.TbDnsOpLog {
	if newManager == "" || newManager == oldManager {
		return nil
	}
	return newOpLog(op, "", now, entity.OpTypeUpdateManager, domainName,
		fmt.Sprintf("manager: %s -> %s", oldManager, newManager))
}

// buildRemarkLog 备注有变化时返回 UPDATE_REMARK 日志，否则返回 nil
func buildRemarkLog(domainName, oldRemark, newRemark string, op OpContext, now time.Time) *entity.TbDnsOpLog {
	if oldRemark == newRemark {
		return nil
	}
	return newOpLog(op, "", now, entity.OpTypeUpdateRemark, domainName,
		fmt.Sprintf("remark: %s -> %s", oldRemark, newRemark))
}

// buildSyncLogs 同步域名对应的操作日志：实例有增删记 UPDATE_IP，管理人有变化记 UPDATE_MANAGER
func buildSyncLogs(domainName string, added, removed []string, oldManager, newManager string, op OpContext,
	now time.Time) []*entity.TbDnsOpLog {
	var logs []*entity.TbDnsOpLog
	if len(added) > 0 || len(removed) > 0 {
		var parts []string
		if len(added) > 0 {
			parts = append(parts, "add instances: "+joinList(added))
		}
		if len(removed) > 0 {
			parts = append(parts, "remove instances: "+joinList(removed))
		}
		logs = append(logs, newOpLog(op, "", now, entity.OpTypeUpdateIp, domainName, strings.Join(parts, "; ")))
	}
	if l := buildManagerLog(domainName, oldManager, newManager, op, now); l != nil {
		logs = append(logs, l)
	}
	return logs
}
