

### 原始 payload 

#### scp

- 开始
```
{
    "extend": {
        "bk_biz_id": "0",
        "backup_type": "GZTAB",
        "download_type": "scp",
        "download_options": "",
        "file_date": "latest",
        "file_src": {
            "ssh_host": "",
            "ssh_port": "",
            "ssh_user": "",
            "ssh_pass": "",
            "path": "/data/dbbak",
            "match": "",
            "file_list": []
        },
        "file_tgt": {
            "path": "/data/dbbak"
        },
        "resume": true,
        "check_disksize": true
    }
}
```

- 暂停
- 回滚

#### gse

#### ieg_backup_center

#### wget