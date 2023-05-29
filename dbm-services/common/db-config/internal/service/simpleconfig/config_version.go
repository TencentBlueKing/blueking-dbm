package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/logger"

	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"gorm.io/gorm"
)

// ListConfigFileVersions TODO
// get versions history list and mark the latest one
func ListConfigFileVersions(r *api.ListConfigVersionsReq) (*api.ListConfigVersionsResp, error) {
	var m = model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,
	}
	var resp = &api.ListConfigVersionsResp{
		BKBizID:      r.BKBizID,
		Namespace:    r.Namespace,
		BaseLevelDef: r.BaseLevelDef,
	}
	verList := make([]string, 0)
	if versions, err := m.ListConfigFileVersions(true); err != nil {
		return nil, err
	} else {
		for _, v := range versions {
			verList = append(verList, v.Revision)
			if v.IsPublished == 1 { // should have only one
				resp.VersionLatest = v.Revision
			}
			ver := map[string]interface{}{
				"revision":      v.Revision,
				"conf_file":     v.ConfFile,
				"created_at":    v.CreatedAt,
				"created_by":    v.CreatedBy,
				"rows_affected": v.RowsAffected,
				"is_published":  v.IsPublished,
				"description":   v.Description,
			}
			resp.Versions = append(resp.Versions, ver)
		}
		// resp.Versions = verList
		return resp, nil
	}
}

// GetVersionedDetail TODO
func GetVersionedDetail(r *api.GetVersionedDetailReq) (*api.GetVersionedDetailResp, error) {
	var m = model.ConfigVersionedModel{
		BKBizID:    r.BKBizID,
		Namespace:  r.Namespace,
		LevelName:  r.LevelName,
		LevelValue: r.LevelValue,
		ConfType:   r.ConfType,
		ConfFile:   r.ConfFile,
	}
	vc := &model.ConfigVersioned{}
	versionList := []string{r.Revision}
	if versions, err := m.GetVersionedConfigFile(model.DB.Self, versionList); err != nil {
		return nil, err
	} else if len(versions) == 0 {
		return nil, errors.Errorf("no version found %s", r.Revision)
	} else if len(versions) != 1 {
		return nil, errors.Errorf("err record found %d for %v", len(versions), m)
	} else {
		vc.Versioned = versions[0]
		v := vc.Versioned
		resp := &api.GetVersionedDetailResp{
			ID:           v.ID,
			Revision:     v.Revision,
			PreRevision:  v.PreRevision,
			RowsAffected: v.RowsAffected,
			Description:  v.Description,
			// ContentStr:   v.ContentStr,
			CreatedAt: v.CreatedAt.String(),
			CreatedBy: v.CreatedBy,
		}
		if err = vc.UnPack(); err != nil {
			return nil, err
		}
		if err = vc.MayDecrypt(); err != nil {
			return nil, err
		}

		// unpack 后，将 configs, configsDiff 转换成resp格式，并情况原对象避免返回太多无用信息
		if confValues, err := FormatConfItemForResp(r.Format, vc.Configs); err != nil {
			return nil, err
		} else {
			resp.Configs = confValues
			// resp.Content = confValues
		}
		if confValues, err := FormatConfItemOpForResp(r.Format, vc.ConfigsDiff); err != nil {
			return nil, err
		} else {
			resp.ConfigsDiff = confValues
		}
		return resp, nil
	}
}

// PublishConfig TODO
type PublishConfig struct {
	Versioned     *model.ConfigVersionedModel
	LevelNode     api.BaseConfigNode
	ConfigsLocked []*model.ConfigModel
	Patch         map[string]string
	FromGenerated bool
	Revision      string
}

// PublishAndApplyVersioned TODO
// 只发布版本，之前已生成revision. is_published=true, is_applied=false
// 如果 configsLocked 数大于 1，表示修改了锁定配置，需要应用到下级
// level_config 在发布包含 locked config 时，都会 apply
func (p *PublishConfig) PublishAndApplyVersioned(db *gorm.DB, isFromApplied bool) error {
	logger.Info("PublishAndApplyVersioned %+v", p)
	c := p.Versioned
	if p.Patch != nil {
		// update tb_config_versioned
		if err := c.PatchConfig(db, p.Patch); err != nil {
			return err
		}
		// update tb_config_node，不检查冲突、是否只读
		var cms []*model.ConfigModelOp
		for confName, confValue := range p.Patch {
			cm := &model.ConfigModelOp{
				Config: &model.ConfigModel{
					BKBizID:         p.LevelNode.BKBizID,
					Namespace:       p.LevelNode.Namespace,
					ConfType:        p.LevelNode.ConfType,
					ConfFile:        p.LevelNode.ConfFile,
					LevelName:       p.LevelNode.LevelName,
					LevelValue:      p.LevelNode.LevelValue,
					UpdatedRevision: p.Revision,
					ConfName:        confName,
					ConfValue:       confValue,
					Description:     "updated by internal api",
				},
				OPType: constvar.OPTypeAdd,
			}
			cms = append(cms, cm)
		}
		if _, err := UpsertConfigItems(db, cms, p.Revision); err != nil {
			return err
		}
		// 走 delete version + update + GenAndPublish 流程
	}
	if err := c.PublishConfig(db); err != nil {
		return err
	}

	levelNode := api.BaseConfigNode{}
	copier.Copy(&levelNode, c)
	p.LevelNode = levelNode
	if model.IsConfigLevelEntityVersioned(c.Namespace, c.ConfType, c.ConfFile, c.LevelName) {
		// versioned config 有修改，就生成更新提示
		return p.GenTaskForApplyEntityConfig(db)
	}
	if isFromApplied { // 不做级联应用
		return nil
	}

	if p.FromGenerated { // 来自 generate 接口，直接设置为 applied，只有 entity level 才能 generate
		if err := p.Versioned.VersionApplyStatus(db); err != nil {
			return err
		}
	} else {
		// level config，仅有 locked 配置修改时，生成更新提示
		if p.ConfigsLocked == nil || len(p.ConfigsLocked) == 0 {
			return p.Versioned.VersionApplyStatus(db)
		}
		return p.ApplyLevelConfig(db)
	}
	return nil
}

// ApplyLevelConfig 向下应用 level config 配置
// 应用行为，会删除与上级锁定冲突的配置
func (p *PublishConfig) ApplyLevelConfig(db *gorm.DB) error {
	logger.Info("ApplyLevelConfig %+v", p)
	applyReq := api.VersionApplyReq{
		BaseConfigNode: p.LevelNode,
		RevisionApply:  p.Versioned.Revision,
	}
	if err := p.ApplyVersionLevelNode(db, &applyReq); err != nil {
		return err
	}
	if err := p.Versioned.VersionApplyStatus(db); err != nil {
		return err
	}
	return nil
}

// GenTaskForApplyEntityConfig 将未应用的配置项，写入 node_task
func (p *PublishConfig) GenTaskForApplyEntityConfig(db *gorm.DB) error {
	// versioned_config 无论是否应用，都生成 node_task，且保持未应用状态
	applyInfo := api.ApplyConfigInfoReq{BaseConfigNode: p.LevelNode}
	diffInfo, err := GetConfigsToApply(db, applyInfo)
	if err != nil {
		return err
	}
	nodeTasks := make([]*model.NodeTaskModel, 0)
	for confName, diff := range diffInfo.ConfigsDiff {
		task := &model.NodeTaskModel{
			VersionID:       diffInfo.VersionID,
			NodeID:          diffInfo.NodeID,
			Revision:        diffInfo.RevisionToApply,
			UpdatedRevision: diff.UpdatedRevision,
			ConfName:        confName,
			ConfValue:       diff.ConfValue,
			OPType:          diff.OPType,
			ValueBefore:     diff.ValueBefore,
		}
		nodeTasks = append(nodeTasks, task)
	}
	if len(nodeTasks) == 0 {
		if err := p.Versioned.VersionApplyStatus(db); err != nil {
			return err
		}
		return nil
	} else {
		return model.GenTaskForApply(db, diffInfo.NodeID, nodeTasks)
	}
}
