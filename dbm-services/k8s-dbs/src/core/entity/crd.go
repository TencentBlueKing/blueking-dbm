package entity

import (
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
)

// CustomResourceDefinition custom resource parameters
type CustomResourceDefinition struct {
	Namespace            string
	ResourceType         string
	ResourceName         string
	GroupVersionResource schema.GroupVersionResource
	ResourceObject       *unstructured.Unstructured
}
