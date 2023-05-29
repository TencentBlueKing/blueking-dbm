package sendwarning

import (
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/util"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"
	"time"
)

// eventBodyItem 告警项
type eventBodyItem struct {
	EventName string `json:"event_name"`
	Target    string `json:"target"`
	Event     struct {
		Content string `json:"content"`
	} `json:"event"`
	Dimension map[string]interface{} `json:"dimension,omitempty"`
	Metrics   map[string]float64     `json:"metrics,omitempty"`
}

// BkMonitorEventSender 蓝鲸监控自定义事件
type BkMonitorEventSender struct {
	DataID            int64           `json:"data_id"`
	AccessToken       string          `json:"access_token"`
	GsePath           string          `json:"-"`
	ToolBkMonitorBeat string          `json:"-"`
	AgentAddress      string          `json:"-"`
	Data              []eventBodyItem `json:"data"`
}

// NewBkMonitorEventSender new
func NewBkMonitorEventSender(dataID int64, token, gsePath string) (ret *BkMonitorEventSender, err error) {
	if !util.FileExists(gsePath) {
		err = fmt.Errorf("GSE_PATH:%s not exists", gsePath)
		mylog.Logger.Error(err.Error())
		return
	}
	ret = &BkMonitorEventSender{
		DataID:      dataID,
		AccessToken: token,
		GsePath:     gsePath,
	}
	ret.ToolBkMonitorBeat = filepath.Join(gsePath, "plugins/bin/bkmonitorbeat")
	if !util.FileExists(ret.ToolBkMonitorBeat) {
		err = fmt.Errorf("%s not exists", ret.ToolBkMonitorBeat)
		mylog.Logger.Error(err.Error())
		return
	}
	beatConf := filepath.Join(gsePath, "plugins/etc/bkmonitorbeat.conf")
	if !util.FileExists(beatConf) {
		err = fmt.Errorf("%s not exists", beatConf)
		mylog.Logger.Error(err.Error())
		return
	}
	grepCmd := fmt.Sprintf(`grep ipc %s|awk '{print $2}'`, beatConf)
	ret.AgentAddress, err = util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	if err != nil {
		return
	}
	ret.Data = append(ret.Data, eventBodyItem{})
	return
}

// SendWarning 发送告警,示例:
// 可以不传入 dimension 和 metrics,如直接调用 SendWarning("xxx","xxx","1.1.1.1",nil,nil)
/*
 /usr/local/gse_bkte/plugins/bin/bkmonitorbeat -report -report.bk_data_id 5428xx \
 -report.type agent \
 -report.message.kind event \
 -report.agent.address /usr/local/gse_bkte/agent/data/ipc.state.report \

	-report.message.body '{
	    "data_id":5428xx,
	    "access_token":"xxxx",
	    "data":[{
	        "event_name":"REDIS_MEM",
	        "target":"1.1.1.1",
	        "event":{
	            "content":" tendisx.aaaa.testapp.db  1.1.1.1:30000 memory_used 7.2GB >= 90% maxmemory:8GB"
	        },
	        "dimension":{
	            "bk_biz_id":"200500194",
	            "bk_cloud_id":"0",
	            "app_id":"200500194",
	            "app_name":"测试app",
	            "app":"testapp",
	            "cluster_domain":"tendisx.aaaa.testapp.db",
	            "cluster_name":"aaaa",
	            "cluster_type":"PredixyTendisplusCluster",
	            "instance":"1.1.1.1:30000",
	            "instance_role":"redis_slave",
				"warn_level":"warning" or "error"
	        },
	        "metrics":{
	            "memory_used":7730941133,
				"maxmemory":8589934592
	        }
	        }
	    ]}'
*/
func (bm *BkMonitorEventSender) SendWarning(eventName, warnmsg, warnLevel, targetIP string) (err error) {
	bm.newDimenSion()
	bm.Data[0].EventName = eventName
	bm.Data[0].Target = targetIP
	// bm.Data[0].Event.Content = bm.addDbMetaInfo(warnmsg)
	bm.Data[0].Event.Content = warnmsg
	bm.Data[0].Dimension["warn_level"] = warnLevel

	tempBytes, _ := json.Marshal(bm)
	sendCmd := fmt.Sprintf(
		`%s -report -report.bk_data_id %d -report.type agent  -report.message.kind event -report.agent.address %s -report.message.body '%s'`,
		bm.ToolBkMonitorBeat, bm.DataID, bm.AgentAddress, string(tempBytes))
	mylog.Logger.Info(sendCmd)
	_, err = util.RunBashCmd(sendCmd, "", nil, 20*time.Second)
	if err != nil {
		return
	}
	return nil
}

// addDbMetaInfo 生成content中前面db元信息
func (bm *BkMonitorEventSender) addDbMetaInfo(warnmsg string) string {
	var ret strings.Builder
	var ok bool
	if len(bm.Data[0].Dimension) > 0 {
		firstDimen := bm.Data[0].Dimension
		if _, ok = firstDimen["bk_biz_id"]; ok {
			ret.WriteString(fmt.Sprintf("bk_biz_id:%v\n", firstDimen["bk_biz_id"]))
		}
		if _, ok = firstDimen["bk_cloud_id"]; ok {
			ret.WriteString(fmt.Sprintf("bk_cloud_id:%v\n", firstDimen["bk_cloud_id"]))
		}
		// if _, ok = firstDimen["app_id"]; ok {
		// 	ret.WriteString(fmt.Sprintf("app_id:%v\n", firstDimen["app_id"]))
		// }
		if _, ok = firstDimen["app"]; ok {
			ret.WriteString(fmt.Sprintf("app:%v\n", firstDimen["app"]))
		}
		if _, ok = firstDimen["app_name"]; ok {
			ret.WriteString(fmt.Sprintf("app_name:%v\n", firstDimen["app_name"]))
		}
		if _, ok = firstDimen["cluster_domain"]; ok {
			ret.WriteString(fmt.Sprintf("cluster_domain:%v\n", firstDimen["cluster_domain"]))
		}
		if _, ok = firstDimen["cluster_type"]; ok {
			ret.WriteString(fmt.Sprintf("cluster_type:%v\n", firstDimen["cluster_type"]))
		}
		if _, ok = firstDimen["instance"]; ok {
			ret.WriteString(fmt.Sprintf("instance:%v\n", firstDimen["instance"]))
		}
		if _, ok = firstDimen["instance_role"]; ok {
			ret.WriteString(fmt.Sprintf("instance_role:%v\n", firstDimen["instance_role"]))
		}
	}
	ret.WriteString("message:" + warnmsg)
	return ret.String()
}
func (bm *BkMonitorEventSender) newDimenSion() {
	if len(bm.Data) == 0 {
		bm.Data = append(bm.Data, eventBodyItem{})
	}
	if len(bm.Data[0].Dimension) == 0 {
		bm.Data[0].Dimension = map[string]interface{}{}
	}
}

// SetBkBizID set bk_biz_id
func (bm *BkMonitorEventSender) SetBkBizID(bkBizID string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["bk_biz_id"] = bkBizID
	bm.Data[0].Dimension["app_id"] = bkBizID
	return bm
}

// SetBkCloudID set bk_cloud_id
func (bm *BkMonitorEventSender) SetBkCloudID(bkCloudID int64) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["bk_cloud_id"] = bkCloudID
	return bm
}

// SetApp set app
func (bm *BkMonitorEventSender) SetApp(app string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["app"] = app
	return bm
}

// SetAppName TODO
// SetApp set app
func (bm *BkMonitorEventSender) SetAppName(appname string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["app_name"] = appname
	return bm
}

// SetClusterDomain set domain
func (bm *BkMonitorEventSender) SetClusterDomain(domain string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["cluster_domain"] = domain
	return bm
}

// SetClusterName set cluster name
func (bm *BkMonitorEventSender) SetClusterName(clusterName string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["cluster_name"] = clusterName
	return bm
}

// SetClusterType set cluster name
func (bm *BkMonitorEventSender) SetClusterType(clusterType string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["cluster_type"] = clusterType
	return bm
}

// SetInstanceRole set role
func (bm *BkMonitorEventSender) SetInstanceRole(role string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["instance_role"] = role
	return bm
}

// SetInstanceHost set server host
func (bm *BkMonitorEventSender) SetInstanceHost(host string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["instance_host"] = host
	return bm
}

// SetInstance set instance
func (bm *BkMonitorEventSender) SetInstance(instance string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["instance"] = instance
	return bm
}

// ReplaceAllDimensions 用参数中dimensions替代 bm.Data[0].Dimension
func (bm *BkMonitorEventSender) ReplaceAllDimensions(dimensions map[string]interface{}) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension = dimensions
	return bm
}

// AppendDimensions 将参数中 dimensions 内容 replace 到 bm.Data[0].Dimension
func (bm *BkMonitorEventSender) AppendDimensions(dimensions map[string]interface{}) *BkMonitorEventSender {
	bm.newDimenSion()
	for key, val := range dimensions {
		bm.Data[0].Dimension[key] = val
	}
	return bm
}

func (bm *BkMonitorEventSender) newMetrics() {
	if len(bm.Data) == 0 {
		bm.Data = append(bm.Data, eventBodyItem{})
	}
	if len(bm.Data[0].Metrics) == 0 {
		bm.Data[0].Metrics = map[string]float64{}
	}
}

// ReplaceAllMetrcs 用参数中 metics 替代 bm.Data[0].Metrics
func (bm *BkMonitorEventSender) ReplaceAllMetrcs(metrcs map[string]float64) *BkMonitorEventSender {
	bm.newMetrics()
	bm.Data[0].Metrics = metrcs
	return bm
}

// AppendMetrcs 将参数中 metics 内容 replace 到 bm.Data[0].Metrcs
func (bm *BkMonitorEventSender) AppendMetrcs(metrcs map[string]float64) *BkMonitorEventSender {
	bm.newMetrics()
	for key, val := range metrcs {
		bm.Data[0].Metrics[key] = val
	}
	return bm
}
