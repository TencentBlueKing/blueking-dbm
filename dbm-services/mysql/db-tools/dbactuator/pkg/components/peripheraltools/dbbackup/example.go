package dbbackup

import "dbm-services/mysql/db-tools/dbactuator/pkg/components"

func (c *NewDbBackupComp) Example() interface{} {
	comp := NewDbBackupComp{
		Params: &NewDbBackupParam{
			Medium: components.Medium{
				Pkg:    "dbbackup-go.tar.gz",
				PkgMd5: "90e5be347c606218b055a61f990ecdf4",
			},
			Host:  "127.0.0.1",
			Ports: []int{20000, 20001},
			Options: map[int]BackupOptions{
				20000: {
					CrontabTime: "09:00:00",
					BackupType:  "logical",
					Master:      logicBackupDataOption{DataSchemaGrant: "grant"},
					Slave:       logicBackupDataOption{DataSchemaGrant: "grant"},
				},
				20001: {
					BackupType: "physical",
				},
			},
			Configs: map[string]map[string]string{
				"Public": {
					"BackupType":      "logical",
					"DataSchemaGrant": "all",
					"ClusterId":       "123",
					"BkBizId":         "456",
				},
				"LogicalBackup": {
					"Threads":       "4",
					"ChunkFilesize": "2048",
				},
				"PhysicalBackup": {
					"DefaultsFile": "/xx/yy/my.cnf.12006",
					"Throttle":     "100",
				},
			},
			Role:           "slave",
			ClusterAddress: map[int]string{20000: "testdb1.xx.a1.db", 20001: "testdb2.xx.a1.db"},
			ClusterId:      map[int]int{20000: 111, 20001: 112},
		},
	}
	return comp
}
