package domain

import (
	"bk-dnsapi/internal/dao"
	"bk-dnsapi/internal/domain/entity"
	"fmt"
	"time"

	"github.com/go-mesh/openlogging"
	"github.com/jinzhu/gorm"
)

// DnsConfigRepo dns_config接口方法
type DnsConfigRepo interface {
	Get(map[string]interface{}) ([]interface{}, error)
	Update(name string, value map[string]interface{}) (rowsAffected int64, err error)
	UpdateLaseUpdateTime() (rowsAffected int64, err error)
}

// DnsConfigImpl dns_config实现类
type DnsConfigImpl struct {
}

// DnsDomainResource 构造类
func DnsConfigResource() DnsConfigRepo {
	return &DnsConfigImpl{}
}

// Get 查询
func (dci *DnsConfigImpl) Get(query map[string]interface{}) (
	[]interface{}, error) {
	rs := []interface{}{}
	var err error
	where := "1 = 1"
	for k, v := range query {
		where = fmt.Sprintf("%s and %s = '%s' ", where, k, v)
	}

	q := fmt.Sprintf("select * from %s where %s", new(entity.TbDnsConfig).TableName(), where)
	openlogging.Info(fmt.Sprintf("query sql is [%+v]", q))
	var l []entity.TbDnsConfig
	if err := dao.DnsDB.Raw(q).Scan(&l).Error; err == nil || entity.IsNoRowFoundError(err) {
		for _, v := range l {
			rs = append(rs, v)
		}
		return rs, nil
	}

	return rs, err
}

// UpdateLaseUpdateTime 更新最后修改时间，多个地方需要，所以单独封装一下
func (dci *DnsConfigImpl) UpdateLaseUpdateTime() (rowsAffected int64, err error) {
	return dci.Update("last_modified_time", map[string]interface{}{
		"paravalue": time.Now().Format("2006-01-02 15:04:05")})
}

// Update 更新
func (dci *DnsConfigImpl) Update(name string, values map[string]interface{}) (rowsAffected int64, err error) {
	var c entity.TbDnsConfig
	if values["update_counter"] == nil {
		values["update_counter"] = gorm.Expr("update_counter + ?", 1)
	}
	r := dao.DnsDB.Model(&c).Where("paraname = ?", name).Update(values)
	return r.RowsAffected, r.Error
}
