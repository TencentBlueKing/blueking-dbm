package handler

import (
	"encoding/json"
	"strconv"

	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/config"
	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/model/backupclient"
	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/model/backupserver"

	"github.com/Shopify/sarama"
	"github.com/jinzhu/copier"
	"github.com/spf13/cast"
	"golang.org/x/exp/slog"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type messageWrapper struct {
	Items []struct {
		Data json.RawMessage `json:"data"`
	} `json:"items"`
}

func (c *RegisterHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for {
		select {
		case message := <-claim.Messages():
			slog.Debug("process message", slog.String("Value", string(message.Value)))

			session.MarkMessage(message, "")

			var msg messageWrapper
			err := json.Unmarshal(message.Value, &msg)
			if err != nil {
				slog.Error("unmarshal message", err)
				return err
			}

			for _, item := range msg.Items {
				var obj backupclient.TaskObject
				slog.Debug("unmarshal task object", slog.String("data", string(item.Data)))
				unquoteData, err := strconv.Unquote(string(item.Data))
				if err != nil {
					slog.Error("unquote message payload", err)
					return err
				}

				err = json.Unmarshal([]byte(unquoteData), &obj)
				if err != nil {
					slog.Error("unmarshal task object", err)
					return err
				}
				var taskObj = &backupserver.TbBackupTasklist{}
				if err = copier.Copy(taskObj, obj); err != nil {
					return err
				}
				taskObj.FileLastMtime = obj.FileMtime
				taskObj.Size = cast.ToInt64(obj.FileSize)
				taskObj.Md5 = obj.FileMD5
				taskObj.RetryTimes = obj.Retries

				slog.Debug("unmarshal task obj", slog.Any("obj", obj))
				var tx *gorm.DB
				if config.RuntimeConfig.Dsn.Table != nil {
					tx = c.Db.Table(*config.RuntimeConfig.Dsn.Table).Clauses(
						clause.OnConflict{
							Columns: []clause.Column{{Name: "task_id"}},
							DoUpdates: clause.AssignmentColumns(
								[]string{
									"status",
									"uptime",
									"start_time",
									"complete_time",
								},
							),
						},
					).Create(&taskObj)
				} else {
					tx = c.Db.Clauses(
						clause.OnConflict{
							Columns: []clause.Column{{Name: "task_id"}},
							DoUpdates: clause.AssignmentColumns(
								[]string{
									"status",
									"uptime",
									"start_time",
									"complete_time",
								},
							),
						},
					).Create(&taskObj)
				}
				if err := tx.Error; err != nil {
					slog.Error("insert message", err, slog.String("value", string(message.Value)))
					return err
				}
				slog.Info("insert message", slog.String("key", string(message.Key)))
			}

		case <-session.Context().Done():
			return nil
		}
	}
}
