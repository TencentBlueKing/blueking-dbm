package entity

import "time"

// K8sLog 封装 k8s 日志消息
type K8sLog struct {
	Timestamp time.Time `json:"timestamp"`
	Message   string    `json:"message"`
}
