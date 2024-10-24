package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"
	"fmt"
	"time"
)

// ModifySecurityRule 修改安全规则
func (m *SecurityRulePara) ModifySecurityRule(jsonPara string, ticket string) error {
	// 根据规则的id，修改规则内容
	if m.Id == 0 {
		return errno.RuleIdNull
	}
	// 重置为默认的规则
	if m.Reset {
		var rules []*TbSecurityRules
		id := TbSecurityRules{Id: m.Id}
		err := DB.Self.Model(&TbSecurityRules{}).Where(&id).Take(&rules).Error
		if err != nil {
			return err
		}
		// 不允许删除各个组件默认使用的密码规则
		var v2 string
		switch rules[0].Name {
		case "mongodb_password":
			v2 = MongodbRule
		case "redis_password_v2":
			v2 = RedisRule
		case "mysql_password", "tendbcluster_password", "sqlserver_password":
			v2 = MysqlSqlserverRule
		case "es_password", "kafka_password", "hdfs_password", "pulsar_password", "influxdb_password", "doris_password":
			v2 = BigDataRule
		default:
			return fmt.Errorf("not system config, can not be reset")
		}
		m.Rule = v2
	}
	updateTime := time.Now()
	rule := TbSecurityRules{Rule: m.Rule, Operator: m.Operator, UpdateTime: updateTime}
	id := TbSecurityRules{Id: m.Id}
	result := DB.Self.Model(&id).Update(&rule)
	if result.Error != nil {
		return result.Error
	}
	// 是否更新成功
	if result.RowsAffected == 0 {
		return errno.RuleNotExisted
	}
	log := PrivLog{BkBizId: 0, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: updateTime}
	AddPrivLog(log)
	return nil
}

// AddSecurityRule 添加安全规则
func (m *SecurityRulePara) AddSecurityRule(jsonPara string, ticket string) error {
	var count uint64
	// 检查是否已存在
	err := DB.Self.Model(&TbSecurityRules{}).Where(&TbSecurityRules{Name: m.Name}).
		Count(&count).Error
	if err != nil {
		return err
	}
	if count != 0 {
		return errno.RuleExisted.AddBefore(m.Name)
	}
	insertTime := time.Now()
	// 添加规则
	rule := &TbSecurityRules{Name: m.Name, Rule: m.Rule, Creator: m.Operator, CreateTime: insertTime,
		UpdateTime: insertTime}
	err = DB.Self.Model(&TbSecurityRules{}).Create(&rule).Error
	if err != nil {
		return err
	}
	AddPrivLog(PrivLog{BkBizId: 0, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: insertTime})
	return nil
}

// GetSecurityRule 查询安全规则
func (m *SecurityRulePara) GetSecurityRule() (*TbSecurityRules, error) {
	var rules []*TbSecurityRules
	// 根据规则名称查询
	if m.Name == "" {
		return nil, errno.RuleNameNull
	}
	err := DB.Self.Model(&TbSecurityRules{}).Where(&TbSecurityRules{Name: m.Name}).Scan(&rules).Error
	if err != nil {
		return nil, err
	}
	if len(rules) > 0 {
		return rules[0], nil
	}
	return nil, errno.RuleNotExisted.AddBefore(m.Name)
}

// DeleteSecurityRule 删除安全规则
func (m *SecurityRulePara) DeleteSecurityRule(jsonPara string, ticket string) error {
	var rules []*TbSecurityRules
	if m.Id == 0 {
		return errno.RuleIdNull
	}
	id := TbSecurityRules{Id: m.Id}
	err := DB.Self.Model(&TbSecurityRules{}).Where(&id).Scan(&rules).Error
	if err != nil {
		return err
	}
	system := []string{"mysql_password", "tendbcluster_password", "redis_password_v2", "es_password",
		"kafka_password", "hdfs_password", "pulsar_password", "influxdb_password",
		"sqlserver_password", "mongodb_password", "doris_password"}
	// 不允许删除各个组件默认使用的密码规则
	if len(rules) > 0 && util.HasElem(rules[0].Name, system) {
		return fmt.Errorf("system config can not be delete")
	}
	// 根据id删除
	err = DB.Self.Model(&TbSecurityRules{}).Delete(&id).Error
	if err != nil {
		return err
	}
	log := PrivLog{BkBizId: 0, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}
