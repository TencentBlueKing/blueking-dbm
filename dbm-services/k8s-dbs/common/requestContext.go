package common

import (
	coreclient "k8s-dbs/core/client"
	providerentity "k8s-dbs/metadata/provider/entity"
)

// RequestContext encapsulates the essential context information for processing Kubernetes-related requests.
type RequestContext struct {
	K8sClient        *coreclient.K8sClient
	K8sClusterConfig *providerentity.K8sClusterConfigEntity
	RequestID        string
}
