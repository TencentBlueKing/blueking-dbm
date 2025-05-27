package entity

// ResourceQuota 定义资源配额结构
type ResourceQuota struct {
	Request Resource `json:"request,omitempty"`
	Limit   Resource `json:"limit,omitempty"`
}

// Resource defines the CPU and memory requests and limits for a Kubernetes component.
type Resource struct {
	CPU    string `json:"cpu,omitempty"`
	Memory string `json:"memory,omitempty"`
}
