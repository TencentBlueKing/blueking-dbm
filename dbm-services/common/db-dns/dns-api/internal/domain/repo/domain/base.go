package domain

import (
	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/domain/entity"
	"fmt"
	"reflect"
	"strings"

	"bk-dnsapi/pkg/logger"
)

// DnsDomainBaseRepo dns_base方法接口
type DnsDomainBaseRepo interface {
	Get(map[string]interface{}, []string) ([]interface{}, error)
	Insert(d []*entity.TbDnsBase) (num int64, err error)
	Delete(tableName, app, domainName string, bkCloudId int64, ins []string) (rowsAffected int64, err error)
	Update(d *entity.TbDnsBase, newIP string, newPort int) (rowsAffected int64, err error)
	UpdateDomainBatch(bs []UpdateBatchDnsBase) (rowsAffected int64, err error)
	UpdateFieldsByDomain(app string, bkCloudId int64, value map[string]interface{}) (rowsAffected int64, err error)
}

// DnsDomainBaseImpl dns_base方法实现
type DnsDomainBaseImpl struct {
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

// Insert 插入域名
func (base *DnsDomainBaseImpl) Insert(dnsList []*entity.TbDnsBase) (num int64, err error) {
	tx := dao.DnsDB.Begin()
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
	ins []string) (rowsAffected int64, err error) {
	execSql := fmt.Sprintf("delete from %s where  app = ? and bk_cloud_id = ?", tableName)
	args := []interface{}{app, bkCloudId}
	if domainName != "" {
		execSql = fmt.Sprintf("%s and domain_name = ?", execSql)
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
		execSql = fmt.Sprintf("%s and  (concat(ip,'#',port) in (?) or ip in (?))", execSql)
		args = append(args, insList, ipList)
	} else {
		execSql = fmt.Sprintf("delete from %s where  domain_name = ? and app = ? and bk_cloud_id = ?", tableName)
		args = []interface{}{domainName, app, bkCloudId}
	}
	logger.Info(fmt.Sprintf("delete sql:[%+v], args:[%+v]", execSql, args))
	r := dao.DnsDB.Exec(execSql, args...)

	if r.Error != nil {
		return 0, r.Error
	}
	return r.RowsAffected, nil
}

// Update 更新单个域名
func (base *DnsDomainBaseImpl) Update(d *entity.TbDnsBase, newIP string, newPort int) (rowsAffected int64, err error) {
	logger.Info(fmt.Sprintf("update op:{[%+v], newIp:%+v, nowPort:%+v}", d, newIP, newPort))
	r := dao.DnsDB.Model(d).Update(map[string]interface{}{"ip": newIP, "port": newPort})
	return r.RowsAffected, r.Error
}

// UpdateDomainBatch 批量更新域名
func (base *DnsDomainBaseImpl) UpdateDomainBatch(bs []UpdateBatchDnsBase) (rowsAffected int64, err error) {
	rowsAffected = 0
	tx := dao.DnsDB.Begin()

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
	}
	if err = tx.Commit().Error; err != nil {
		return 0, err
	}
	return
}

// UpdateFieldsByDomain 根据域名和bkID更新对应字段
func (base *DnsDomainBaseImpl) UpdateFieldsByDomain(name string, bkCloudId int64, values map[string]interface{}) (
	rowsAffected int64, err error) {
	var c entity.TbDnsBase
	r := dao.DnsDB.Model(&c).Where("domain_name = ? and bk_cloud_id = ? ", name, bkCloudId).Update(values)
	return r.RowsAffected, r.Error
}
