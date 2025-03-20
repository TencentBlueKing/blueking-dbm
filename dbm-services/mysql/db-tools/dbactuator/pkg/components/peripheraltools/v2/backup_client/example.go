package backup_client

import (
	"dbm-services/common/go-pubpkg/backupclient"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
)

func (c *BackupClientComp) Example() interface{} {
	return BackupClientComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.AccountMonitorExample,
			},
		},
		Params: BackupClientParam{
			Medium: components.Medium{
				Pkg:    "backup_client.tar.gz",
				PkgMd5: "12345",
			},
			Config: backupclient.CosClientConfig{
				Base: backupclient.BaseLimit{
					BlockSize:       100,
					LocalFileLimit:  100,
					LocalTotalLimit: 100,
				},
				Cfg: backupclient.UploadConfig{
					FileTagAllowed: "MYSQL_FULL_BACKUP,REDIS_FULL....",
					NetAddr:        "x.x.x.x",
				},
			},
			CosInfo: backupclient.CosInfo{
				Cos: &backupclient.CosAuth{
					Region:     "xxx",
					BucketName: "yyy",
					SecretId:   "sid encrypted",
					SecretKey:  "skey encrypted",
					CosServer:  "urlxxx",
				},
				AppAttr: &backupclient.AppAttr{
					BkBizId:   3,
					BkCloudId: 0,
				},
			},
			ExecUser: "sys",
		},
	}
}
