package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"fmt"
	"time"
)

// ModifySecurityRule 修改安全规则
func (m *SecurityRulePara) ModifySecurityRule(jsonPara string) error {
	if m.Id == 0 {
		return errno.RuleIdNull
	}
	updateTime := time.Now()
	rule := TbSecurityRules{Name: m.Name, Rule: m.Rule, Operator: m.Operator, UpdateTime: updateTime}
	id := TbSecurityRules{Id: m.Id}
	result := DB.Self.Model(&id).Update(&rule)
	if result.Error != nil {
		return result.Error
	}
	// 是否更新
	if result.RowsAffected == 0 {
		return errno.RuleNotExisted
	}
	log := PrivLog{BkBizId: 0, Operator: m.Operator, Para: jsonPara, Time: updateTime}
	AddPrivLog(log)
	return nil
}

// AddSecurityRule 添加安全规则
func (m *SecurityRulePara) AddSecurityRule(jsonPara string) error {
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
	log := PrivLog{BkBizId: 0, Operator: m.Operator, Para: jsonPara, Time: insertTime}
	AddPrivLog(log)
	return nil
}

// GetSecurityRule 查询安全规则
func (m *SecurityRulePara) GetSecurityRule() (*TbSecurityRules, error) {
	var rules []*TbSecurityRules
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
func (m *SecurityRulePara) DeleteSecurityRule(jsonPara string) error {
	var rules []*TbSecurityRules
	if m.Id == 0 {
		return errno.RuleIdNull
	}
	id := TbSecurityRules{Id: m.Id}
	err := DB.Self.Model(&TbSecurityRules{}).Where(&id).Scan(&rules).Error
	if err != nil {
		return err
	}
	// 不允许删除密码规则，随机化默认使用的规则
	if len(rules) > 0 && rules[0].Name == "password" {
		return fmt.Errorf("system config can not be delete")
	}
	// 根据id删除
	err = DB.Self.Model(&TbSecurityRules{}).Delete(&id).Error
	if err != nil {
		return err
	}
	log := PrivLog{BkBizId: 0, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}
