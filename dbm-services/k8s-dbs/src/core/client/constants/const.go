package constants

const (
	BEARER_TOKEN = ""
	CRT_NAME     = ""
	Host         = ""
)

// Kind
const (
	ClusterDefinition   = "ClusterDefinition"
	ComponentDefinition = "ComponentDefinition"
	ComponentVersion    = "ComponentVersion"
)

var ResourceInGlobal = map[string]struct{}{
	ClusterDefinition:   {},
	ComponentDefinition: {},
	ComponentVersion:    {},
}

const (
	HelmDefaultNamespace = "kb-system"
	HelmDriver           = "secrets"
)
