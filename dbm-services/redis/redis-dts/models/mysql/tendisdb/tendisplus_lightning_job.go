package tendisdb

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/spf13/viper"
	"go.uber.org/zap"

	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/customtime"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
)

/*
create table tb_tendisplus_lightning_job (
id bigint NOT NULL primary key,
ticket_id bigint(20) NOT NULL,
user varchar(64) NOT NULL,
bk_biz_id varchar(64) NOT NULL,
bk_cloud_id bigint(20) NOT NULL,
dst_cluster varchar(128) NOT NULL,
dst_cluster_id bigint(20) NOT NULL,
cluster_nodes  longtext NOT NULL,
create_time datetime(6) NOT NULL,
key idx_create_time(create_time),
key idx_dst_cluster_id(dst_cluster_id),
key idx_user(user),
unique index uniq_ticket_cluster(ticket_id,dst_cluster)
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
*/

// TbTendisplusLightningJob TODO
type TbTendisplusLightningJob struct {
	// gorm
	ID           int64                 `gorm:"primary_key;column:id;type:bigint(20) unsigned;not null" json:"id"`
	TicketID     int64                 `gorm:"column:ticket_id;type:bigint(20) unsigned;not null" json:"ticket_id"`
	User         string                `gorm:"column:user;type:varchar(64);not null" json:"user"`
	BkBizID      string                `gorm:"column:bk_biz_id;type:varchar(64);not null" json:"bk_biz_id"`
	BkCloudID    int64                 `gorm:"column:bk_cloud_id;type:bigint(20) unsigned;not null" json:"bk_cloud_id"`
	DstCluster   string                `gorm:"column:dst_cluster;type:varchar(128);not null" json:"dst_cluster"`
	DstClusterID int64                 `gorm:"column:dst_cluster_id;type:bigint(20) unsigned;not null" json:"dst_cluster_id"`
	ClusterNodes string                `gorm:"column:cluster_nodes;type:longtext;not null" json:"cluster_nodes"`
	CreateTime   customtime.CustomTime `json:"create_time" gorm:"column:create_time"` // 创建时间
}

// TableName 表名
func (t *TbTendisplusLightningJob) TableName() string {
	return "tb_tendisplus_lightning_job"
}

// GetLightningJob 获取 lightning job对应row
func GetLightningJob(
	ticketID int64, dstCluster string,
	logger *zap.Logger,
) (jobRows []*TbTendisplusLightningJob, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	jobRows = []*TbTendisplusLightningJob{}
	subURL = constvar.DbmLightningJobDetailURL
	type lightningJobReq struct {
		TicketID   int64  `json:"ticket_id"`
		DstCluster string `json:"dst_cluster"`
	}
	param := lightningJobReq{
		TicketID:   ticketID,
		DstCluster: dstCluster,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &jobRows)
	if err != nil {
		err = fmt.Errorf("GetLightningJob unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}
