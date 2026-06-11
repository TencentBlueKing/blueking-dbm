package simpleconfig

import (
	"bk-dbconfig/internal/api"
	"bk-dbconfig/internal/repository/model"

	"github.com/pkg/errors"
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
