package model

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"github.com/pkg/errors"
)

// QueryChildLevelValues 获取当前层级的所有直接下级
// 如果 childLevelName不为空，会校验下级 level_name 对不对
func QueryChildLevelValues(r *api.BaseConfigNode, childLevelName string) (childVals []string, err error) {
	v := ConfigVersionedModel{ // 这里只给 3 个值，来拼接条件，其它的条件在具体方法里面拼接
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
	}
	var levelErr bool
	switch r.LevelName {
	case constvar.LevelPlat:
		if childLevelName == "" || childLevelName == constvar.LevelApp {
			childVals, err = v.GetAppsAll()
		} else {
			levelErr = true
		}
	case constvar.LevelApp:
		if childLevelName == "" || childLevelName == constvar.LevelModule {
			childVals, err = v.GetModulesByApp(r.BKBizID)
		} else {
			levelErr = true
		}
	case constvar.LevelModule:
		if childLevelName == "" || childLevelName == constvar.LevelCluster {
			childVals, err = v.GetClustersByModule(r.BKBizID, r.LevelValue)
		} else {
			levelErr = true
		}
	case constvar.LevelCluster:
		if childLevelName == "" || childLevelName == constvar.LevelInstance {
			childVals, err = v.GetInstancesByCluster(r.BKBizID, r.LevelValue)
		} else {
			levelErr = true
		}
	default:
		return nil, errors.Errorf("fail to get child level for %s %s", r.LevelName, r.LevelValue)
	}
	if levelErr {
		err = errors.Errorf("level error: bk_biz_id=%s, level_name=%s, child_level_name=%s",
			r.BKBizID, r.LevelName, childLevelName)
		logger.Errorf(err.Error())
	}
	return childVals, errors.Wrap(err, "QueryChildLevelValues")
}

// QueryParentLevelValue 获取当前层级的的直接上级
func QueryParentLevelValue(r *api.BaseConfigNode) (levelInfo map[string]string, err error) {
	v := ConfigVersionedModel{ // 这里只给 3 个值，来拼接条件
		Namespace: r.Namespace,
		ConfType:  r.ConfType,
		ConfFile:  r.ConfFile,
	}
	levelInfo = make(map[string]string)
	var parentVal string
	switch r.LevelName {
	case constvar.LevelPlat: // plat 上级是它自己
		parentVal = constvar.BKBizIDForPlat
		levelInfo[constvar.LevelPlat] = parentVal
	case constvar.LevelApp:
		parentVal = constvar.BKBizIDForPlat
		levelInfo[constvar.LevelPlat] = parentVal
	case constvar.LevelModule:
		parentVal = r.BKBizID
		levelInfo[constvar.LevelApp] = parentVal
	case constvar.LevelCluster:
		parentVal, err = v.GetModuleByCluster(r.BKBizID, r.LevelValue)
		levelInfo[constvar.LevelModule] = parentVal
	case constvar.LevelInstance:
		parentVal, _ = v.GetClusterByInstance(r.BKBizID, r.LevelValue)
		levelInfo[constvar.LevelCluster] = parentVal
	default:
		return nil, errors.Errorf("fail to get parent level for %s %s", r.LevelName, r.LevelValue)
	}
	if parentVal == "" {
		return nil, errors.Errorf("cannot find parent level for %s %s", r.LevelName, r.LevelValue)
	}
	return levelInfo, errors.Wrap(err, "QueryParentLevelValue")
}
