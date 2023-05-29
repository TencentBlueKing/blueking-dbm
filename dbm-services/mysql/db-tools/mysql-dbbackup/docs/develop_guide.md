## 编译
编译不需要 bin, lib 目录，但出包需要相关的依赖

二进制可执行文件、依赖库已被移除
```
dbbackup/bin]# tree
.
├── export.sh
├── mydumper
├── myloader
├── xtrabackup
│   ├── innobackupex_56.pl
│   ├── innobackupex_57
│   ├── innobackupex.pl
│   ├── qpress
│   ├── xbcloud_57
│   ├── xbcloud_80
│   ├── xbcloud_osenv_57
│   ├── xbcloud_osenv_80
│   ├── xbcrypt
│   ├── xbcrypt_57
│   ├── xbcrypt_80
│   ├── xbstream
│   ├── xbstream_57
│   ├── xbstream_80
│   ├── xtrabackup
│   ├── xtrabackup_56
│   ├── xtrabackup_57
│   └── xtrabackup_80
└── zstd

1 directory, 22 files

dbbackup/lib]# tree
.
├── libmydumper
│   ├── libmysqlclient.so.20
│   └── libzstd.so.1
├── libxtra
│   ├── libgcrypt.la
│   ├── libgcrypt.so
│   ├── libgcrypt.so.20
│   ├── libgcrypt.so.20.0.0
│   ├── libgpg-error.la
│   ├── libgpg-error.so
│   ├── libgpg-error.so.0
│   └── libgpg-error.so.0.10.0
└── libxtra_80
    ├── libmysqlservices.a
    ├── plugin
    │   ├── keyring_file.so
    │   └── keyring_vault.so
    └── private
        ├── libprotobuf-lite.so.3.6.1
        └── libprotobuf.so.3.6.1

5 directories, 15 files
```