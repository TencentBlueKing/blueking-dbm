package domain

import (
	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/domain/entity"
	"bk-dnsapi/pkg/logger"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/jinzhu/gorm"
)

// DnsDomainMgrRepo 域名管理(新功能页面)使用的方法接口。
// 与 DnsDomainBaseRepo 的区别：写操作会同步维护 tb_dns_domain_info（管理人、更新人、更新时间），
// 并在同一个事务里写入操作日志 tb_dns_op_log（日志写入失败则整个变更回滚）；
// 原有 DnsDomainBaseRepo 的行为保持不变
type DnsDomainMgrRepo interface {
	// Insert 新增域名记录，同步域名管理人、更新人。
	// 域名原本不存在记 CREATE_DOMAIN，已存在（追加实例）记 UPDATE_IP
	Insert(d []*entity.TbDnsBase, op OpContext) (num int64, err error)
	// Delete 删除记录。域名下的记录被删光记 DELETE_DOMAIN，否则记 UPDATE_IP
	Delete(tableName, app, domainName string, bkCloudId int64, ins []string, op OpContext) (
		rowsAffected int64, err error)
	// SyncDomains 按“更新后应保留的实例列表”同步域名，整批在一个事务里。
	// 列表中没有的现有实例会被删除，现有记录中没有的实例会被新增；列表为空则实例不变。
	// 各域名 manager 非空时覆盖该域名管理人（已规范化，多个用逗号分隔），空则不改。
	// 传了 remark 时覆盖域名维度的备注（tb_dns_domain_info.remark），不改 tb_dns_base 中记录的备注。
	// 实例有增删记 UPDATE_IP，管理人有变化记 UPDATE_MANAGER，备注有变化记 UPDATE_REMARK
	SyncDomains(app string, bkCloudId int64, ps []SyncDomainParam, op OpContext) ([]SyncDomainResult, error)
	Search(q DomainSearchQuery) (rs []DomainSearchResult, total int64, err error)
}

// DomainSearchResult 域名检索结果，一行一个域名。
// manager、remark、updater、update_time 取自 tb_dns_domain_info；没有记录时 manager 取 tb_dns_base 中的管理人，
// remark、updater 为空，update_time 取该域名下记录 last_change_time 的最大值。不读取 tb_dns_base 的备注
type DomainSearchResult struct {
	DomainName string `json:"domain_name"`
	// DomainType 维护方式。0:集群托管 1:自主维护
	DomainType int64 `json:"domain_type"`
	// Instances 域名对应的实例列表，ip#port 格式，无端口时为 ip#0
	Instances  []string  `json:"instances" gorm:"-"`
	Manager    string    `json:"manager"`
	Updater    string    `json:"updater"`
	UpdateTime time.Time `json:"update_time"`
	App        string    `json:"app"`
	BkCloudId  int64     `json:"bk_cloud_id"`
	Remark     string    `json:"remark"`
}

// DomainSearchQuery 域名检索条件
type DomainSearchQuery struct {
	// DomainName 域名，模糊匹配
	DomainName string
	// DomainType 维护方式，nil表示不过滤。0:集群托管 1:自主维护
	DomainType *int64
	// Manager 负责人，精确匹配
	Manager string
	Limit   int
	Offset  int
}

// DomainInstance 域名下的实例，无端口时 Port 为 0
type DomainInstance struct {
	Ip   string
	Port int
}

// String 返回 ip#port 格式
func (d DomainInstance) String() string {
	return fmt.Sprintf("%s#%d", d.Ip, d.Port)
}

// SyncDomainParam 单个域名的同步参数
type SyncDomainParam struct {
	DomainName string
	// Instances 更新后应保留的实例。为空表示实例不变
	Instances []DomainInstance
	// Manager 域名管理人，已规范化。为空表示不修改
	Manager string
	// Remark 域名备注（保存在 tb_dns_domain_info）。nil 表示不修改，空串表示清空
	Remark *string
}

// SyncDomainResult 单个域名的同步结果
type SyncDomainResult struct {
	DomainName     string   `json:"domain_name"`
	Added          []string `json:"added"`
	Removed        []string `json:"removed"`
	ManagerUpdated bool     `json:"manager_updated"`
	RemarkUpdated  bool     `json:"remark_updated"`
}

// DnsDomainMgrImpl DnsDomainMgrRepo 的实现
type DnsDomainMgrImpl struct {
}

// DnsDomainMgrResource 域名管理表构建类
func DnsDomainMgrResource() DnsDomainMgrRepo {
	return &DnsDomainMgrImpl{}
}

// prepareDomainInfoForInsert 新增域名前，同步 tb_dns_domain_info，返回每个域名在本次新增前是否不存在。
// 域名在 tb_dns_base 中还不存在：新建域名，写入管理人、备注，更新人=操作人（没有则取管理人，已存在的旧记录会被覆盖）。
// 域名已存在：只是追加实例，管理人、备注保持不变，仅刷新更新人和更新时间
func prepareDomainInfoForInsert(tx *gorm.DB, dnsList []*entity.TbDnsBase, op OpContext) (
	isNew map[string]bool, err error) {
	isNew = map[string]bool{}
	done := map[string]bool{}
	for _, l := range dnsList {
		if done[l.DomainName] {
			continue
		}
		done[l.DomainName] = true

		manager := normalizeManagers(l.Manager)
		updater := op.operatorOr(manager)
		var cnt int64
		if err = tx.Model(&entity.TbDnsBase{}).Where("domain_name = ?", l.DomainName).Count(&cnt).Error; err != nil {
			return nil, err
		}
		if cnt == 0 {
			isNew[l.DomainName] = true
			if err = upsertDomainInfo(tx, l.DomainName, manager, l.Remark, updater); err != nil {
				return nil, err
			}
			continue
		}
		if err = ensureAndTouchDomainInfo(tx, l.DomainName, updater); err != nil {
			return nil, err
		}
	}
	return isNew, nil
}

// Insert 插入域名
func (m *DnsDomainMgrImpl) Insert(dnsList []*entity.TbDnsBase, op OpContext) (num int64, err error) {
	tx := dao.DnsDB.Begin()
	isNew, err := prepareDomainInfoForInsert(tx, dnsList, op)
	if err != nil {
		tx.Rollback()
		return 0, err
	}
	for _, l := range dnsList {
		logger.Info(fmt.Sprintf("insert op:[%+v]", l))
		r := tx.Create(&l)
		if r.Error != nil {
			tx.Rollback()
			return 0, r.Error
		}
		num += r.RowsAffected
	}
	if err = writeOpLogs(tx, buildInsertLogs(dnsList, isNew, op, time.Now())); err != nil {
		tx.Rollback()
		return 0, err
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return
}

// Delete 删除域名
func (m *DnsDomainMgrImpl) Delete(tableName, app, domainName string, bkCloudId int64,
	ins []string, op OpContext) (rowsAffected int64, err error) {
	where := "app = ? and bk_cloud_id = ?"
	args := []interface{}{app, bkCloudId}
	if domainName != "" {
		where = fmt.Sprintf("%s and domain_name = ?", where)
		args = append(args, domainName)
	}
	if len(ins) != 0 {
		var insList, ipList []string
		for _, i := range ins {
			if strings.HasSuffix(i, "#0") {
				ipList = append(ipList, strings.Split(i, "#")[0])
			} else {
				insList = append(insList, i)
			}
		}
		where = fmt.Sprintf("%s and  (concat(ip,'#',port) in (?) or ip in (?))", where)
		args = append(args, insList, ipList)
	} else {
		where = "domain_name = ? and app = ? and bk_cloud_id = ?"
		args = []interface{}{domainName, app, bkCloudId}
	}
	logger.Info(fmt.Sprintf("delete from %s where %s, args:[%+v]", tableName, where, args))

	tx := dao.DnsDB.Begin()
	// 删除前先查出将被删除的记录：用于补全这些域名在 tb_dns_domain_info 中缺失的记录（保留历史管理人），
	// 以及写操作日志
	var records []entity.TbDnsBase
	if err = tx.Table(tableName).Set("gorm:query_option", "FOR UPDATE").Where(where, args...).
		Order("uid asc").Find(&records).Error; err != nil {
		tx.Rollback()
		return 0, err
	}
	var domains []string
	seen := map[string]bool{}
	for _, r := range records {
		if !seen[r.DomainName] {
			seen[r.DomainName] = true
			domains = append(domains, r.DomainName)
		}
	}
	for _, d := range domains {
		if err = ensureDomainInfo(tx, d); err != nil {
			tx.Rollback()
			return 0, err
		}
	}

	r := tx.Exec(fmt.Sprintf("delete from %s where %s", tableName, where), args...)
	if r.Error != nil {
		tx.Rollback()
		return 0, r.Error
	}
	if r.RowsAffected > 0 && len(domains) > 0 {
		updater := op.operatorOr("")
		for _, d := range domains {
			if err = touchDomainInfo(tx, d, updater); err != nil {
				tx.Rollback()
				return 0, err
			}
		}
		// 删除后各域名剩余的记录数，没有剩余的域名不会出现在结果里（即为 0）
		type cntRow struct {
			DomainName string
			Cnt        int64
		}
		var rows []cntRow
		if err = tx.Table(tableName).Select("domain_name, count(*) as cnt").
			Where("domain_name in (?)", domains).Group("domain_name").Scan(&rows).Error; err != nil {
			tx.Rollback()
			return 0, err
		}
		remaining := make(map[string]int64, len(rows))
		for _, row := range rows {
			remaining[row.DomainName] = row.Cnt
		}
		if err = writeOpLogs(tx, buildDeleteLogs(records, remaining, op, time.Now())); err != nil {
			tx.Rollback()
			return 0, err
		}
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return r.RowsAffected, nil
}

// diffInstances 对比现有记录和期望实例，返回需要新增的实例、需要删除的记录。结果保持输入顺序
func diffInstances(existing []entity.TbDnsBase, want []DomainInstance) (toAdd []DomainInstance,
	toDel []entity.TbDnsBase) {
	wantSet := make(map[DomainInstance]bool, len(want))
	for _, w := range want {
		wantSet[w] = true
	}
	existSet := make(map[DomainInstance]bool, len(existing))
	for _, e := range existing {
		k := DomainInstance{Ip: e.Ip, Port: e.Port}
		existSet[k] = true
		if !wantSet[k] {
			toDel = append(toDel, e)
		}
	}
	added := map[DomainInstance]bool{}
	for _, w := range want {
		if !existSet[w] && !added[w] {
			added[w] = true
			toAdd = append(toAdd, w)
		}
	}
	return toAdd, toDel
}

func instanceStrings(ins []DomainInstance) []string {
	rs := make([]string, 0, len(ins))
	for _, i := range ins {
		rs = append(rs, i.String())
	}
	return rs
}

// SyncDomains 按“更新后应保留的实例列表”同步域名。
// 域名在 app + bk_cloud_id 下没有任何记录时报错，不会新建域名。
// 有实际变更（增删实例、传了 manager、备注有变化）时，同步刷新 tb_dns_domain_info 的更新人、更新时间，并写操作日志
func (m *DnsDomainMgrImpl) SyncDomains(app string, bkCloudId int64, ps []SyncDomainParam, op OpContext) (
	results []SyncDomainResult, err error) {
	tx := dao.DnsDB.Begin()
	updater := op.operatorOr("")
	results = make([]SyncDomainResult, 0, len(ps))

	for _, p := range ps {
		var existing []entity.TbDnsBase
		if err = tx.Set("gorm:query_option", "FOR UPDATE").
			Where("app = ? and bk_cloud_id = ? and domain_name = ?", app, bkCloudId, p.DomainName).
			Order("uid asc").Find(&existing).Error; err != nil {
			tx.Rollback()
			return nil, err
		}
		if len(existing) == 0 {
			tx.Rollback()
			return nil, fmt.Errorf("domain[%s] not found, app[%s] bk_cloud_id[%d]", p.DomainName, app, bkCloudId)
		}

		res := SyncDomainResult{DomainName: p.DomainName, Added: []string{}, Removed: []string{}}
		var toAdd []DomainInstance
		var toDel []entity.TbDnsBase
		if len(p.Instances) > 0 {
			toAdd, toDel = diffInstances(existing, p.Instances)
		}
		logger.Info(fmt.Sprintf("sync domain[%s] app[%s] want[%v] add[%v] del count[%d] manager[%s] remark[%v]",
			p.DomainName, app, p.Instances, toAdd, len(toDel), p.Manager, p.Remark))

		changed := len(toAdd) > 0 || len(toDel) > 0
		// 没有传 manager、remark 且实例无变化：不需要读写 tb_dns_domain_info
		if !changed && p.Manager == "" && p.Remark == nil {
			results = append(results, res)
			continue
		}
		// 先补全域名信息，保留历史管理人和备注；必须在删除记录之前
		if err = ensureDomainInfo(tx, p.DomainName); err != nil {
			tx.Rollback()
			return nil, err
		}
		info, err2 := getDomainInfo(tx, p.DomainName)
		if err2 != nil {
			tx.Rollback()
			return nil, err2
		}
		managerChanged := p.Manager != "" && p.Manager != info.Manager
		remarkChanged := p.Remark != nil && *p.Remark != info.Remark
		// 实例没变化、管理人和备注也与现有相同：不写库、不写日志
		if !changed && !managerChanged && !remarkChanged {
			results = append(results, res)
			continue
		}
		oldManager := info.Manager

		if len(toDel) > 0 {
			uids := make([]int64, 0, len(toDel))
			for _, d := range toDel {
				uids = append(uids, d.Uid)
				res.Removed = append(res.Removed, DomainInstance{Ip: d.Ip, Port: d.Port}.String())
			}
			if err = tx.Exec("delete from tb_dns_base where uid in (?)", uids).Error; err != nil {
				tx.Rollback()
				return nil, err
			}
		}
		// 新增的实例沿用该域名已有记录的备注、维护方式、状态等
		tpl := existing[0]
		now := time.Now()
		for _, a := range toAdd {
			t := &entity.TbDnsBase{
				App:            app,
				DomainName:     p.DomainName,
				Ip:             a.Ip,
				Port:           a.Port,
				StartTime:      now,
				LastChangeTime: now,
				Manager:        tpl.Manager,
				Remark:         tpl.Remark,
				DnsStr:         tpl.DnsStr,
				Status:         tpl.Status,
				DomainType:     tpl.DomainType,
				BkCloudId:      bkCloudId,
			}
			if err = tx.Create(t).Error; err != nil {
				tx.Rollback()
				return nil, err
			}
			res.Added = append(res.Added, a.String())
		}

		if err = applyDomainInfoChange(tx, p.DomainName, updater, p.Manager, p.Remark); err != nil {
			tx.Rollback()
			return nil, err
		}
		logs := buildSyncLogs(p.DomainName, res.Added, res.Removed, oldManager, p.Manager, op, now)
		if remarkChanged {
			if l := buildRemarkLog(p.DomainName, info.Remark, *p.Remark, op, now); l != nil {
				logs = append(logs, l)
			}
		}
		if err = writeOpLogs(tx, logs); err != nil {
			tx.Rollback()
			return nil, err
		}
		res.ManagerUpdated = managerChanged
		res.RemarkUpdated = remarkChanged
		results = append(results, res)
	}
	if err = tx.Commit().Error; err != nil {
		return nil, err
	}
	return results, nil
}

// escapeLike 转义 LIKE 通配符，使用户输入按字面值匹配
func escapeLike(s string) string {
	return strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`).Replace(s)
}

// attachInstances 把实例记录按域名挂到检索结果上，实例按 ip、port 排序；没有记录的域名返回空数组
func attachInstances(rs []DomainSearchResult, records []entity.TbDnsBase) {
	byDomain := make(map[string][]entity.TbDnsBase, len(rs))
	for _, r := range records {
		byDomain[r.DomainName] = append(byDomain[r.DomainName], r)
	}
	for i := range rs {
		recs := byDomain[rs[i].DomainName]
		sort.SliceStable(recs, func(a, b int) bool {
			if recs[a].Ip != recs[b].Ip {
				return recs[a].Ip < recs[b].Ip
			}
			return recs[a].Port < recs[b].Port
		})
		rs[i].Instances = make([]string, 0, len(recs))
		for _, r := range recs {
			rs[i].Instances = append(rs[i].Instances, DomainInstance{Ip: r.Ip, Port: r.Port}.String())
		}
	}
}

// Search 按域名(模糊)、维护方式、负责人检索域名，一行一个域名，按域名升序。total 为满足条件的域名个数。
// 只读，不会补全 tb_dns_domain_info。
// 负责人过滤作用于生效的 manager（有 tb_dns_domain_info 记录取该表，否则取 tb_dns_base 中的管理人），
// 多个管理人以逗号分隔，命中任意一个即可。
// 维护方式过滤作用于该域名的 domain_type；同一域名下记录的维护方式不一致时取最大值
func (m *DnsDomainMgrImpl) Search(q DomainSearchQuery) (rs []DomainSearchResult, total int64, err error) {
	rs = []DomainSearchResult{}
	where, having := "1 = 1", "1 = 1"
	var whereArgs, havingArgs []interface{}
	if q.DomainName != "" {
		where += " and b.domain_name like ?"
		whereArgs = append(whereArgs, "%"+escapeLike(q.DomainName)+"%")
	}
	if q.DomainType != nil {
		having += " and max(b.domain_type) = ?"
		havingArgs = append(havingArgs, *q.DomainType)
	}
	if q.Manager != "" {
		having += " and find_in_set(?, coalesce(i.manager, min(b.manager))) > 0"
		havingArgs = append(havingArgs, q.Manager)
	}
	logger.Info(fmt.Sprintf("search domain. params[%+v]", q))

	from := "from tb_dns_base b left join tb_dns_domain_info i on i.domain_name = b.domain_name " +
		"where " + where + " group by b.domain_name, i.manager, i.remark, i.updater, i.update_time having " + having
	args := append(append([]interface{}{}, whereArgs...), havingArgs...)

	if err = dao.DnsDB.Raw("select count(*) from (select b.domain_name "+from+") t", args...).
		Row().Scan(&total); err != nil {
		return rs, 0, err
	}
	if total == 0 {
		return rs, 0, nil
	}

	listSQL := "select b.domain_name, max(b.domain_type) as domain_type, " +
		"coalesce(i.manager, min(b.manager)) as manager, coalesce(i.updater, '') as updater, " +
		"coalesce(i.update_time, max(b.last_change_time)) as update_time, " +
		"min(b.app) as app, min(b.bk_cloud_id) as bk_cloud_id, coalesce(i.remark, '') as remark " +
		from + " order by b.domain_name asc limit ? offset ?"
	listArgs := append(append([]interface{}{}, args...), q.Limit, q.Offset)
	if err = dao.DnsDB.Raw(listSQL, listArgs...).Scan(&rs).Error; err != nil {
		return []DomainSearchResult{}, 0, err
	}
	if len(rs) == 0 {
		return rs, total, nil
	}

	names := make([]string, 0, len(rs))
	for _, r := range rs {
		names = append(names, r.DomainName)
	}
	var records []entity.TbDnsBase
	if err = dao.DnsDB.Where("domain_name in (?)", names).Find(&records).Error; err != nil {
		return []DomainSearchResult{}, 0, err
	}
	attachInstances(rs, records)
	return rs, total, nil
}
