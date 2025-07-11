package model

import (
	"fmt"
	"slices"
	"strings"
	"time"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

type BaseModel struct {
	ID        uint64    `gorm:"primaryKey;autoIncrement:true"  xorm:"pk autoincr"`
	CreatedAt time.Time `json:"created_at" db:"created_at" gorm:"autoCreateTime" xorm:"created"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at" gorm:"autoUpdateTime" xorm:"updated"`

	EventCreateTimestamp  int64 `json:"event_create_timestamp"`
	EventReportTimestamp  int64 `json:"event_report_timestamp"`
	EventReceiveTimestamp int64 `json:"event_receive_timestamp"`

	EventBkCloudId int    `json:"event_bk_cloud_id"`
	EventSourceIp  string `json:"event_source_ip" gorm:"type:varchar(30)"`
	EventBkBizId   int64  `json:"event_bk_biz_id"`
	//EventClusterType string `json:"event_cluster_type"`
	//EventType        string `json:"event_type"`
	//ClusterType string `json:"cluster_type"`
	//EventUuid string `json:"event_uuid"`
}

func (b BaseModel) OmitFields() []string {
	return []string{"event_cluster_type", "event_type", "cluster_type", "event_uuid"}
}

// StrictSchema use map[string]interface to unmarshal kafka msg, and save to db
// no_manage_schema=true still need model_table to determine TableName() and OmitFields() to generate sql
// default is false means use model_table's definition to unmarshal kafka msg
func (b BaseModel) StrictSchema() bool {
	return true
}

// CreateOrUpdateIndex create index if not exists
// if exists and has different definition, drop and create
// if exists and has same definition, do nothing
func CreateOrUpdateIndex(db *gorm.DB, tableName string, indexName string, columnNames []string, unique bool, overwrite bool) error {
	indexes, _ := db.Migrator().GetIndexes(tableName)
	for _, i := range indexes {
		// same definition: 索引名字相同，unique相同，列相同 --> 不重复添加索引
		if i.Name() == indexName {
			i.Option()
			if uk, _ := i.Unique(); uk == unique && slices.Equal(columnNames, i.Columns()) {
				return nil
			} else if overwrite {
				if err := db.Migrator().DropIndex(tableName, indexName); err != nil {
					return errors.WithMessage(err, "create index")
				}
			} else {
				return errors.Errorf("index %s already exists on %s", indexName, tableName)
			}
		}
	}
	var buildAlter string
	if unique {
		buildAlter = fmt.Sprintf("ALTER TABLE `%s` ADD UNIQUE KEY", tableName)
	} else {
		buildAlter = fmt.Sprintf("ALTER TABLE `%s` ADD INDEX", tableName)
	}
	buildAlter += fmt.Sprintf(" %s (%s)", indexName, strings.Join(columnNames, ","))
	if err := db.Exec(buildAlter).Error; err != nil {
		return err
	}
	return nil
}
