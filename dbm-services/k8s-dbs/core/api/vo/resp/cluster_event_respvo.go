package resp

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ClusterEventRespVo Defining cluster event response structures
type ClusterEventRespVo struct {
	Items []Event `json:"items"`
}

// Event Describes the core attributes of Kubernetes cluster events
type Event struct {
	CreationTimestamp metav1.Time `json:"creationTimestamp,omitempty"`
	Type              string      `json:"type,omitempty"`
	Reason            string      `json:"reason,omitempty"`
	Message           string      `json:"message,omitempty"`
}
