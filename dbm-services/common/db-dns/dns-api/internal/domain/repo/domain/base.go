package domain

import (
	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/domain/entity"
	"fmt"
	"reflect"
	"strings"
	"time"

	"bk-dnsapi/pkg/logger"

	"github.com/jinzhu/gorm"
)

// DnsDomainBaseRepo dns_base方法接口
type DnsDomainBaseRepo interface {
	Get(map[string]interface{}, []string) ([]interface{}, error)
	Insert(d []*entity.TbDnsBase) (num int64, err error)
	// Delete operator 为更新人，空则取默认值
	Delete(tableName, app, domainName string, bkCloudId int64, ins []string, operator string) (
		rowsAffected int64, err error)
	Update(d *entity.TbDnsBase, newIP string, newPort int) (rowsAffected int64, err error)
	// UpdateDomainBatch operator 为更新人；manager 非空时同时覆盖域名管理人（已规范化，多个用逗号分隔），空则不改
	UpdateDomainBatch(bs []UpdateBatchDnsBase, operator, manager string) (rowsAffected int64, err error)
	// UpdateFieldsByDomain operator、manager 含义同 UpdateDomainBatch
	UpdateFieldsByDomain(app string, bkCloudId int64, value map[string]interface{}, operator, manager string) (
		rowsAffected int64, err error)
	Search(q DomainSearchQuery) (rs []DomainSearchResult, total int64, err error)
}

// DomainSearchResult 域名检索结果。manager 为 tb_dns_domain_info 中的域名管理人(覆盖 tb_dns_base.manager)
type DomainSearchResult struct {
	entity.TbDnsBase
	Updater    string    `json:"updater"`
	UpdateTime time.Time `json:"update_time"`
}

// DnsDomainBaseImpl dns_base方法实现
type DnsDomainBaseImpl struct {
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

// UpdateBatchDnsBase 批量update参数
type UpdateBatchDnsBase struct {
	App        string
	DomainName string
	OIp        string
	OPort      int
	NIp        string
	NPort      int
	BkCloudId  int64
}

// DnsDomainResource dns表构建类
func DnsDomainResource() DnsDomainBaseRepo {
	return &DnsDomainBaseImpl{}
}

// Get 查询域名
func (base *DnsDomainBaseImpl) Get(query map[string]interface{}, fields []string) (
	[]interface{}, error) {
	rs := []interface{}{}
	var err error
	where := "1 = 1"
	args := []interface{}{}
	for k, v := range query {
		if k == "ins" || k == "ip" {
			continue
		}
		switch v.(type) {
		case []string:
			if len(v.([]string)) != 0 {
				where = fmt.Sprintf("%s and %s in (?)", where, k)
				args = append(args, v.([]string))
			}
		case string:
			where = fmt.Sprintf("%s and %s = ? ", where, k)
			args = append(args, v)
		default:
			continue
		}
	}
	var insList, ipList []string
	if ins, _ok := query["ins"].([]string); _ok {
		insList = ins
	}
	if ip, _ok := query["ip"].([]string); _ok {
		ipList = ip
	}
	if len(insList) != 0 || len(ipList) != 0 {
		where = fmt.Sprintf("%s and (ip in (?) or concat(ip,'#',port) in (?))", where)
		args = append(args, ipList, insList)
	}

	q := fmt.Sprintf("select * from %s where %s", new(entity.TbDnsBase).TableName(), where)
	logger.Info(fmt.Sprintf("query sql is [%+v], args[%+v]", q, args))
	var l []entity.TbDnsBase
	if err := dao.DnsDB.Raw(q, args...).Scan(&l).Error; err == nil || entity.IsNoRowFoundError(err) {
		// rs = append(rs, l)
		if len(fields) == 0 {
			for _, v := range l {
				rs = append(rs, v)
			}
		} else {
			// trim unused fields
			for _, v := range l {
				m := make(map[string]interface{})
				val := reflect.ValueOf(v)
				s := reflect.TypeOf(&v).Elem()
				for _, fname := range fields {
					for i := 0; i < s.NumField(); i++ {
						if s.Field(i).Tag.Get("json") == fname {
							m[fname] = val.FieldByName(s.Field(i).Name).Interface()
						}
					}
				}
				rs = append(rs, m)
			}
		}
		return rs, nil
	}

	return rs, err
}

// prepareDomainInfoForInsert 新增域名前，同步 tb_dns_domain_info。
// 域名在 tb_dns_base 中还不存在：新建域名，写入管理人，更新人=管理人（已存在的旧记录会被覆盖）。
// 域名已存在：只是追加实例，管理人保持不变，仅刷新更新人和更新时间
func prepareDomainInfoForInsert(tx *gorm.DB, dnsList []*entity.TbDnsBase) error {
	done := map[string]bool{}
	for _, l := range dnsList {
		if done[l.DomainName] {
			continue
		}
		done[l.DomainName] = true

		manager := normalizeManagers(l.Manager)
		updater := resolveUpdater(manager, "")
		var cnt int64
		if err := tx.Model(&entity.TbDnsBase{}).Where("domain_name = ?", l.DomainName).Count(&cnt).Error; err != nil {
			return err
		}
		if cnt == 0 {
			if err := upsertDomainInfo(tx, l.DomainName, manager, updater); err != nil {
				return err
			}
			continue
		}
		if err := ensureAndTouchDomainInfo(tx, l.DomainName, updater); err != nil {
			return err
		}
	}
	return nil
}

// Insert 插入域名
func (base *DnsDomainBaseImpl) Insert(dnsList []*entity.TbDnsBase) (num int64, err error) {
	tx := dao.DnsDB.Begin()
	if err = prepareDomainInfoForInsert(tx, dnsList); err != nil {
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
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return
}

// Delete 删除域名
func (base *DnsDomainBaseImpl) Delete(tableName, app, domainName string, bkCloudId int64,
	ins []string, operator string) (rowsAffected int64, err error) {
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
	// 删除会影响哪些域名：删除前查出来，并补全这些域名在 tb_dns_domain_info 中缺失的记录，保留历史管理人
	var domains []string
	if err = tx.Table(tableName).Where(where, args...).Pluck("distinct domain_name", &domains).Error; err != nil {
		tx.Rollback()
		return 0, err
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
	if r.RowsAffected > 0 {
		updater := resolveUpdater(operator, "")
		for _, d := range domains {
			if err = touchDomainInfo(tx, d, updater); err != nil {
				tx.Rollback()
				return 0, err
			}
		}
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return r.RowsAffected, nil
}

// Update 更新单个域名
func (base *DnsDomainBaseImpl) Update(d *entity.TbDnsBase, newIP string, newPort int) (rowsAffected int64, err error) {
	logger.Info(fmt.Sprintf("update op:{[%+v], newIp:%+v, nowPort:%+v}", d, newIP, newPort))
	r := dao.DnsDB.Model(d).Update(map[string]interface{}{"ip": newIP, "port": newPort})
	return r.RowsAffected, r.Error
}

// UpdateDomainBatch 批量更新域名。manager 非空时，同时覆盖本次涉及域名的管理人
func (base *DnsDomainBaseImpl) UpdateDomainBatch(bs []UpdateBatchDnsBase, operator, manager string) (
	rowsAffected int64, err error) {
	rowsAffected = 0
	tx := dao.DnsDB.Begin()
	updater := resolveUpdater(operator, "")
	touched := map[string]bool{}

	for _, b := range bs {
		logger.Info(fmt.Sprintf("update op:{[%+v]}", b))
		r := tx.Model(&entity.TbDnsBase{}).Where("app = ? and bk_cloud_id = ?", b.App, b.BkCloudId).
			Where("domain_name = ? and ip = ? and port = ?", b.DomainName, b.OIp, b.OPort).
			Update(map[string]interface{}{"ip": b.NIp, "port": b.NPort})
		if r.Error != nil {
			tx.Rollback()
			return 0, r.Error
		}
		rowsAffected += r.RowsAffected
		if r.RowsAffected > 0 && !touched[b.DomainName] {
			touched[b.DomainName] = true
			if err = applyDomainInfoChange(tx, b.DomainName, updater, manager); err != nil {
				tx.Rollback()
				return 0, err
			}
		}
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return
}

// escapeLike 转义 LIKE 通配符，使用户输入按字面值匹配
func escapeLike(s string) string {
	return strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`).Replace(s)
}

// Search 按域名(模糊)、维护方式、负责人检索域名记录。total 为满足条件的总条数。
// 只读，不会补全 tb_dns_domain_info：有记录则 manager、updater、update_time 取自该表；
// 没有记录则 manager 取 tb_dns_base.manager，updater 为空，update_time 取 last_change_time。
// 负责人过滤作用于上述生效的 manager（多个管理人以逗号分隔，命中任意一个即可）
func (base *DnsDomainBaseImpl) Search(q DomainSearchQuery) (rs []DomainSearchResult, total int64, err error) {
	rs = []DomainSearchResult{}
	db := dao.DnsDB.Table("tb_dns_base b").
		Joins("left join tb_dns_domain_info i on i.domain_name = b.domain_name")
	if q.DomainName != "" {
		db = db.Where("b.domain_name like ?", "%"+escapeLike(q.DomainName)+"%")
	}
	if q.DomainType != nil {
		db = db.Where("b.domain_type = ?", *q.DomainType)
	}
	if q.Manager != "" {
		db = db.Where("find_in_set(?, coalesce(i.manager, b.manager)) > 0", q.Manager)
	}
	logger.Info(fmt.Sprintf("search domain. params[%+v]", q))

	if err = db.Count(&total).Error; err != nil {
		return rs, 0, err
	}
	err = db.Select("b.uid, b.app, b.domain_name, b.ip, b.port, b.start_time, b.last_change_time, " +
		"coalesce(i.manager, b.manager) as manager, b.remark, b.dns_str, b.status, b.domain_type, b.bk_cloud_id, " +
		"coalesce(i.updater, '') as updater, coalesce(i.update_time, b.last_change_time) as update_time").
		Order("b.uid asc").Limit(q.Limit).Offset(q.Offset).Scan(&rs).Error
	return rs, total, err
}

// UpdateFieldsByDomain 根据域名和bkID更新对应字段，并同步更新域名的更新人、更新时间；manager 非空时同时更新管理人
func (base *DnsDomainBaseImpl) UpdateFieldsByDomain(name string, bkCloudId int64, values map[string]interface{},
	operator, manager string) (rowsAffected int64, err error) {
	tx := dao.DnsDB.Begin()
	var c entity.TbDnsBase
	r := tx.Model(&c).Where("domain_name = ? and bk_cloud_id = ? ", name, bkCloudId).Update(values)
	if r.Error != nil {
		tx.Rollback()
		return 0, r.Error
	}
	// 传了 manager 时，即使 app 没变化（影响行数为 0）也要更新管理人。调用方已校验过域名记录存在
	if r.RowsAffected > 0 || manager != "" {
		if err = applyDomainInfoChange(tx, name, resolveUpdater(operator, ""), manager); err != nil {
			tx.Rollback()
			return 0, err
		}
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return r.RowsAffected, nil
}
