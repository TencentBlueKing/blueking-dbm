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

package workflow

import (
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

type dbmRespond struct {
	Result    bool   `json:""`
	Code      int    `json:"code"`
	Message   string `json:"message"`
	RequestID string `json:"request_id"`
	Data      []struct {
		BkIdcCityID        int                             `json:"bk_idc_city_id"`
		BkIdcCityName      string                          `json:"bk_idc_city_name"`
		LogicalCityID      int                             `json:"logical_city_id"`
		LogicalCityName    string                          `json:"logical_city_name"`
		BkOSName           string                          `json:"bk_os_name"`
		BkIdcArea          string                          `json:"bk_idc_area"`
		BkIdcAreaID        int                             `json:"bk_idc_area_id"`
		BkSubZone          string                          `json:"bk_sub_zone"`
		BkSubZoneID        int                             `json:"bk_sub_zone_id"`
		BkRack             string                          `json:"bk_rack"`
		BkRackID           int                             `json:"bk_rack_id"`
		BkSvrDeviceClsName string                          `json:"bk_svr_device_cls_name"`
		BkIdcName          string                          `json:"bk_idc_name"`
		BkIdcID            int                             `json:"bk_idc_id"`
		BkCloudID          int                             `json:"bk_cloud_id"`
		NetDeviceID        string                          `json:"net_device_id"`
		AdminPort          int                             `json:"admin_port"`
		Port               int                             `json:"port"`
		IP                 string                          `json:"ip"`
		DbModuleID         int                             `json:"db_module_id"`
		BkBizID            int                             `json:"bk_biz_id"`
		Cluster            string                          `json:"cluster"`
		AccessLayer        string                          `json:"access_layer"`
		MachineType        hamodel.DbmMetadataMachineType  `json:"machine_type"`
		InstanceRole       hamodel.DbmMetadataInstanceRole `json:"instance_role"`
		InstanceInnerRole  string                          `json:"instance_inner_role"`
		ClusterID          int                             `json:"cluster_id"`
		ClusterType        hamodel.DbmMetadataClusterType  `json:"cluster_type"`
		Status             string                          `json:"status"`

		// The storage instance will be set when the cluster type is tendbha and the access layer is storage.
		Receiver []hamodel.DbmMetadataSlaveInfo `json:"receiver"`

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

		BindEntry map[string][]struct {
			BindPort       int         `json:"bind_port"`
			BindIps        []string    `json:"bind_ips"`
			Domain         string      `json:"domain"`
			EntryRole      string      `json:"entry_role"`
			ForwardEntryId interface{} `json:"forward_entry_id"`
			ClbIP          string      `json:"clb_ip"`
			ClbID          string      `json:"clb_id"`
			ClbListenerID  string      `json:"listener_id"`
			ClbRegion      string      `json:"clb_region"`
		} `json:"bind_entry"`

		// The receiver  will be set when the cluster type is tendbha
		// and the access layer is storage.
		ProxyInstanceSet []hamodel.DbmMetadataProxyInstance `json:"proxyinstance_set"`

		TBinlogDumpers []hamodel.DbmMetadataBinlogDumper `json:"tbinlogdumpers"`
	} `json:"data"`
}
