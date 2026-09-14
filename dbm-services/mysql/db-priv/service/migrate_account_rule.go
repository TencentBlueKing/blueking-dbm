package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// MigrateAccountRuleInDbm DBM一个业务下的集群拆分到另一个业务，账号规则也需要迁移
func (m *MigrateInDbmPara) MigrateAccountRuleInDbm(jsonPara string, ticket string) ([]string, []string, error) {
	var targetAccounts []*TbAccounts
	var sourceAccounts []*TbAccounts
	var sourceRules []*TbAccountRules
	var conflictUsers []string
	var migrateUsers []string
	var userPara string
	var userIdFilter string
	var where, checkWhere, ruleWhere string
	var dbType string
	AddPrivLog(PrivLog{BkBizId: m.TargetBiz, Ticket: ticket, Operator: "dbm_clone", Para: jsonPara, Time: time.Now()})
	if m.ClusterType == nil {
		return nil, nil, errno.ClusterTypeIsEmpty
	}
	if *m.ClusterType == tendbha || *m.ClusterType == tendbsingle {
		dbType = mysql
	} else if *m.ClusterType == tendbcluster {
		dbType = tendbcluster
	} else {
		return nil, nil, errno.NotSupportedClusterType
	}
	if m.SourceBiz == 0 || m.TargetBiz == 0 {
		return nil, nil, errno.BkBizIdIsEmpty
	}
	base := fmt.Sprintf("bk_biz_id=%d and cluster_type='%s'", m.SourceBiz, dbType)
	where = base
	if len(m.Users) > 0 {
		userPara = strings.Join(m.Users, "','")
		where = fmt.Sprintf("%s and user in ('%s')", base, userPara)
	}
	// 查询有哪些账号需要迁移
	err := DB.Self.Model(&TbAccounts{}).Where(where).Scan(&sourceAccounts).Order("id").Error
	if err != nil {
		return nil, nil, err
	}
	if len(sourceAccounts) == 0 {
		return nil, nil, fmt.Errorf("no user to be cloned")
	}
	// 实际需要迁移的user
	for _, v := range sourceAccounts {
		migrateUsers = append(migrateUsers, (*v).User)
		userIdFilter = fmt.Sprintf("%s,%d", userIdFilter, (*v).Id)
	}
	userIdFilter = strings.TrimPrefix(userIdFilter, ",")
	userPara = strings.Join(migrateUsers, "','")
	// 检查目标业务下待迁移账号是否已经存在，存在不迁移
	checkWhere = fmt.Sprintf("bk_biz_id=%d and cluster_type='%s' and user in ('%s')", m.TargetBiz, dbType, userPara)
	err = DB.Self.Model(&TbAccounts{}).Where(checkWhere).Scan(&targetAccounts).Error
	if err != nil {
		return nil, nil, err
	}
	if len(targetAccounts) > 0 {
		for _, v := range targetAccounts {
			conflictUsers = append(conflictUsers, (*v).User)
		}
		return conflictUsers, nil, fmt.Errorf("some users already exist in target biz:%d", m.TargetBiz)
	}

	ruleWhere = fmt.Sprintf("%s and account_id in (%s)", base, userIdFilter)
	err = DB.Self.Model(&TbAccountRules{}).Where(ruleWhere).Scan(&sourceRules).Error
	if err != nil {
		return nil, nil, err
	}

	type MaxId struct {
		MaxId int `gorm:"column:max_id"`
	}
	maxId := MaxId{}
	queryMax := fmt.Sprintf(
		"select auto_increment as max_id from information_schema.tables "+
			"where table_Schema ='%s' and table_name ='tb_accounts';", viper.GetString("db.name"),
	)
	err = DB.Self.Raw(queryMax).Scan(&maxId).Error
	if err != nil {
		return nil, nil, err
	}
	diff := int64(maxId.MaxId) - (*sourceAccounts[0]).Id + 100
	tx := DB.Self.Begin()
	vtime := time.Now()
	// 读取的行数据，填充目标业务、更新账号id值、账号规则中的account_id等
	// 批量插入
	for _, v := range sourceAccounts {
		(*v).BkBizId = m.TargetBiz
		(*v).Id = (*v).Id + diff
		(*v).CreateTime = vtime
		(*v).UpdateTime = vtime
		(*v).Creator = "migrator"
		(*v).Operator = "migrator"
		err = tx.Model(&TbAccounts{}).Create(v).Error
		if err != nil {
			tx.Rollback()
			return nil, nil, err
		}
	}
	for _, v := range sourceRules {
		(*v).BkBizId = m.TargetBiz
		(*v).Id = 0
		(*v).AccountId = (*v).AccountId + diff
		(*v).CreateTime = vtime
		(*v).UpdateTime = vtime
		(*v).Creator = "migrator"
		(*v).Operator = "migrator"
		err = tx.Model(&TbAccountRules{}).Create(v).Error
		if err != nil {
			tx.Rollback()
			return nil, nil, err
		}
	}
	err = tx.Commit().Error
	if err != nil {
		return nil, nil, err
	}
	return nil, migrateUsers, nil
}
