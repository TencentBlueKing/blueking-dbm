package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/util"
	"fmt"

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
		return nil, errors.New("illegal node_id")
	} else if resp.RevisionToApply == "" {
		return nil, errors.New("illegal revision")
	}
	return resp, nil
}

// GetVersionStat 批量获取某个 levelNode 的配置状态
func GetVersionStat(req api.VersionStatReq) (*api.VersionStatResp, error) {
	type objStatus struct {
		published string
		applied   string
		status    int
	}
	version := model.ConfigVersionedModel{
		Namespace: req.Namespace,
		ConfType:  req.ConfType,
		ConfFile:  req.ConfFile,
		LevelName: req.LevelName,
		BKBizID:   req.BKBizID,
	}
	applied, err := version.BatchGetApplied(req.LevelValues, model.DB.Self)
	if err != nil {
		logger.Warn("applied version not found %+v", version)
	}
	published, err := version.BatchGetPublished(req.LevelValues, model.DB.Self)
	if err != nil {
		return nil, errors.Wrap(err, "没有找到已发布且待下发的配置")
	}

	// todo 目前没有检查 已保存版本但未发布(且需要发布) 的情况，这个情况需要配置 version generate 时设定 is_published=2
	// {"cluster_id1": {"published":"xx", {"applied":"yy"}}, "cluster_id2":{}}
	objMap := make(map[string]*objStatus)
	for _, ver := range applied {
		objMap[ver.LevelValue] = &objStatus{}
		objMap[ver.LevelValue].applied = ver.Revision
	}
	for _, ver := range published {
		if _, ok := objMap[ver.LevelValue]; !ok {
			objMap[ver.LevelValue] = &objStatus{}
		}
		objMap[ver.LevelValue].published = ver.Revision
	}
	resp := &api.VersionStatResp{
		LevelValues: map[string][]int{},
	}
	for _, obj := range req.LevelValues {
		resp.LevelValues[obj] = make([]int, 0, 1)
		if val, ok := objMap[obj]; ok {
			if val.published == "" {
				objMap[obj].status = 3
			} else if val.published == "" {
				objMap[obj].status = 4
			} else if val.published == val.applied {
				objMap[obj].status = 1
			} else if val.published != val.applied {
				objMap[obj].status = 2
			}
			resp.LevelValues[obj] = []int{objMap[obj].status}
		} else {
			resp.LevelValues[obj] = []int{3, 4}
		}
	}
	resp.StatusInfo = api.StatusMap
	return resp, nil
}

// UpdateVersionApplied 修改 version 状态为已应用
// 在该 version 下的所有变动已经应用生效完成后，修改 version 状态
func UpdateVersionApplied() error {
	return nil
}

// ApplyVersionLevelNode 版本应用
// 对于 level_config, version apply 是找到所有直属下级，删除locked 冲突配置，然后对他们生成版本（但不应用）
func (p *PublishConfig) ApplyVersionLevelNode(db *gorm.DB, req *api.VersionApplyReq) error {
	// 生成的版本可以发布is_published=1，也可以不发布但需要下级自己发布 is_published=2
	if model.IsConfigLevelEntityVersioned(req.Namespace, req.ConfType, req.ConfFile, req.LevelName) {
		// 对于 versioned_config，version apply 需要外部下发命令去修改（但可以修改部分 config_item）
		// 当所有变更的配置项都已应用，才修改为 applied
		return errno.ErrOnlyLevelConfigAllowed
	}
	// todo 将来这两步，可以换成从 dbmeta 获取：比如获取 app 的所有 module，或者获取 app=1,module=2 的所有 cluster
	childLevelName := model.GetChildLevelStraight(req.Namespace, req.ConfType, req.ConfFile,
		req.LevelName) // todo 这里会重连连接中断事务？
	// childLevelValues := model.QueryLevelValuesWithName(req.Namespace, req.ConfType, req.ConfFile, req.BKBizID, childLevelName)
	childLevelValues, err := model.QueryChildLevelValues(&req.BaseConfigNode, childLevelName)
	if err != nil {
		return err
	}
	levelNode := api.BaseConfigNode{
		BKBizIDDef: api.BKBizIDDef{BKBizID: req.BKBizID},
		BaseConfFileDef: api.BaseConfFileDef{
			Namespace: req.Namespace,
			ConfType:  req.ConfType,
			ConfFile:  req.ConfFile,
		},
	}
	namesToDel := make([]string, 0) // 需要删除的下级 conf_name
	if p.ConfigsLocked != nil {
		for _, config := range p.ConfigsLocked {
			namesToDel = append(namesToDel, config.ConfName)
		}
	} else {
		// 获取 已应用 和 将应用(=已发布) 之间的差异
		levelNode.LevelName = req.LevelName
		levelNode.LevelValue = req.LevelValue
		applyInfo := api.ApplyConfigInfoReq{BaseConfigNode: levelNode}
		diffInfo, err := GetConfigsToApply(db, applyInfo)
		if err != nil {
			return err
		}
		for _, c := range diffInfo.ConfigsDiff {
			if c.FlagLocked == 1 && (c.OPType == constvar.OPTypeAdd || c.OPType == constvar.OPTypeUpdate) {
				namesToDel = append(namesToDel, c.ConfName)
			}
		}
	}
	for _, child := range childLevelValues {
		levelNode.LevelName = childLevelName
		levelNode.LevelValue = child
		if req.BKBizID == constvar.BKBizIDForPlat {
			levelNode.BKBizID = child // childLevelName 一定是 app
		}
		options := api.QueryConfigOptions{
			Generate:              false, // 不应用
			FromNodeConfigApplied: true,
			Description: fmt.Sprintf("generated by apply up level_name=%s, level_value=%s",
				req.LevelName, req.LevelValue),
			InheritFrom: constvar.LevelPlat,
			View:        constvar.ViewMerge,
		}
		upLevelInfo := api.UpLevelInfo{
			LevelInfo: map[string]string{
				req.LevelName: req.LevelValue,
			},
		}
		logger.Info("ApplyVersionLevelNode: %+v", levelNode)

		// 删除与上层锁定 存在冲突的 直接下级
		if err := model.QueryAndDeleteConfig(db, &levelNode, namesToDel); err != nil {
			return err
		}
		// 发布直接下级，代表应用
		if err := GenerateAndPublish(db, &levelNode, &options, &upLevelInfo, p.Revision, nil); err != nil {
			return err
		}
	}
	return nil
}

// NodeTaskApplyItem TODO
func NodeTaskApplyItem(r *api.ConfItemApplyReq) error {
	if r.NodeID == 0 {
		v := model.ConfigFileNodeModel{
			BKBizID:    r.BKBizID,
			Namespace:  r.Namespace,
			ConfType:   r.ConfType,
			ConfFile:   r.ConfFile,
			LevelName:  r.LevelName,
			LevelValue: r.LevelValue,
		}
		if node, err := v.Detail(model.DB.Self); err != nil {
			return err
		} else if node == nil {
			return errors.Wrapf(errno.ErrNodeNotFound, "bk_biz_id=%s,namespace=%s,conf_file=%s,level_value=%s",
				r.BKBizID, r.Namespace, r.ConfFile, r.LevelValue)
		} else {
			r.NodeID = node.ID
		}
	}

	// configItems:

	return UpdateNodeTaskApplied(r.NodeID, r.RevisionApply, r.ConfNames)
}

// UpdateNodeTaskApplied 修改 node_task 里面任务状态为 applied
func UpdateNodeTaskApplied(nodeID uint64, revision string, confNames []string) error {
	n := model.NodeTaskModel{
		NodeID:   nodeID,
		Revision: revision,
	}
	logCtx := fmt.Sprintf("node_id=%d revision=%s", nodeID, revision)
	namesNotApplied := []string{}
	namesApplied := []string{}
	// 如果要 update task 存在跟 db 里的 revision 不一样，则报错
	if tasks, err := n.QueryTasksByNode(model.DB.Self); err != nil {
		return err
	} else {
		if len(tasks) == 0 {
			return errors.Errorf("no items to apply for %s", logCtx)
		} else {
			for _, t := range tasks {
				if t.Revision != revision {
					return errors.Errorf("当前需要应用的版本 %s，与待应用任务版本 %s 不一致", revision, t.Revision)
				}
				if t.Stage == 0 {
					namesNotApplied = append(namesNotApplied, t.ConfName)
				} else {
					namesApplied = append(namesApplied, t.ConfName)
				}
			}
		}
	}
	if len(namesNotApplied) == 0 {
		return errors.Errorf("没有找到待应用配置项 %s", logCtx)
	}
	for _, confName := range confNames {
		if util.StringsHas(namesApplied, confName) {
			logger.Errorf("配置项 %s 已应用 %s", confName, logCtx) // 不报错，只记录 log
		}
		if !util.StringsHas(namesNotApplied, confName) {
			return errors.Errorf("conf_name %s 未找到待应用任务 %s", confName, logCtx)
		}
	}

	txErr := model.DB.Self.Transaction(func(tx *gorm.DB) error {
		// 判断如果所有的 conf_name 都已 applied，update version 为 applied
		isAllApplied := true
		for _, confName := range namesNotApplied {
			if !util.StringsHas(confNames, confName) {
				isAllApplied = false
			}
		}
		if isAllApplied {
			v := model.ConfigVersionedModel{
				NodeID:   nodeID,
				Revision: revision,
			}
			if err := v.VersionApplyStatus(tx); err != nil {
				return err
			}
			// 如果全部应用，则清空列表
			if err := model.DeleteNodeTask(tx, nodeID); err != nil {
				return err
			}
		} else {
			// 设置为已应用
			err := n.UpdateStage(tx, confNames, 2)
			if err != nil {
				return err
			}
		}
		return nil
	})
	return txErr
}
