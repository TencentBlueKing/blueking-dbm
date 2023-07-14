package backupclient

// CosAuth cos bucket 信息
type CosAuth struct {
	CosServer  string `mapstructure:"cos_server" json:"cos_server" toml:"cos_server"`
	Region     string `mapstructure:"region" json:"region" toml:"region"`
	SecretId   string `mapstructure:"secret_id" json:"secret_id" toml:"secret_id"`
	SecretKey  string `mapstructure:"secret_key" json:"secret_key" toml:"secret_key"`
	BucketName string `mapstructure:"bucket_name" json:"bucket_name" toml:"bucket_name"`
}

// AppAttr 机器业务属性
type AppAttr struct {
	BkBizId   int `mapstructure:"bk_biz_id" json:"bk_biz_id" toml:"bk_biz_id"`
	BkCloudId int `mapstructure:"bk_cloud_id" json:"bk_cloud_id" toml:"bk_cloud_id"`
}

// CosInfo cosinfo.toml
type CosInfo struct {
	Cos     *CosAuth `toml:"cos_auth" json:"cos_auth"`
	AppAttr *AppAttr `toml:"app_attr" json:"app_attr"`
}

type CosClientConfig struct {
	Base BaseLimit    `toml:"coslimits" json:"coslimit" mapstructure:"coslimits"`
	Cfg  UploadConfig `toml:"cfg" json:"cfg" mapstructure:"cfg"`
}

type UploadConfig struct {
	// FileTagAllowed 允许的 file tag 列表
	FileTagAllowed string `mapstructure:"file_tag_allowed" json:"file_tag_allowed" toml:"file_tag_allowed"`
	// NetAddr 本机内网ip地址
	NetAddr string `mapstructure:"net_addr" json:"net_addr" toml:"net_addr"`
}

type BaseLimit struct {
	BlockSize       int `mapstructure:"chunk_size" json:"block_size" toml:"chunk_size"`
	LocalTotalLimit int `mapstructure:"local_total_limit" json:"local_total_limit" toml:"local_total_limit"`
	LocalFileLimit  int `mapstructure:"local_file_limit" json:"local_file_limit" toml:"local_file_limit"`
}
