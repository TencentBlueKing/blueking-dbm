package model

import (
	"gorm.io/gorm"
)

// NodeTaskModel TODO
type NodeTaskModel struct {
	ID uint64 `json:"id" gorm:"column:id;type:int;AUTO_INCREMENT;PRIMARY_KEY"`
	/*
	   BKBizID        string `json:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(120);not null"`
	   ConfType       string `json:"conf_type" gorm:"column:conf_type;type:varchar(60)"`
	   ConfFile       string `json:"conf_file" gorm:"column:conf_file;type:varchar(120)"`
	   Namespace      string `json:"namespace" gorm:"column:namespace;type:varchar(120)"`
	   LevelName      string `json:"level_name" gorm:"column:level_name;type:varchar(120)"`
	   LevelValue     string `json:"level_value" gorm:"column:level_value;type:varchar(120)"`
	   IsPublished    int8   `json:"is_published" gorm:"column:is_published;type:tinyint"`
	   IsApplied      int8   `json:"is_applied" gorm:"column:is_applied;type:tinyint"`
	   ContentObjDiff string `json:"content_obj_diff" gorm:"column:content_obj_diff;type:blob"`
	   Module         string `json:"module" gorm:"column:module;type:varchar(120)"`
	   Cluster        string `json:"cluster" gorm:"column:cluster;type varchar(120)"`
	   Description    string `json:"description" gorm:"column:description;type:varchar(255)"`
	   CreatedBy      string `json:"created_by" gorm:"column:created_by;type:varchar(120)"`
	*/

	NodeID          uint64 `json:"node_id" gorm:"column:node_id;type:int"`
	VersionID       uint64 `json:"version_id" gorm:"column:version_id;type:int"`
	Revision        string `json:"revision" gorm:"column:revision;type:varchar(120)"`
	OPType          string `json:"op_type" gorm:"column:op_type;type:varchar(120)"`
	UpdatedRevision string `json:"updated_revision" gorm:"column:updated_revision;type:varchar(120)"`
	ConfName        string `json:"conf_name" gorm:"column:conf_name;type:varchar(120)"`
	ConfValue       string `json:"conf_value" gorm:"column:conf_value;type:varchar(120)"`
	ValueBefore     string `json:"value_before" gorm:"column:value_before;type:varchar(120)"`
	Stage           int8   `json:"stage" gorm:"column:stage;type:tinyint"`
}

// TableName TODO
func (c NodeTaskModel) TableName() string {
	return "tb_config_node_task"
}

// BatchSaveNodeTask TODO
func BatchSaveNodeTask(db *gorm.DB, tasks []*NodeTaskModel) error {
	return db.Model(&NodeTaskModel{}).Save(tasks).Error
	// return nil
}

// DeleteNodeTask TODO
func DeleteNodeTask(db *gorm.DB, nodeID uint64) error {
	return db.Where("node_id = ?", nodeID).Delete(&NodeTaskModel{}).Error
	// return nil
}

// UpdateNodeTaskStage TODO
func UpdateNodeTaskStage(db *gorm.DB, nodeID uint64, confName []string, stage int) error {
	where := map[string]interface{}{
		"node_id":   nodeID,
		"conf_name": confName,
	}
	return db.Model(&NodeTaskModel{}).Update("stage = ?", stage).Where(where).Error
	// return nil
}

// GenTaskForApply 开启事务
func GenTaskForApply(db *gorm.DB, nodeID uint64, tasks []*NodeTaskModel) (err error) {
	err = db.Transaction(func(tx *gorm.DB) error {
		if err = DeleteNodeTask(tx, nodeID); err != nil {
			return err
		}
		if err = BatchSaveNodeTask(tx, tasks); err != nil {
			return err
		}
		return nil
	})
	return err
}

// UpdateStage godoc
func (c *NodeTaskModel) UpdateStage(db *gorm.DB, confNames []string, stage int) error {
	return db.Debug().Model(&NodeTaskModel{}).Where("conf_name in ?", confNames).Where(c).Update("stage", stage).Error
}

// QueryTasksByNode 确保同一个 node_id 只有一个 revision 存在
func (c *NodeTaskModel) QueryTasksByNode(db *gorm.DB) ([]*NodeTaskModel, error) {
	var tasks []*NodeTaskModel
	err := db.Model(&NodeTaskModel{}).Where("node_id = ?", c.NodeID).Find(&tasks).Error
	return tasks, err
}
