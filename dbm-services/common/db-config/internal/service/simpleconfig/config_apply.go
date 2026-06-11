package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// GetConfigsToApply 获取两个版本之间的差异
// 比较 published(to_apply) 和 applied 之间的差异
func GetConfigsToApply(db *gorm.DB, req api.ApplyConfigInfoReq) (*api.ApplyConfigInfoResp, error) {
	// 判断是否是 versioned 级别配置
	version := model.ConfigVersionedModel{
		Namespace:  req.Namespace,
		ConfType:   req.ConfType,
		ConfFile:   req.ConfFile,
		LevelName:  req.LevelName,
		LevelValue: req.LevelValue,
		BKBizID:    req.BKBizID,
	}
	version.IsPublished = 0
	applied, err := version.GetVersionApplied(db)
	if err != nil {
		logger.Warn("applied version not found %+v", version)
	}
	version.IsApplied = 0
	published, err := version.GetVersionPublished(db)
	if err != nil {
		return nil, errors.Wrap(err, "没有找到已发布且待下发的配置")
	}

	if applied != nil && applied.Versioned.ID == published.Versioned.ID {
		return nil, errors.New("最新版本已应用至目标")
	}
	resp := &api.ApplyConfigInfoResp{
		ConfigsDiff:     map[string]*api.ApplyConfigItem{},
		RevisionToApply: published.Versioned.Revision,
		VersionID:       published.Versioned.ID,
		NodeID:          published.Versioned.NodeID,
	}
	if applied == nil {
		// 我们认为历史没有应用过，此次是第一次 publish
		return resp, nil
	} else {
		resp.RevisionBefore = applied.Versioned.Revision
		for _, c := range applied.Configs {
			resp.ConfigsDiff[c.ConfName] = &api.ApplyConfigItem{
				ValueBefore: c.ConfValue,
			}
		}
	}

	for _, c := range published.Configs {
		newItem := &api.ApplyConfigItem{
			ConfValue:       c.ConfValue,
			UpdatedRevision: c.UpdatedRevision,
			OPType:          constvar.OPTypeUpdate,
			LevelNameFrom:   c.LevelName,
			FlagLocked:      c.FlagLocked,
		}
		if val, ok := resp.ConfigsDiff[c.ConfName]; ok {
			newItem.ValueBefore = val.ValueBefore
		} else {
			// no value_before
			newItem.OPType = constvar.OPTypeAdd
		}
		resp.ConfigsDiff[c.ConfName] = newItem
	}

	nTask := model.NodeTaskModel{NodeID: published.Versioned.NodeID}
	confNamesApplied := make(map[string]string)
	if tasks, err := nTask.QueryTasksByNode(db); err != nil {
		return nil, err
	} else {
		for _, t := range tasks {
			if t.Stage == 2 { // stage 废弃？
				confNamesApplied[t.ConfName] = t.ConfValue
			}
		}
	}

	ConfigsDiffNew := make(map[string]*api.ApplyConfigItem)
	for confName, diff := range resp.ConfigsDiff {
		if diff.ConfValue == diff.ValueBefore {
			continue
		} else if util.ConfValueIsPlaceHolder(diff.ConfValue) {
			// 新值为计算得出，忽略
			logger.Warn("new conf_value is a variable %s: %s", confName, diff.ConfValue)
			continue
		}
		if _, ok := confNamesApplied[confName]; ok {
			diff.Applied = 1 // 已应用
		}
		ConfigsDiffNew[confName] = diff
	}
	resp.ConfigsDiff = ConfigsDiffNew

	if resp.NodeID == 0 {
		return resp, nil
		//return nil, errors.New("illegal node_id")
	} else if resp.RevisionToApply == "" {
		return nil, errors.New("illegal revision")
	}
	return resp, nil
}
