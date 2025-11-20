package response

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ClusterEventResponse Defining cluster event response structures
type ClusterEventResponse struct {
	Items []Event `json:"items"`
}

// Event Describes the core attributes of Kubernetes cluster events
type Event struct {
	InvolvedObject    ObjectReference `json:"involvedObject,omitempty"`
	CreationTimestamp metav1.Time     `json:"creationTimestamp,omitempty"`
	Type              string          `json:"type,omitempty"`
	Reason            string          `json:"reason,omitempty"`
	Message           string          `json:"message,omitempty"`
}

// ObjectReference The object that this event is about
type ObjectReference struct {
	Kind      string `json:"kind,omitempty"`
	Namespace string `json:"namespace,omitempty"`
	Name      string `json:"name,omitempty"`
}
