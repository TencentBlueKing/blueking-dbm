package domain

import (
	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/domain/entity"
	"fmt"
	"reflect"
	"strings"

	"github.com/go-mesh/openlogging"
)

// DnsDomainBaseRepo dns_base方法接口
type DnsDomainBaseRepo interface {
	Get(map[string]interface{}, []string) ([]interface{}, error)
	Insert(d []*entity.TbDnsBase) (num int64, err error)
	Delete(tableName, app, domainName string, bkCloudId int64, ins []string) (rowsAffected int64, err error)
	Update(d *entity.TbDnsBase, newIP string, newPort int) (rowsAffected int64, err error)
	UpdateDomainBatch(bs []UpdateBatchDnsBase) (rowsAffected int64, err error)
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
	for k, v := range query {
		if k == "ins" || k == "ip" {
			continue
		}
		switch v.(type) {
		case []string:
			if len(v.([]string)) != 0 {
				t := ""
				for _, tv := range v.([]string) {
					t = fmt.Sprintf("%s,'%s'", t, tv)
				}
				t = strings.Trim(t, ",")
				where = fmt.Sprintf("%s and %s in (%s)", where, k, t)
			}
		case string:
			where = fmt.Sprintf("%s and %s = '%s' ", where, k, v)
		default:
			continue
		}
	}
	insStr := "''"
	ipStr := "''"
	if ins, _ok := query["ins"]; _ok {
		insStr = "'" + strings.Join(ins.([]string), "','") + "'"
	}
	if ip, _ok := query["ip"]; _ok {
		ipStr = "'" + strings.Join(ip.([]string), "','") + "'"
	}
	if insStr != "''" || ipStr != "''" {
		where = fmt.Sprintf("%s and (ip in (%s) or concat(ip,'#',port) in (%s))", where, ipStr, insStr)
	}

	q := fmt.Sprintf("select * from %s where %s", new(entity.TbDnsBase).TableName(), where)
	openlogging.Info(fmt.Sprintf("query sql is [%+v]", q))
	var l []entity.TbDnsBase
	if err := dao.DnsDB.Raw(q).Scan(&l).Error; err == nil || entity.IsNoRowFoundError(err) {
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
	execSql := fmt.Sprintf("delete from %s where  app = '%s' and bk_cloud_id = '%d'",
		tableName, app, bkCloudId)
	if domainName != "" {
		execSql = fmt.Sprintf("%s and domain_name = '%s'", execSql, domainName)
	}
	if len(ins) != 0 {
		insStr := "''"
		ipStr := "''"
		for _, i := range ins {
			if strings.HasSuffix(i, "#0") {
				ip := strings.Split(i, "#")[0]
				ipStr = fmt.Sprintf("%s,'%s'", ipStr, ip)
			} else {
				insStr = fmt.Sprintf("%s,'%s'", insStr, i)
			}

		}
		insStr = strings.Trim(insStr, ",")
		ipStr = strings.Trim(ipStr, ",")
		execSql = fmt.Sprintf("%s and  (concat(ip,'#',port) in (%s) or ip in (%s))",
			execSql, insStr, ipStr)
	} else {
		execSql = fmt.Sprintf("delete from %s where  domain_name = '%s' and app = '%s' and bk_cloud_id ='%d'",
			tableName, domainName, app, bkCloudId)
	}
	r := dao.DnsDB.Exec(execSql)

	if r.Error != nil {
		return 0, r.Error
	}
	return r.RowsAffected, nil
}

// Update 更新单个域名
func (base *DnsDomainBaseImpl) Update(d *entity.TbDnsBase, newIP string, newPort int) (rowsAffected int64, err error) {
	r := dao.DnsDB.Model(d).Update(map[string]interface{}{"ip": newIP, "port": newPort})
	return r.RowsAffected, r.Error
}

// UpdateDomainBatch 批量更新域名
func (base *DnsDomainBaseImpl) UpdateDomainBatch(bs []UpdateBatchDnsBase) (rowsAffected int64, err error) {
	rowsAffected = 0
	tx := dao.DnsDB.Begin()

	for _, b := range bs {
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
