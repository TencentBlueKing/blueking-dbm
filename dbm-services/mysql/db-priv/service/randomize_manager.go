package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"
	"fmt"

	"golang.org/x/exp/slog"
)

// RandomExcludePara 对计划相关函数的入参
type RandomExcludePara struct {
	UserName string  `json:"username"`
	BkBizIds []int64 `json:"bk_biz_ids"`
	Operator string  `json:"operator"`
}

// TbRandomExclude 不参与随机化的业务的表
type TbRandomExclude struct {
	UserName   string          `gorm:"column:username;not_null" json:"username"`
	BkBizId    int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	Operator   string          `gorm:"column:operator" json:"operator"`
	UpdateTime util.TimeFormat `gorm:"column:update_time" json:"update_time"`
}

// ModifyRandomizeExclude 修改不参与随机化的业务
func (m *RandomExcludePara) ModifyRandomizeExclude(jsonPara string) error {
	if m.UserName == "" {
		return errno.NameNull
	}
	tx := DB.Self.Begin()
	// 传入的业务列表替换当前业务列表
	sql := fmt.Sprintf("delete from tb_randomize_exclude where username='%s'", m.UserName)
	err := tx.Debug().Exec(sql).Error
	if err != nil {
		slog.Error("msg", sql, err)
		tx.Rollback()
		return err
	}
	for _, id := range m.BkBizIds {
		// 更新tb_passwords中实例的密码
		sql = fmt.Sprintf("replace into tb_randomize_exclude(username,bk_biz_id,operator) values('%s',%d,'%s')",
			m.UserName, id, m.Operator)
		err = tx.Debug().Exec(sql).Error
		if err != nil {
			slog.Error("msg", sql, err)
			tx.Rollback()
			return err
		}
	}
	err = tx.Commit().Error
	if err != nil {
		return err
	}
	log := PrivLog{BkBizId: 0, Operator: m.Operator, Para: jsonPara, Time: util.NowTimeFormat()}
	AddPrivLog(log)
	return nil
}

// GetRandomizeExclude 查询不参与随机化的业务
func (m *RandomExcludePara) GetRandomizeExclude() ([]int64, error) {
	var ids []*TbRandomExclude
	if m.UserName == "" {
		return nil, errno.NameNull
	}
	err := DB.Self.Table("tb_randomize_exclude").Where(fmt.Sprintf("username = '%s'", m.UserName)).Scan(&ids).Error
	if err != nil {
		return nil, err
	}
	var list []int64
	for _, id := range ids {
		list = append(list, id.BkBizId)
	}
	return list, nil
}
