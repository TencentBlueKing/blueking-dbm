package model

import (
	"errors"

	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"gorm.io/gorm"
)

// GetModuleByCluster TODO
// up: 根据 bk_biz_id, cluster 查询集群所属模块
func (c *ConfigVersionedModel) GetModuleByCluster(bkBizID, cluster string) (string, error) {
	var dbModule string
	err := DB.Self.Table(c.TableName()).Select("module").
		Where(c).
		Where("is_published = 1 and bk_biz_id = ? and level_name=? and level_value = ? and module is not null",
			bkBizID, constvar.LevelCluster, cluster).
		Take(&dbModule).Error
	if err != nil && !errors.Is(err, gorm.ErrRecordNotFound) {
		return "", err
	}
	return dbModule, nil
}

// GetClusterByInstance TODO
// up
func (c *ConfigVersionedModel) GetClusterByInstance(bkBizID, instance string) (string, error) {
	var cluster string
	err := DB.Self.Table(c.TableName()).Select("cluster").
		Where(c).
		Where("is_published = 1 and bk_biz_id = ? and level_name = ? and level_value = ?",
			bkBizID, constvar.LevelInstance, instance).Take(&cluster).Error
	if err != nil {
		return "", err
	}
	return cluster, nil
}

// GetAppsAll TODO
// down: 获取所有 bk_biz_id 列表
func (c *ConfigVersionedModel) GetAppsAll() ([]string, error) {
	var bkBizIDs []string
	err := DB.Self.Debug().Table(c.TableName()).
		Where("is_published = 1 and bk_biz_id != ?", constvar.BKBizIDForPlat).
		Where(c).
		Distinct().Pluck("bk_biz_id", &bkBizIDs).Error
	if err != nil {
		return nil, err
	}
	return bkBizIDs, nil
}

// GetModulesByApp TODO
// down: 根据 bk_biz_id 查询所有db模块
func (c *ConfigVersionedModel) GetModulesByApp(bkBizID string) ([]string, error) {
	var modules []string
	err := DB.Self.Debug().Table(c.TableName()).
		Where("is_published = 1 and bk_biz_id = ? and level_name=?", bkBizID, constvar.LevelModule).
		Where(c).
		Distinct().Pluck("level_value", &modules).Error
	if err != nil {
		return nil, err
	}
	return modules, nil
}

// GetClustersByModule TODO
// down: 根据 bk_biz_id, db_module 查询所有集群
func (c *ConfigVersionedModel) GetClustersByModule(bkBizID, dbModule string) ([]string, error) {
	var clusters []string
	err := DB.Self.Debug().Table(c.TableName()).
		Where("is_published = 1 and bk_biz_id = ? and module = ?", bkBizID, dbModule).
		Where(c).
		Distinct().Pluck("level_value", &clusters).Error
	if err != nil {
		return nil, err
	}
	return clusters, nil
}

// GetInstancesByCluster TODO
// 根据集群查询 集群实例列表
// down: 不支持 instance 级配置. 暂时不用
func (c *ConfigVersionedModel) GetInstancesByCluster(bkBizID, dbCluster string) ([]string, error) {
	return nil, nil
}

// GetHostsByCluster TODO
// 根据集群查询 集群主机列表. 暂时不用
// down: 不支持 machine 级配置. 暂时不用
func (c *ConfigVersionedModel) GetHostsByCluster() ([]string, error) {
	return nil, nil
}

// GetModuleByCluster TODO
func GetModuleByCluster(bkBizID, cluster string) ([]*CmdbInfoBase, error) {
	var sqlRes *gorm.DB
	cmdbInfoBase := make([]*CmdbInfoBase, 0)
	sqlRes = DB.Self.Where("bk_biz_id=? and cluster=?", bkBizID, cluster).Find(&cmdbInfoBase)
	if err := sqlRes.Error; err != nil {
		if err != gorm.ErrRecordNotFound {
			return nil, err
		}
	}
	logger.Warnf("GetModuleByCluster sql: %+v", cmdbInfoBase)
	return cmdbInfoBase, nil
}
