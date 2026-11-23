package domain

import (
	"fmt"
	"strings"
	"time"

	"github.com/jinzhu/gorm"
)

const (
	// defaultUpdater 补全历史域名、或请求没有传 operator 时使用的更新人
	defaultUpdater = "system"
)

// normalizeManagers 管理人去空格、去重，保持顺序，英文逗号分隔
func normalizeManagers(s string) string {
	var rs []string
	seen := map[string]bool{}
	for _, m := range strings.Split(s, ",") {
		m = strings.TrimSpace(m)
		if m == "" || seen[m] {
			continue
		}
		seen[m] = true
		rs = append(rs, m)
	}
	return strings.Join(rs, ",")
}

// resolveUpdater 更新人：优先用传入的 operator，其次用 fallback，最后用默认值
func resolveUpdater(operator, fallback string) string {
	if s := strings.TrimSpace(operator); s != "" {
		return s
	}
	if s := strings.TrimSpace(fallback); s != "" {
		return s
	}
	return defaultUpdater
}

// ensureDomainInfo 补全单个域名在 tb_dns_domain_info 中缺失的记录，已存在则不处理。
// 管理人取该域名在 tb_dns_base 下所有记录管理人的并集，更新时间取 last_change_time 的最大值，更新人为 system。
// 只在写操作中调用，按域名精确匹配（走 tb_dns_base 的 domain_name 索引）；并发时由唯一索引兜底
func ensureDomainInfo(db *gorm.DB, domainName string) error {
	return db.Exec(`insert ignore into tb_dns_domain_info (domain_name, manager, updater, update_time)
select b.domain_name,
coalesce(group_concat(distinct nullif(b.manager, '') order by b.manager separator ','), ''),
?, coalesce(max(b.last_change_time), now())
from tb_dns_base b where b.domain_name = ? group by b.domain_name`,
		defaultUpdater, domainName).Error
}

// upsertDomainInfo 写入域名公共属性；已存在则覆盖管理人、更新人、更新时间
func upsertDomainInfo(db *gorm.DB, domainName, manager, updater string) error {
	return db.Exec(`insert into tb_dns_domain_info (domain_name, manager, updater, update_time) values (?, ?, ?, ?)
on duplicate key update manager = values(manager), updater = values(updater), update_time = values(update_time)`,
		domainName, manager, updater, time.Now()).Error
}

// touchDomainInfo 更新域名的更新人和更新时间。调用前需保证记录已存在（ensureDomainInfo）
func touchDomainInfo(db *gorm.DB, domainName, updater string) error {
	return db.Exec("update tb_dns_domain_info set updater = ?, update_time = ? where domain_name = ?",
		updater, time.Now(), domainName).Error
}

// ensureAndTouchDomainInfo 补全并更新域名的更新人和更新时间
func ensureAndTouchDomainInfo(db *gorm.DB, domainName, updater string) error {
	if err := ensureDomainInfo(db, domainName); err != nil {
		return err
	}
	return touchDomainInfo(db, domainName, updater)
}

// ParseManagerParam 解析更新请求中可选的管理人参数。
// 返回规范化后的管理人；未传（空串）返回空串，表示不修改。传了但不含有效管理人（如 ","）则报错
func ParseManagerParam(raw string) (string, error) {
	if strings.TrimSpace(raw) == "" {
		return "", nil
	}
	m := normalizeManagers(raw)
	if m == "" {
		return "", fmt.Errorf("manager[%s] has no valid manager", raw)
	}
	return m, nil
}

// applyDomainInfoChange 域名发生修改后同步 tb_dns_domain_info：
// 先补全缺失记录，再更新更新人、更新时间；manager 非空时同时覆盖管理人，为空则管理人不变
func applyDomainInfoChange(db *gorm.DB, domainName, updater, manager string) error {
	if err := ensureDomainInfo(db, domainName); err != nil {
		return err
	}
	if manager == "" {
		return touchDomainInfo(db, domainName, updater)
	}
	return db.Exec("update tb_dns_domain_info set manager = ?, updater = ?, update_time = ? where domain_name = ?",
		manager, updater, time.Now(), domainName).Error
}
