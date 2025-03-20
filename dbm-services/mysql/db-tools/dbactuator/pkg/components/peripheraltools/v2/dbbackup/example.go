package dbbackup

func (c *NewDbBackupComp) Example() interface{} {
	comp := NewDbBackupComp{
		Params: &NewDbBackupParam{
			Host:  "127.0.0.1",
			Ports: []int{20000, 20001},
			Options: &BackupOptions{

				CrontabTime: "09:00:00",
				BackupType:  "logical",
				Master:      logicBackupDataOption{DataSchemaGrant: "grant"},
				Slave:       logicBackupDataOption{DataSchemaGrant: "grant"},
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
			Role:         "slave",
			ImmuteDomain: "testdb1.xx.a1.db",
			ClusterId:    112,
		},
	}
	return comp
}
