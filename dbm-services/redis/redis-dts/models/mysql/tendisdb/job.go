package tendisdb

import (
	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/pkg/customtime"
	"dbm-services/redis/redis-dts/pkg/scrdbclient"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/spf13/viper"
	"go.uber.org/zap"
)

// TbTendisDTSJob tendisSSD迁移数据到Tendisx任务行
type TbTendisDTSJob struct {
	ID                   int64                 `json:"id" gorm:"column:id;primary_key"`
	BillID               int64                 `json:"bill_id" gorm:"column:bill_id"`
	App                  string                `json:"app" gorm:"column:app"`
	BkCloudID            int64                 `json:"bk_cloud_id" gorm:"column:bk_cloud_id"`
	User                 string                `json:"user" gorm:"column:user"`
	DtsBillType          string                `json:"dts_bill_type" gorm:"column:dts_bill_type"`
	DtsCopyType          string                `json:"dts_copy_type" gorm:"column:dts_copy_type"`
	OnlineSwitchType     string                `json:"online_switch_type" gorm:"column:online_switch_type"`
	DataCheck            int                   `json:"data_check" gorm:"column:data_check"`
	DataRepair           int                   `json:"data_repair" gorm:"column:data_repair"`
	DataRapairMode       string                `json:"data_repair_mode" gorm:"column:data_repair_mode"`
	SrcCluster           string                `json:"src_cluster" gorm:"column:src_cluster"`
	SrcClusterType       string                `json:"src_cluster_type" gorm:"column:src_cluster_type"`
	SrcRollbackBillID    int64                 `json:"src_rollback_bill_id" gorm:"column:src_rollback_bill_id"`
	SrcRollbackInstances string                `json:"src_rollback_instances" gorm:"column:src_rollback_instances"`
	DstBkBizID           string                `json:"dst_bk_biz_id" gorm:"column:dst_bk_biz_id"`
	DstCluster           string                `json:"dst_cluster" gorm:"column:dst_cluster"`
	DstClusterType       string                `json:"dst_cluster_type" gorm:"column:dst_cluster_type"`
	KeyWhiteRegex        string                `json:"key_white_regex" gorm:"column:key_white_regex"`
	KeyBlackRegex        string                `json:"key_black_regex" gorm:"column:key_black_regex"`
	Status               int                   `json:"status" gorm:"column:status"`
	Reason               string                `json:"reason" gorm:"column:reason"`
	CreateTime           customtime.CustomTime `json:"createTime" gorm:"column:create_time"`
	UpdateTime           customtime.CustomTime `json:"updateTime" gorm:"column:update_time"`
}

// TableName sets the insert table name for this struct type
func (t *TbTendisDTSJob) TableName() string {
	return "tb_tendis_dts_job"
}

// GetTendisDTSJob 获取job对应row
func GetTendisDTSJob(
	billID int64, srcCluster, dstCluster string,
	logger *zap.Logger,
) (jobRows []*TbTendisDTSJob, err error) {
	var cli01 *scrdbclient.Client
	var subURL string
	var data *scrdbclient.APIServerResponse
	cli01, err = scrdbclient.NewClient(viper.GetString("serviceName"), logger)
	if err != nil {
		return
	}
	jobRows = []*TbTendisDTSJob{}
	if cli01.GetServiceName() == constvar.DtsRemoteTendisxk8s {
		subURL = constvar.K8sGetDtsJobURL
	} else if cli01.GetServiceName() == constvar.BkDbm {
		subURL = constvar.DbmGetDtsJobURL
	}
	type dtsJobReq struct {
		BillID     int64  `json:"bill_id"`
		SrcCluster string `json:"src_cluster"`
		DstCluster string `json:"dst_cluster"`
	}
	param := dtsJobReq{
		BillID:     billID,
		SrcCluster: srcCluster,
		DstCluster: dstCluster,
	}
	data, err = cli01.Do(http.MethodPost, subURL, param)
	if err != nil {
		return
	}
	err = json.Unmarshal(data.Data, &jobRows)
	if err != nil {
		err = fmt.Errorf("GetTendisDTSJob unmarshal data fail,err:%v,resp.Data:%s,subURL:%s,param:%+v",
			err.Error(), string(data.Data), subURL, param)
		logger.Error(err.Error())
		return
	}
	return
}
