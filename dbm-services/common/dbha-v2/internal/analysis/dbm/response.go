/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package dbm

import (
	"encoding/json"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// DbInstMetadata represents the metadata of a database instance.
type DbInstMetadata struct {
	BkIdcCityID        int                                `json:"bk_idc_city_id"`
	BkIdcCityName      string                             `json:"bk_idc_city_name"`
	LogicalCityID      int                                `json:"logical_city_id"`
	LogicalCityName    string                             `json:"logical_city_name"`
	BkOSName           string                             `json:"bk_os_name"`
	BkIdcArea          string                             `json:"bk_idc_area"`
	BkIdcAreaID        int                                `json:"bk_idc_area_id"`
	BkSubZone          string                             `json:"bk_sub_zone"`
	BkSubZoneID        int                                `json:"bk_sub_zone_id"`
	BkRack             string                             `json:"bk_rack"`
	BkRackID           int                                `json:"bk_rack_id"`
	BkSvrDeviceClsName string                             `json:"bk_svr_device_cls_name"`
	BkIdcName          string                             `json:"bk_idc_name"`
	BkIdcID            int                                `json:"bk_idc_id"`
	BkCloudID          int                                `json:"bk_cloud_id"`
	NetDeviceID        string                             `json:"net_device_id"`
	AdminPort          int                                `json:"admin_port"`
	Port               int                                `json:"port"`
	IP                 string                             `json:"ip"`
	DbModuleID         int                                `json:"db_module_id"`
	BkBizID            int                                `json:"bk_biz_id"`
	Cluster            string                             `json:"cluster"`
	AccessLayer        haprobe.DbmMetadataAccessLayerType `json:"access_layer"`
	MachineType        haprobe.DbmMetadataMachineType     `json:"machine_type"`
	InstanceRole       haprobe.DbmMetadataInstanceRole    `json:"instance_role"`
	InstanceInnerRole  string                             `json:"instance_inner_role"`
	ClusterID          int                                `json:"cluster_id"`
	ClusterType        haprobe.DbmMetadataClusterType     `json:"cluster_type"`
	Status             DbmMetadataStatus                  `json:"status"`
	SpiderRole         haprobe.DbmMetadataSpiderRole      `json:"spider_role"`
	IsStandBy          bool                               `json:"is_stand_by"`

	// The storage instance will be set when the cluster type is tendbha and the access layer is storage.
	Receiver []DbmMetadataSlaveInfo `json:"receiver"`

	Ejector []struct {
		IP        string `json:"ip"`
		Port      int    `json:"port"`
		Status    string `json:"status"`
		IsStandBy bool   `json:"is_stand_by"`
	} `json:"ejector"`

	// The storage instance will be set when the access layer is proxy.
	StorageInstance []struct {
		IP        string `json:"ip"`
		Port      int    `json:"port"`
		IsStandBy bool   `json:"is_stand_by"`
	} `json:"storageinstance"`

	BindEntry DbmMetadataBindEntry `json:"bind_entry"`

	// The receiver  will be set when the cluster type is tendbha
	// and the access layer is storage.
	ProxyInstanceSet []DbmMetadataProxyInstance `json:"proxyinstance_set"`
	BinlogDumpers    []DbmMetadataBinlogDumper  `json:"tbinlogdumpers"`
}

// UnmarshalJSON unmarshals metadata and keeps role compatibility between instance_role and spider_role.
func (d *DbInstMetadata) UnmarshalJSON(data []byte) error {
	type alias DbInstMetadata

	decoded := alias{}
	if err := json.Unmarshal(data, &decoded); err != nil {
		return err
	}

	rolePayload := struct {
		InstanceRole *haprobe.DbmMetadataInstanceRole `json:"instance_role"`
		SpiderRole   *haprobe.DbmMetadataSpiderRole   `json:"spider_role"`
	}{}
	if err := json.Unmarshal(data, &rolePayload); err != nil {
		return err
	}

	if decoded.InstanceRole == "" && rolePayload.SpiderRole != nil && *rolePayload.SpiderRole != "" {
		decoded.InstanceRole = haprobe.DbmMetadataInstanceRole(*rolePayload.SpiderRole)
	}

	*d = DbInstMetadata(decoded)

	return nil
}

// ResponseCommonInfo defines the other info except "data" of response.
type ResponseCommonInfo struct {
	Result    bool   `json:"result"`
	Code      int    `json:"code"`
	Message   string `json:"message"`
	RequestID string `json:"request_id"`
}

// Response represents the response structure for instances metadata query
type Response struct {
	ResponseCommonInfo

	Data []*DbInstMetadata `json:"data"`
}

// UpdateInstanceStatusResponse represents the response for updating database instance status
type UpdateInstanceStatusResponse struct {
	ResponseCommonInfo

	Data string `json:"data"`
}

// InstanceInfoInDomain contains detailed information about a instance in a domain
type InstanceInfoInDomain struct {
	App            string    `json:"app"`
	DnsStr         string    `json:"dns_str"`
	DomainName     string    `json:"domain_name"`
	DomainType     int       `json:"domain_type"`
	Ip             string    `json:"ip"`
	LastChangeTime time.Time `json:"last_change_time"`
	Manager        string    `json:"manager"`
	Port           int       `json:"port"`
	Remark         string    `json:"remark"`
	StartTime      time.Time `json:"start_time"`
	Status         string    `json:"status"`
	Uid            int       `json:"uid"`
}

// DomainGetResponse represents the response structure for domain information query
type DomainGetResponse struct {
	ResponseCommonInfo

	Data struct {
		Detail  []InstanceInfoInDomain `json:"detail"`
		RowsNum int                    `json:"rowsNum"`
	} `json:"data"`
}

// DomainDeleteResponse represents the response structure for domain deletion operation
type DomainDeleteResponse struct {
	ResponseCommonInfo

	Data struct {
		Detail  []InstanceInfoInDomain `json:"detail"`
		RowsNum int                    `json:"rowsNum"`
	} `json:"data"`
}

// ClbDeleteResponse represents the response structure for CLB deregistration.
// data is omitted intentionally: DBM may return number, string, or object; we only check result.
type ClbDeleteResponse struct {
	ResponseCommonInfo
}
