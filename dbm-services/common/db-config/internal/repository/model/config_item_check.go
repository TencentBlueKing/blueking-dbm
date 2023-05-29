package model

import (
	"fmt"
	"strings"

	"bk-dbconfig/internal/pkg/cst"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// GetConfigItemsAssociateNodes TODO
// 获取与本层级节点相关的节点：当前节点的 所有父节点 与 所有子节点
// 暂时允许的层级级别 plat,app,module,cluster
func (c *ConfigModelView) GetConfigItemsAssociateNodes() (map[string]interface{}, map[string]interface{}, error) {
	upLevels := cst.GetConfigLevelsUp(c.LevelName)
	downLevels := cst.GetConfigLevelsDown(c.LevelName)
	var err error
	levelUpMaps := map[string]interface{}{}
	if c.LevelName != constvar.LevelPlat {
		levelUpMaps[constvar.LevelPlat] = constvar.BKBizIDForPlat // 顶层平台配置，始终是上级
	}
	logger.Info("GetConfigItemsAssociateNodes level=%s %v %v", c.LevelName, upLevels, downLevels)
	versionObj := ConfigVersionedModel{}

	// 获得当前层级的所有上级
	for _, lName := range upLevels {
		if lName == constvar.LevelPlat {
			continue
		} else if lName == constvar.LevelApp {
			levelUpMaps[lName] = c.BKBizID
		} else if lName == constvar.LevelModule {
			if dbModule, ok := c.UpLevelInfo[constvar.LevelModule]; ok {
				levelUpMaps[lName] = dbModule
			} else {
				dbModule, err = versionObj.GetModuleByCluster(c.BKBizID, c.LevelValue)
				if dbModule == "" {
					return nil, nil, errors.Errorf("cannot find module for cluster %s", c.LevelValue)
				}
				levelUpMaps[lName] = dbModule
			}
		} else if lName == constvar.LevelCluster {
			if dbCluster, ok := c.UpLevelInfo[constvar.LevelCluster]; ok {
				levelUpMaps[lName] = dbCluster
			} else {
				dbCluster, err = versionObj.GetClusterByInstance(c.BKBizID, c.LevelValue)
				if dbCluster == "" {
					return nil, nil, errors.Errorf("cannot find cluster for instance %s", c.LevelValue)
				}
				levelUpMaps[lName] = dbCluster
			}
		} else {
			// return
		}
	}

	levelDownMaps := map[string]interface{}{}
	for _, lName := range downLevels {
		if lName == constvar.LevelApp {
			levelDownMaps[lName], err = versionObj.GetAppsAll()
		} else if lName == constvar.LevelModule {
			levelDownMaps[lName], err = versionObj.GetModulesByApp(c.BKBizID)
		} else if lName == constvar.LevelCluster {
			levelDownMaps[lName], err = versionObj.GetClustersByModule(c.BKBizID, c.LevelValue)
		} else if lName == constvar.LevelInstance {
			// @todo GetInstancesByCluster
			levelDownMaps[lName], err = versionObj.GetInstancesByCluster(c.BKBizID, c.LevelValue)
		}
	}
	return levelUpMaps, levelDownMaps, err
}

// GetConfigItemsAssociate TODO
// 根据 levelName, levelValue 批量获取配置项
// 访问视图 v_tb_config_node_plat
func (c *ConfigModelView) GetConfigItemsAssociate(bkBizID string, levelNodes map[string]interface{}) ([]*ConfigModel,
	error) {
	logger.Info("GetConfigItemsAssociate params: %s, %+v", bkBizID, levelNodes)
	sqlSubs := []string{}
	params := make([]interface{}, 0)
	configs := make([]*ConfigModel, 0)
	sqlPreparePlat := fmt.Sprintf(
		"select id,bk_biz_id, conf_name, conf_value,level_name,level_value,flag_locked " +
			"from v_tb_config_node_plat " +
			"where (namespace = ? and conf_type = ? and conf_file = ? and conf_name = ? ) " +
			"and (level_name = ? and level_value = ? )")
	sqlPrepare := fmt.Sprintf(
		"select id,bk_biz_id, conf_name, conf_value,level_name,level_value,flag_locked " +
			"from tb_config_node " +
			"where (namespace = ? and conf_type = ? and conf_file = ? and conf_name = ? )" +
			"and (level_name = ? and level_value in ? ) and bk_biz_id = ?")
	for levelName, levelValue := range levelNodes {
		if levelName == constvar.LevelPlat {
			if bkBizID == constvar.BKBizIDForPlat {
				return configs, nil // plat has no up level
			}
			param := []interface{}{c.Namespace, c.ConfType, c.ConfFile, c.ConfName,
				constvar.LevelPlat, constvar.BKBizIDForPlat}
			params = append(params, param...)
			sqlSubs = append(sqlSubs, sqlPreparePlat)
		} else {
			levelValues := cast.ToStringSlice(levelValue)
			if levelValue == nil || len(levelValues) == 0 {
				continue
			}
			param := []interface{}{c.Namespace, c.ConfType, c.ConfFile, c.ConfName,
				levelName, levelValues, bkBizID,
			}
			params = append(params, param...)
			sqlSubs = append(sqlSubs, sqlPrepare)
		}
	}
	sqlStr := strings.Join(sqlSubs, " UNION ALL ")
	logger.Info("GetConfigItemsAssociate ~%s~ ~%v~", sqlStr, params)
	if len(sqlStr) == 0 {
		return configs, nil
	}
	if err := DB.Self.Debug().Raw(sqlStr, params...).Scan(&configs).Error; err != nil {
		return nil, err
	}
	logger.Info("GetConfigItemsAssociate result: %+v", configs)

	return configs, nil
}
