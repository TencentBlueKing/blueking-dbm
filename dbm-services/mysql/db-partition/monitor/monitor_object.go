package monitor

type eventBody struct {
	commonBody
	Data []eventData `json:"data"`
}

type metricsBody struct {
	commonBody
	Data []metricsData `json:"data"`
}

type commonBody struct {
	DataId      int    `json:"data_id"`
	AccessToken string `json:"access_token"`
}

type eventData struct {
	EventName string                 `json:"event_name"`
	Event     map[string]interface{} `json:"event"`
	commonData
}

type metricsData struct {
	commonData
}

type commonData struct {
	Target    string                 `json:"target"`
	Timestamp int64                  `json:"timestamp"`
	Dimension map[string]interface{} `json:"dimension"`
	Metrics   map[string]int         `json:"metrics"`
}

type Setting struct {
	MonitorMetricDataID      int    `json:"MONITOR_METRIC_DATA_ID"`
	MonitorEventDataID       int    `json:"MONITOR_EVENT_DATA_ID"`
	MonitorMetricAccessToken string `json:"MONITOR_METRIC_ACCESS_TOKEN"`
	MonitorEventAccessToken  string `json:"MONITOR_EVENT_ACCESS_TOKEN"`
	MonitorService           string `json:"MONITOR_SERVICE"`
}
