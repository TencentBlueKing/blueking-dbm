package entity

type Dependencies struct {
	ExternalS3    *ExternalS3    `json:"externalS3,omitempty"`
	ExternalEtcd  *ExternalEtcd  `json:"externalEtcd,omitempty"`
	ExternalKafka *ExternalKafka `json:"externalKafka,omitempty"`
}

type ExternalS3 struct {
	Enabled        bool   `json:"enabled,omitempty"`
	Host           string `json:"host,omitempty"`
	Port           string `json:"port,omitempty"`
	AccessKey      string `json:"accessKey,omitempty"`
	SecretKey      string `json:"secretKey,omitempty"`
	UseSSL         bool   `json:"useSSL,omitempty"`
	BucketName     string `json:"bucketName,omitempty"`
	RootPath       string `json:"rootPath,omitempty"`
	UseIAM         bool   `json:"useIAM,omitempty"`
	CloudProvider  string `json:"cloudProvider,omitempty"`
	IamEndpoint    string `json:"iamEndpoint,omitempty"`
	Region         string `json:"region,omitempty"`
	UseVirtualHost bool   `json:"useVirtualHost,omitempty"`
}

type ExternalEtcd struct {
	Enabled   bool     `json:"enabled,omitempty"`
	Endpoints []string `json:"endpoints,omitempty"`
}

type ExternalKafka struct {
	Enabled          bool   `json:"enabled,omitempty"`
	BrokerList       string `json:"brokerList,omitempty"`
	SecurityProtocol string `json:"securityProtocol,omitempty"`
	Sasl             Sasl   `json:"sasl,omitempty"`
}

type Sasl struct {
	Mechanisms string `json:"mechanisms,omitempty"`
	Username   string `json:"username,omitempty"`
	Password   string `json:"password,omitempty"`
}
