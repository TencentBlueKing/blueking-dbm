package sendwarning

// 用于发送bkMonitorMsg
// 消息有两类，Event事件消息和TimeSeries时序消息
import (
	"dbm-services/mongodb/db-tools/dbmon/mylog"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/dbmon/util"
)

// eventBodyItem 告警项
type eventBodyItem struct {
	EventName string `json:"event_name"`
	Target    string `json:"target"`
	Timestamp int64  `json:"timestamp"`
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
	ToolBkMonitorBeat string          `json:"-"`
	AgentAddress      string          `json:"-"`
	Data              []eventBodyItem `json:"data"`
}

// NewBkMonitorEventSender new
func NewBkMonitorEventSender(beatPath, agentAddress string) (ret *BkMonitorEventSender,
	err error) {
	if !util.FileExists(beatPath) {
		err = fmt.Errorf("BEAT_PATH:%s not exists", beatPath)
		return
	}
	if !util.FileExists(agentAddress) {
		err = fmt.Errorf("agent_address:%s not exists", agentAddress)
		return
	}
	ret = &BkMonitorEventSender{
		ToolBkMonitorBeat: beatPath,
		AgentAddress:      agentAddress,
	}
	ret.AgentAddress = agentAddress
	ret.Data = make([]eventBodyItem, 0)
	ret.Data = append(ret.Data, eventBodyItem{})
	return
}

// SendEventMsg 发送告警消息
func (bm *BkMonitorEventSender) SendEventMsg(dataId int64, token string, eventName, warnmsg, warnLevel, targetIP string) (err error) {
	bm.newDimenSion()
	bm.DataID = dataId
	bm.AccessToken = token
	bm.Data[0].EventName = eventName
	bm.Data[0].Target = targetIP
	warnmsg = strings.ReplaceAll(warnmsg, "'", "")
	bm.Data[0].Event.Content = warnmsg
	bm.Data[0].Dimension["warn_level"] = warnLevel
	bm.SetEventCreateTime()

	tempBytes, _ := json.Marshal(bm)
	sendCmd := mycmd.New(bm.ToolBkMonitorBeat,
		"-report", "-report.bk_data_id", bm.DataID,
		"-report.type", "agent",
		"-report.message.kind", "event",
		"-report.agent.address", bm.AgentAddress,
		"-report.message.body", string(tempBytes))

	mylog.Logger.Info(sendCmd.GetCmdLine("", false))
	_, err = sendCmd.Run2(20 * time.Second)
	return
}

// SendTimeSeriesMsg dbmon心跳上报. "mongo_dbmon_heart_beat"
func (bm *BkMonitorEventSender) SendTimeSeriesMsg(dataId int64, token string, targetIP string, metricName string, val float64) (err error) {
	bm.newDimenSion()
	bm.DataID = dataId
	bm.AccessToken = token
	bm.Data[0].Target = targetIP
	l, _ := time.LoadLocation("Local")
	// 毫秒级时间戳
	bm.Data[0].Timestamp = time.Now().In(l).UnixMilli()
	metrics := make(map[string]float64)
	metrics[metricName] = val
	bm.Data[0].Metrics = metrics
	tempBytes, _ := json.Marshal(bm)
	sendCmd := mycmd.New(bm.ToolBkMonitorBeat,
		"-report", "-report.bk_data_id", bm.DataID,
		"-report.type", "agent",
		"-report.message.kind", "timeseries",
		"-report.agent.address", bm.AgentAddress,
		"-report.message.body", string(tempBytes))
	mylog.Logger.Info(sendCmd.GetCmdLine("", false))
	_, err = sendCmd.Run2(20 * time.Second)
	return
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

// DeleteAllDimesion delete all dimension
func (bm *BkMonitorEventSender) DeleteAllDimesion() *BkMonitorEventSender {
	bm.Data = bm.Data[:0]
	return bm
}

// SetBkBizID set bk_biz_id
func (bm *BkMonitorEventSender) SetBkBizID(bkBizID string) *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["bk_biz_id"] = bkBizID
	bm.Data[0].Dimension["appid"] = bkBizID
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

// SetEventCreateTime set instance
func (bm *BkMonitorEventSender) SetEventCreateTime() *BkMonitorEventSender {
	bm.newDimenSion()
	bm.Data[0].Dimension["event_create_time"] = time.Now().Local().Format(consts.UnixtimeLayout)
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
